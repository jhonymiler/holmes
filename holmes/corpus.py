#!/usr/bin/env python3
"""corpus — the investigation's material (chats, documents, books) in searchable chunks.

One database per project (`corpus/corpus.db`), several collections. Never injected: only queried.

    python3 -I holmes/corpus.py add <collection> <file|folder> [--type auto|text|chat|pdf]
    python3 -I holmes/corpus.py search "<text>" [-c collection] [--author X] [-n 8] [--mode bm25|literal|vector|hybrid]
    python3 -I holmes/corpus.py show <chunk>                     full raw text of one chunk
    python3 -I holmes/corpus.py window <collection> <msg_id> [-k 5]   conversation around a message
    python3 -I holmes/corpus.py collections
    python3 -I holmes/corpus.py embed [-c collection] [--batch 32]    computes vectors (needs a server)

Vectors: HOLMES_EMBED_URL (Ollama-compatible server, POST /api/embed) and HOLMES_EMBED_MODEL.
HOLMES_EMBED_URL=fake makes deterministic hash vectors (tests only).
"""
import argparse
import array
import hashlib
import html
import json
import math
import os
import re
import shutil
import struct
import sqlite3
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("HOLMES_ROOT") or Path(__file__).resolve().parents[1])
DB = Path(os.environ.get("HOLMES_CORPUS") or ROOT / "corpus" / "corpus.db")
WINDOW = 8  # messages per context window

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS collection(name TEXT PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS document(id INTEGER PRIMARY KEY, collection TEXT NOT NULL REFERENCES collection(name),
  ref TEXT NOT NULL, title TEXT, sha TEXT, type TEXT, meta TEXT, UNIQUE(collection, ref));
CREATE TABLE IF NOT EXISTS chunk(id INTEGER PRIMARY KEY, document INTEGER NOT NULL REFERENCES document(id),
  kind TEXT NOT NULL, position INTEGER, ts TEXT, author TEXT, msg_id TEXT, text TEXT NOT NULL, meta TEXT);
CREATE INDEX IF NOT EXISTS chunk_doc ON chunk(document, kind, position);
CREATE INDEX IF NOT EXISTS chunk_msg ON chunk(msg_id);
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(text, content='chunk', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS chunk_ai AFTER INSERT ON chunk BEGIN
  INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text); END;
CREATE TRIGGER IF NOT EXISTS chunk_ad AFTER DELETE ON chunk BEGIN
  INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES ('delete', old.id, old.text); END;
CREATE TABLE IF NOT EXISTS vector(chunk INTEGER PRIMARY KEY REFERENCES chunk(id), model TEXT, emb BLOB,
  fmt TEXT DEFAULT 'f4');  -- f4 = float32, f2 = float16 (half the disk); always normalized
"""

class Error(Exception):
    pass


def file_sha(p):
    """sha256 of a file read in 1 MB blocks (a big source never sits whole in memory); None if it is not a file."""
    p = Path(p)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def exists():
    return DB.exists()


# ---------- ingestion ----------

def text_chunks(text, target=1200):
    buf = ""
    for par in re.split(r"\n\s*\n", text):
        if buf and len(buf) + len(par) > target:
            yield buf
            buf = ""
        buf += ("\n\n" if buf else "") + par
        while len(buf) > 2 * target:  # giant paragraph (a single line): hard cut
            yield buf[:target]
            buf = buf[target:]
    if buf.strip():
        yield buf


def msg_text(t):
    """Telegram Desktop stores `text` as a string or as a list of pieces with entities."""
    if isinstance(t, list):
        return "".join(x if isinstance(x, str) else x.get("text", "") for x in t)
    return t or ""


def read_chat(p):
    """Messages from a Telegram Desktop export (result.json) or from a JSONL {id, ts, author, text}."""
    if p.suffix == ".jsonl":
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                m = json.loads(l)
                yield str(m.get("id")), m.get("ts"), m.get("author"), m.get("text") or ""
        return
    for m in json.loads(p.read_text(encoding="utf-8")).get("messages", []):
        if m.get("type", "message") == "message":
            yield str(m.get("id")), m.get("date"), m.get("from") or m.get("actor"), msg_text(m.get("text"))


def detect(p):
    if p.suffix.lower() == ".pdf":
        return "pdf"
    if p.suffix == ".jsonl":
        head = p.read_text(encoding="utf-8", errors="replace")[:2000]
        return "chat" if '"text"' in head else "text"
    if p.suffix == ".json":
        head = p.read_text(encoding="utf-8", errors="replace")[:4000]
        return "chat" if '"messages"' in head else "text"
    return "text"


def pdf_pages(a):
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", str(a), "-"], capture_output=True, text=True).stdout.split("\f")
    try:
        import pypdf
    except ImportError:
        raise Error("a PDF needs pdftotext (poppler-utils) or the pypdf package")
    return [pg.extract_text() or "" for pg in pypdf.PdfReader(str(a)).pages]


def add_text(db, collection, ref, title, text, typ="text", kind="section"):
    """Ingests a text that is not in a file (e.g. generated text). Replaces the document if the content changed."""
    db.execute("INSERT OR IGNORE INTO collection(name) VALUES (?)", (collection,))
    sha = hashlib.sha256(text.encode()).hexdigest()
    old = db.execute("SELECT * FROM document WHERE collection=? AND ref=?", (collection, ref)).fetchone()
    if old and old["sha"] == sha:
        return old["id"]
    if old:
        db.execute("DELETE FROM vector WHERE chunk IN (SELECT id FROM chunk WHERE document=?)", (old["id"],))
        db.execute("DELETE FROM chunk WHERE document=?", (old["id"],))
        db.execute("DELETE FROM document WHERE id=?", (old["id"],))
    did = db.execute("INSERT INTO document(collection, ref, title, sha, type) VALUES (?,?,?,?,?)",
                     (collection, ref, title, sha, typ)).lastrowid
    for i, pd in enumerate(text_chunks(text) if kind == "section" else [text]):
        db.execute("INSERT INTO chunk(document, kind, position, text) VALUES (?,?,?,?)", (did, kind, i, pd))
    return did


TEXT = {".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".html", ".htm", ".xml", ".log", ".yaml", ".yml", ".pdf"}


def add(db, collection, path, typ="auto"):
    p = Path(path).resolve()
    if not p.exists():
        raise Error(f"{p} does not exist")
    files = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in TEXT)
    db.execute("INSERT OR IGNORE INTO collection(name) VALUES (?)", (collection,))
    out = []
    for a in files:
        st = a.stat()
        stamp = json.dumps({"size": st.st_size, "mtime_ns": st.st_mtime_ns})
        old = db.execute("SELECT * FROM document WHERE collection=? AND ref=?", (collection, str(a))).fetchone()
        if old and old["meta"] == stamp:  # same size and modification time: not even read
            out.append((old["id"], "unchanged", a))
            continue
        sha = file_sha(a)
        if old and old["sha"] == sha:
            db.execute("UPDATE document SET meta=? WHERE id=?", (stamp, old["id"]))
            out.append((old["id"], "unchanged", a))
            continue
        if old:
            db.execute("DELETE FROM vector WHERE chunk IN (SELECT id FROM chunk WHERE document=?)", (old["id"],))
            db.execute("DELETE FROM chunk WHERE document=?", (old["id"],))
            db.execute("DELETE FROM document WHERE id=?", (old["id"],))
        t = detect(a) if typ == "auto" else typ
        did = db.execute("INSERT INTO document(collection, ref, title, sha, type, meta) VALUES (?,?,?,?,?,?)",
                         (collection, str(a), a.name, sha, t, stamp)).lastrowid
        n = 0
        if t == "chat":
            msgs = list(read_chat(a))
            for i, (mid, ts, author, tx) in enumerate(msgs):
                db.execute("INSERT INTO chunk(document, kind, position, ts, author, msg_id, text) VALUES "
                           "(?,'msg',?,?,?,?,?)", (did, i, ts, author, mid, tx))
            for i in range(0, len(msgs), WINDOW // 2):  # windows overlapping by half
                block = msgs[i:i + WINDOW]
                if block:
                    db.execute("INSERT INTO chunk(document, kind, position, ts, msg_id, text) VALUES "
                               "(?,'window',?,?,?,?)", (did, i, block[0][1], block[0][0],
                                                        "\n".join(f"[{m[0]}] {m[2]}: {m[3]}" for m in block)))
            n = len(msgs)
        elif t == "pdf":
            for i, pg in enumerate(pdf_pages(a)):
                if pg.strip():
                    db.execute("INSERT INTO chunk(document, kind, position, text) VALUES (?,'page',?,?)",
                               (did, i + 1, pg))
                    n += 1
        else:
            txt = a.read_text(encoding="utf-8", errors="replace")
            if a.suffix.lower() in (".html", ".htm"):
                txt = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", txt)))
            for i, pd in enumerate(text_chunks(txt)):
                db.execute("INSERT INTO chunk(document, kind, position, text) VALUES (?,'section',?,?)", (did, i, pd))
                n += 1
        out.append((did, f"indexed ({t}, {n} chunks)", a))
    return out


# ---------- search ----------

def terms(text):
    return re.findall(r"\w{3,}", text.lower())[:24]


def _filter(collection, author, where=None):
    sql, args = "", []
    for cond in where or []:  # key=value over the meta JSON (e.g. lang=pt)
        k, _, v = cond.partition("=")
        sql += " AND CAST(json_extract(p.meta, ?) AS TEXT)=?"
        args += [f"$.{k}", v]
    if collection:
        sql += " AND d.collection=?"
        args.append(collection)
    if author:
        sql += " AND p.author LIKE ?"
        args.append(f"%{author}%")
    return sql, args


def bm25(db, q, collection=None, author=None, n=8, where=None):
    ws = terms(q)
    if not ws:
        return []
    f, args = _filter(collection, author, where)
    return [r["id"] for r in db.execute(
        "SELECT p.id FROM chunk_fts JOIN chunk p ON p.id=chunk_fts.rowid JOIN document d ON d.id=p.document "
        f"WHERE chunk_fts MATCH ? {f} ORDER BY bm25(chunk_fts) LIMIT ?",
        [" OR ".join(f'"{w}"' for w in ws), *args, n]).fetchall()]


def literal(db, q, collection=None, author=None, n=8, where=None):
    """Exact substring in the raw text (respects case, line breaks and spaces)."""
    f, args = _filter(collection, author, where)
    return [r["id"] for r in db.execute(
        f"SELECT p.id FROM chunk p JOIN document d ON d.id=p.document WHERE instr(p.text, ?) > 0 {f} "
        "ORDER BY p.kind='window', p.id LIMIT ?", [q, *args, n]).fetchall()]


def embed_model():
    return os.environ.get("HOLMES_EMBED_MODEL") or ""


def embed_texts(texts):
    url, model = os.environ.get("HOLMES_EMBED_URL"), embed_model()
    if not url:
        raise Error("vector search without a server: set HOLMES_EMBED_URL (and HOLMES_EMBED_MODEL)")
    if url == "fake":  # tests only: bag of hashed words, always the same dimension
        out = []
        for t in texts:
            v = [0.0] * 64
            for w in terms(t):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
            out.append(v)
        return out
    req = urllib.request.Request(url.rstrip("/") + "/api/embed", json.dumps({"model": model, "input": texts}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["embeddings"]


def normalize(v):
    s = math.sqrt(sum(x * x for x in v)) or 1.0
    return array.array("f", (x / s for x in v))


def embed(db, collection=None, batch=32):
    model = embed_model() or os.environ.get("HOLMES_EMBED_URL", "")
    f, args = _filter(collection, None)
    pend = db.execute(f"SELECT p.id, p.text FROM chunk p JOIN document d ON d.id=p.document WHERE p.kind != 'msg' "
                      f"AND p.id NOT IN (SELECT chunk FROM vector WHERE model=?) {f}", [model, *args]).fetchall()
    for i in range(0, len(pend), batch):
        block = pend[i:i + batch]
        for r, v in zip(block, embed_texts([x["text"][:4000] for x in block])):
            db.execute("INSERT OR REPLACE INTO vector(chunk, model, emb) VALUES (?,?,?)", (r["id"], model, normalize(v).tobytes()))
        db.commit()
    return len(pend)


def vector_search(db, q, collection=None, author=None, n=8, where=None):
    model = embed_model() or os.environ.get("HOLMES_EMBED_URL", "")
    qv = normalize(embed_texts([q])[0])
    f, args = _filter(collection, author, where)
    rows = db.execute(f"SELECT v.chunk, v.emb, v.fmt FROM vector v JOIN chunk p ON p.id=v.chunk JOIN document d "
                      f"ON d.id=p.document WHERE v.model=? {f}", [model, *args]).fetchall()
    if not rows:
        raise Error("no vector for this model/collection: run `corpus.py embed` first")
    try:  # numpy speeds a big corpus up a lot; without it, a plain dot product
        import numpy as np
        m = np.vstack([np.frombuffer(r["emb"], dtype=np.float16 if r["fmt"] == "f2" else np.float32) for r in rows])
        v = np.frombuffer(qv.tobytes(), dtype=np.float32)[: m.shape[1]]  # Matryoshka model truncated at indexing time
        sc = m.astype(np.float32) @ (v / (np.linalg.norm(v) or 1.0))
        order = np.argsort(-sc)[:n]
        return [rows[i]["chunk"] for i in order]
    except ImportError:
        dec = lambda r: struct.unpack(f"{len(r['emb']) // 2}e", r["emb"]) if r["fmt"] == "f2" else array.array("f", r["emb"])
        sc = [(sum(a * b for a, b in zip(dec(r), qv)), r["chunk"]) for r in rows]
        return [p for _, p in sorted(sc, reverse=True)[:n]]


def search(db, q, collection=None, author=None, n=8, mode="bm25", where=None):
    if mode == "literal":
        return literal(db, q, collection, author, n, where)
    if mode == "vector":
        return vector_search(db, q, collection, author, n, where)
    if mode == "hybrid":  # rank fusion (RRF): robust without calibrating different scales
        sc = {}
        for ranked in (bm25(db, q, collection, author, n * 3, where), vector_search(db, q, collection, author, n * 3, where)):
            for i, p in enumerate(ranked):
                sc[p] = sc.get(p, 0) + 1 / (60 + i)
        return [p for p, _ in sorted(sc.items(), key=lambda x: -x[1])[:n]]
    return bm25(db, q, collection, author, n, where)


def chunk(db, cid):
    r = db.execute("SELECT p.*, d.collection, d.ref, d.title FROM chunk p JOIN document d ON d.id=p.document "
                   "WHERE p.id=?", (cid,)).fetchone()
    if not r:
        raise Error(f"chunk {cid} does not exist")
    return r


def line(r, q=""):
    where = f"msg {r['msg_id']}" if r["kind"] == "msg" else f"{r['kind']} {r['position']}"
    who = f" {r['author']}:" if r["author"] else ""
    if r["meta"]:
        who = f" {{{', '.join(f'{k}={v}' for k, v in json.loads(r['meta']).items())}}}" + who
    tx = " ".join(r["text"].split())
    ws = terms(q)
    i = min((tx.lower().find(w) for w in ws if w in tx.lower()), default=0)
    excerpt = tx[max(0, i - 60):i + 160]
    return f"#{r['id']} [{r['collection']}/{r['title']} {where}{(' ' + r['ts'][:10]) if r['ts'] else ''}]{who} {excerpt}"


def window(db, collection, msg_id, k=5):
    r = db.execute("SELECT p.* FROM chunk p JOIN document d ON d.id=p.document WHERE d.collection=? AND p.kind='msg' "
                   "AND p.msg_id=?", (collection, str(msg_id))).fetchone()
    if not r:
        raise Error(f"message {msg_id} is not in {collection}")
    return db.execute("SELECT * FROM chunk WHERE document=? AND kind='msg' AND position BETWEEN ? AND ? ORDER BY position",
                      (r["document"], r["position"] - k, r["position"] + k)).fetchall()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="corpus.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("collection"); s.add_argument("path")
    s.add_argument("--type", default="auto", choices=["auto", "text", "chat", "pdf"])
    s = sub.add_parser("search"); s.add_argument("text"); s.add_argument("-c", "--collection")
    s.add_argument("--author"); s.add_argument("-n", type=int, default=8)
    s.add_argument("--mode", default="bm25", choices=["bm25", "literal", "vector", "hybrid"])
    s.add_argument("--where", action="append", help="filter over meta, key=value (repeat for AND)")
    s = sub.add_parser("show"); s.add_argument("chunk", type=int)
    s = sub.add_parser("window"); s.add_argument("collection"); s.add_argument("msg_id"); s.add_argument("-k", type=int, default=5)
    sub.add_parser("collections")
    s = sub.add_parser("embed"); s.add_argument("-c", "--collection"); s.add_argument("--batch", type=int, default=32)
    a = ap.parse_args(argv)
    with connect() as db:
        if a.cmd == "add":
            for did, st, p in add(db, a.collection, a.path, a.type):
                print(f"doc {did} {st}: {p}")
        elif a.cmd == "search":
            ids = search(db, a.text, a.collection, a.author, a.n, a.mode, a.where)
            print("\n".join(line(chunk(db, i), a.text) for i in ids) if ids else
                  "nothing. Try synonyms, --mode literal or --mode hybrid before concluding it does not exist.")
        elif a.cmd == "show":
            r = chunk(db, a.chunk)
            print(f"#{r['id']} {r['collection']} {r['ref']} {r['kind']} {r['msg_id'] or r['position']} "
                  f"{r['ts'] or ''} {r['author'] or ''}\n{r['text']}")
        elif a.cmd == "window":
            for r in window(db, a.collection, a.msg_id, a.k):
                print(f"#{r['id']} [msg {r['msg_id']} {(r['ts'] or '')[:16]}] {r['author']}: {r['text']}")
        elif a.cmd == "collections":
            for r in db.execute("SELECT d.collection, count(DISTINCT d.id) docs, count(p.id) chunks, "
                                "(SELECT count(*) FROM vector v JOIN chunk q ON q.id=v.chunk JOIN document e ON "
                                "e.id=q.document WHERE e.collection=d.collection) vec FROM document d LEFT JOIN chunk p "
                                "ON p.document=d.id GROUP BY d.collection"):
                print(f"{r['collection']}: {r['docs']} documents, {r['chunks']} chunks, {r['vec']} vectors")
        elif a.cmd == "embed":
            print(f"{embed(db, a.collection, a.batch)} chunks embedded")


if __name__ == "__main__":
    try:
        main()
    except Error as e:
        sys.exit(f"corpus: {e}")
