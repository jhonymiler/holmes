#!/usr/bin/env python3
"""corpus — o material da investigação (chats, documentos, livros) em pedaços pesquisáveis.

Um banco por projeto (`corpus/corpus.db`), várias coleções. Nunca é injetado: só consultado.

    python3 -I holmes/corpus.py add <colecao> <arquivo|pasta> [--tipo auto|texto|chat|pdf]
    python3 -I holmes/corpus.py busca "<texto>" [-c colecao] [--autor X] [-n 8] [--modo bm25|literal|vetor|hibrido]
    python3 -I holmes/corpus.py ver <pedaco>                 texto cru inteiro de um pedaço
    python3 -I holmes/corpus.py janela <colecao> <msg_id> [-k 5]   conversa ao redor de uma mensagem
    python3 -I holmes/corpus.py colecoes
    python3 -I holmes/corpus.py embed [-c colecao] [--lote 32]     calcula vetores (precisa de servidor)

Vetores: HOLMES_EMBED_URL (servidor compatível com Ollama, POST /api/embed) e HOLMES_EMBED_MODELO.
HOLMES_EMBED_URL=fake gera vetores determinísticos por hash (só para testes).
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

RAIZ = Path(os.environ.get("HOLMES_RAIZ") or Path(__file__).resolve().parents[1])
DB = Path(os.environ.get("HOLMES_CORPUS") or RAIZ / "corpus" / "corpus.db")
JANELA = 8  # mensagens por janela de contexto

ESQUEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS colecao(nome TEXT PRIMARY KEY, criado TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS documento(id INTEGER PRIMARY KEY, colecao TEXT NOT NULL REFERENCES colecao(nome),
  ref TEXT NOT NULL, titulo TEXT, sha TEXT, tipo TEXT, meta TEXT, UNIQUE(colecao, ref));
CREATE TABLE IF NOT EXISTS pedaco(id INTEGER PRIMARY KEY, documento INTEGER NOT NULL REFERENCES documento(id),
  kind TEXT NOT NULL, ordem INTEGER, ts TEXT, autor TEXT, msg_id TEXT, texto TEXT NOT NULL, meta TEXT);
CREATE INDEX IF NOT EXISTS pedaco_doc ON pedaco(documento, kind, ordem);
CREATE INDEX IF NOT EXISTS pedaco_msg ON pedaco(msg_id);
CREATE VIRTUAL TABLE IF NOT EXISTS pedaco_fts USING fts5(texto, content='pedaco', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS pedaco_ai AFTER INSERT ON pedaco BEGIN
  INSERT INTO pedaco_fts(rowid, texto) VALUES (new.id, new.texto); END;
CREATE TRIGGER IF NOT EXISTS pedaco_ad AFTER DELETE ON pedaco BEGIN
  INSERT INTO pedaco_fts(pedaco_fts, rowid, texto) VALUES ('delete', old.id, old.texto); END;
CREATE TABLE IF NOT EXISTS vetor(pedaco INTEGER PRIMARY KEY REFERENCES pedaco(id), modelo TEXT, emb BLOB,
  fmt TEXT DEFAULT 'f4');  -- f4 = float32, f2 = float16 (metade do disco); sempre normalizado
"""


class Erro(Exception):
    pass


def conecta():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(ESQUEMA)
    return db


def existe():
    return DB.exists()


# ---------- ingestão ----------

def pedacos_texto(texto, alvo=1200):
    buf = ""
    for par in re.split(r"\n\s*\n", texto):
        if buf and len(buf) + len(par) > alvo:
            yield buf
            buf = ""
        buf += ("\n\n" if buf else "") + par
        while len(buf) > 2 * alvo:  # parágrafo gigante (uma linha só): corta duro
            yield buf[:alvo]
            buf = buf[alvo:]
    if buf.strip():
        yield buf


def texto_msg(t):
    """Telegram Desktop guarda `text` como string ou lista de pedaços com entidades."""
    if isinstance(t, list):
        return "".join(x if isinstance(x, str) else x.get("text", "") for x in t)
    return t or ""


def le_chat(p):
    """Mensagens de um export do Telegram Desktop (result.json) ou de um JSONL {id, ts, autor, texto}."""
    if p.suffix == ".jsonl":
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                m = json.loads(l)
                yield str(m.get("id")), m.get("ts"), m.get("autor"), m.get("texto") or ""
        return
    for m in json.loads(p.read_text(encoding="utf-8")).get("messages", []):
        if m.get("type", "message") == "message":
            yield str(m.get("id")), m.get("date"), m.get("from") or m.get("actor"), texto_msg(m.get("text"))


def detecta(p):
    if p.suffix.lower() == ".pdf":
        return "pdf"
    if p.suffix == ".jsonl":
        return "chat" if '"texto"' in p.read_text(encoding="utf-8", errors="replace")[:2000] else "texto"
    if p.suffix == ".json":
        cab = p.read_text(encoding="utf-8", errors="replace")[:4000]
        return "chat" if '"messages"' in cab else "texto"
    return "texto"


def paginas_pdf(a):
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", str(a), "-"], capture_output=True, text=True).stdout.split("\f")
    try:
        import pypdf
    except ImportError:
        raise Erro("PDF precisa do pdftotext (poppler-utils) ou do pacote pypdf")
    return [pg.extract_text() or "" for pg in pypdf.PdfReader(str(a)).pages]


def add_texto(db, colecao, ref, titulo, texto, tipo="texto", kind="secao"):
    """Ingere um texto que não está em arquivo (ex.: migração). Substitui o documento se o conteúdo mudou."""
    db.execute("INSERT OR IGNORE INTO colecao(nome) VALUES (?)", (colecao,))
    sha = hashlib.sha256(texto.encode()).hexdigest()
    velho = db.execute("SELECT * FROM documento WHERE colecao=? AND ref=?", (colecao, ref)).fetchone()
    if velho and velho["sha"] == sha:
        return velho["id"]
    if velho:
        db.execute("DELETE FROM vetor WHERE pedaco IN (SELECT id FROM pedaco WHERE documento=?)", (velho["id"],))
        db.execute("DELETE FROM pedaco WHERE documento=?", (velho["id"],))
        db.execute("DELETE FROM documento WHERE id=?", (velho["id"],))
    did = db.execute("INSERT INTO documento(colecao, ref, titulo, sha, tipo) VALUES (?,?,?,?,?)",
                     (colecao, ref, titulo, sha, tipo)).lastrowid
    for i, pd in enumerate(pedacos_texto(texto) if kind == "secao" else [texto]):
        db.execute("INSERT INTO pedaco(documento, kind, ordem, texto) VALUES (?,?,?,?)", (did, kind, i, pd))
    return did


TEXTO = {".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".html", ".htm", ".xml", ".log", ".yaml", ".yml", ".pdf"}


def add(db, colecao, caminho, tipo="auto"):
    p = Path(caminho).resolve()
    if not p.exists():
        raise Erro(f"{p} não existe")
    arqs = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in TEXTO)
    db.execute("INSERT OR IGNORE INTO colecao(nome) VALUES (?)", (colecao,))
    out = []
    for a in arqs:
        sha = hashlib.sha256(a.read_bytes()).hexdigest()
        velho = db.execute("SELECT * FROM documento WHERE colecao=? AND ref=?", (colecao, str(a))).fetchone()
        if velho and velho["sha"] == sha:
            out.append((velho["id"], "sem mudança", a))
            continue
        if velho:
            db.execute("DELETE FROM vetor WHERE pedaco IN (SELECT id FROM pedaco WHERE documento=?)", (velho["id"],))
            db.execute("DELETE FROM pedaco WHERE documento=?", (velho["id"],))
            db.execute("DELETE FROM documento WHERE id=?", (velho["id"],))
        t = detecta(a) if tipo == "auto" else tipo
        did = db.execute("INSERT INTO documento(colecao, ref, titulo, sha, tipo) VALUES (?,?,?,?,?)",
                         (colecao, str(a), a.name, sha, t)).lastrowid
        n = 0
        if t == "chat":
            msgs = list(le_chat(a))
            for i, (mid, ts, autor, tx) in enumerate(msgs):
                db.execute("INSERT INTO pedaco(documento, kind, ordem, ts, autor, msg_id, texto) VALUES "
                           "(?,'msg',?,?,?,?,?)", (did, i, ts, autor, mid, tx))
            for i in range(0, len(msgs), JANELA // 2):  # janelas sobrepostas pela metade
                bloco = msgs[i:i + JANELA]
                if bloco:
                    db.execute("INSERT INTO pedaco(documento, kind, ordem, ts, msg_id, texto) VALUES "
                               "(?,'janela',?,?,?,?)", (did, i, bloco[0][1], bloco[0][0],
                                                        "\n".join(f"[{m[0]}] {m[2]}: {m[3]}" for m in bloco)))
            n = len(msgs)
        elif t == "pdf":
            for i, pg in enumerate(paginas_pdf(a)):
                if pg.strip():
                    db.execute("INSERT INTO pedaco(documento, kind, ordem, texto) VALUES (?,'pagina',?,?)",
                               (did, i + 1, pg))
                    n += 1
        else:
            txt = a.read_text(encoding="utf-8", errors="replace")
            if a.suffix.lower() in (".html", ".htm"):
                txt = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", txt)))
            for i, pd in enumerate(pedacos_texto(txt)):
                db.execute("INSERT INTO pedaco(documento, kind, ordem, texto) VALUES (?,'secao',?,?)", (did, i, pd))
                n += 1
        out.append((did, f"indexado ({t}, {n} pedaços)", a))
    return out


# ---------- busca ----------

def termos(texto):
    return re.findall(r"\w{3,}", texto.lower())[:24]


def _filtro(colecao, autor, onde=None):
    sql, args = "", []
    for cond in onde or []:  # chave=valor sobre o JSON de meta (ex.: lingua=pt)
        k, _, v = cond.partition("=")
        sql += " AND CAST(json_extract(p.meta, ?) AS TEXT)=?"
        args += [f"$.{k}", v]
    if colecao:
        sql += " AND d.colecao=?"
        args.append(colecao)
    if autor:
        sql += " AND p.autor LIKE ?"
        args.append(f"%{autor}%")
    return sql, args


def bm25(db, q, colecao=None, autor=None, n=8, onde=None):
    ws = termos(q)
    if not ws:
        return []
    f, args = _filtro(colecao, autor, onde)
    return [r["id"] for r in db.execute(
        "SELECT p.id FROM pedaco_fts JOIN pedaco p ON p.id=pedaco_fts.rowid JOIN documento d ON d.id=p.documento "
        f"WHERE pedaco_fts MATCH ? {f} ORDER BY bm25(pedaco_fts) LIMIT ?",
        [" OR ".join(f'"{w}"' for w in ws), *args, n]).fetchall()]


def literal(db, q, colecao=None, autor=None, n=8, onde=None):
    """Substring exata no texto cru (respeita maiúsculas, quebras de linha e espaços)."""
    f, args = _filtro(colecao, autor, onde)
    return [r["id"] for r in db.execute(
        f"SELECT p.id FROM pedaco p JOIN documento d ON d.id=p.documento WHERE instr(p.texto, ?) > 0 {f} "
        "ORDER BY p.kind='janela', p.id LIMIT ?", [q, *args, n]).fetchall()]


def embute(textos):
    url, modelo = os.environ.get("HOLMES_EMBED_URL"), os.environ.get("HOLMES_EMBED_MODELO", "")
    if not url:
        raise Erro("busca vetorial sem servidor: defina HOLMES_EMBED_URL (e HOLMES_EMBED_MODELO)")
    if url == "fake":  # só para testes: saco de palavras com hash, mesma dimensão sempre
        out = []
        for t in textos:
            v = [0.0] * 64
            for w in termos(t):
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
            out.append(v)
        return out
    req = urllib.request.Request(url.rstrip("/") + "/api/embed", json.dumps({"model": modelo, "input": textos}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["embeddings"]


def normaliza(v):
    s = math.sqrt(sum(x * x for x in v)) or 1.0
    return array.array("f", (x / s for x in v))


def embed(db, colecao=None, lote=32):
    modelo = os.environ.get("HOLMES_EMBED_MODELO", "") or os.environ.get("HOLMES_EMBED_URL", "")
    f, args = _filtro(colecao, None)
    pend = db.execute(f"SELECT p.id, p.texto FROM pedaco p JOIN documento d ON d.id=p.documento WHERE p.kind != 'msg' "
                      f"AND p.id NOT IN (SELECT pedaco FROM vetor WHERE modelo=?) {f}", [modelo, *args]).fetchall()
    for i in range(0, len(pend), lote):
        bloco = pend[i:i + lote]
        for r, v in zip(bloco, embute([x["texto"][:4000] for x in bloco])):
            db.execute("INSERT OR REPLACE INTO vetor(pedaco, modelo, emb) VALUES (?,?,?)", (r["id"], modelo, normaliza(v).tobytes()))
        db.commit()
    return len(pend)


def vetorial(db, q, colecao=None, autor=None, n=8, onde=None):
    modelo = os.environ.get("HOLMES_EMBED_MODELO", "") or os.environ.get("HOLMES_EMBED_URL", "")
    qv = normaliza(embute([q])[0])
    f, args = _filtro(colecao, autor, onde)
    rows = db.execute(f"SELECT v.pedaco, v.emb, v.fmt FROM vetor v JOIN pedaco p ON p.id=v.pedaco JOIN documento d "
                      f"ON d.id=p.documento WHERE v.modelo=? {f}", [modelo, *args]).fetchall()
    if not rows:
        raise Erro("nenhum vetor para este modelo/coleção: rode `corpus.py embed` antes")
    try:  # numpy acelera muito em corpus grande; sem ele, produto escalar puro
        import numpy as np
        m = np.vstack([np.frombuffer(r["emb"], dtype=np.float16 if r["fmt"] == "f2" else np.float32) for r in rows])
        v = np.frombuffer(qv.tobytes(), dtype=np.float32)[: m.shape[1]]  # modelo Matryoshka truncado na indexação
        sc = m.astype(np.float32) @ (v / (np.linalg.norm(v) or 1.0))
        ordem = np.argsort(-sc)[:n]
        return [rows[i]["pedaco"] for i in ordem]
    except ImportError:
        dec = lambda r: struct.unpack(f"{len(r['emb']) // 2}e", r["emb"]) if r["fmt"] == "f2" else array.array("f", r["emb"])
        sc = [(sum(a * b for a, b in zip(dec(r), qv)), r["pedaco"]) for r in rows]
        return [p for _, p in sorted(sc, reverse=True)[:n]]


def busca(db, q, colecao=None, autor=None, n=8, modo="bm25", onde=None):
    if modo == "literal":
        return literal(db, q, colecao, autor, n, onde)
    if modo == "vetor":
        return vetorial(db, q, colecao, autor, n, onde)
    if modo == "hibrido":  # fusão de ranks (RRF): robusta sem calibrar escalas diferentes
        sc = {}
        for lista in (bm25(db, q, colecao, autor, n * 3, onde), vetorial(db, q, colecao, autor, n * 3, onde)):
            for i, p in enumerate(lista):
                sc[p] = sc.get(p, 0) + 1 / (60 + i)
        return [p for p, _ in sorted(sc.items(), key=lambda x: -x[1])[:n]]
    return bm25(db, q, colecao, autor, n, onde)


def pedaco(db, pid):
    r = db.execute("SELECT p.*, d.colecao, d.ref, d.titulo FROM pedaco p JOIN documento d ON d.id=p.documento "
                   "WHERE p.id=?", (pid,)).fetchone()
    if not r:
        raise Erro(f"pedaço {pid} não existe")
    return r


def linha(r, q=""):
    onde = f"msg {r['msg_id']}" if r["kind"] == "msg" else f"{r['kind']} {r['ordem']}"
    quem = f" {r['autor']}:" if r["autor"] else ""
    if r["meta"]:
        quem = f" {{{', '.join(f'{k}={v}' for k, v in json.loads(r['meta']).items())}}}" + quem
    tx = " ".join(r["texto"].split())
    ws = termos(q)
    i = min((tx.lower().find(w) for w in ws if w in tx.lower()), default=0)
    trecho = tx[max(0, i - 60):i + 160]
    return f"#{r['id']} [{r['colecao']}/{r['titulo']} {onde}{(' ' + r['ts'][:10]) if r['ts'] else ''}]{quem} {trecho}"


def janela(db, colecao, msg_id, k=5):
    r = db.execute("SELECT p.* FROM pedaco p JOIN documento d ON d.id=p.documento WHERE d.colecao=? AND p.kind='msg' "
                   "AND p.msg_id=?", (colecao, str(msg_id))).fetchone()
    if not r:
        raise Erro(f"mensagem {msg_id} não está em {colecao}")
    return db.execute("SELECT * FROM pedaco WHERE documento=? AND kind='msg' AND ordem BETWEEN ? AND ? ORDER BY ordem",
                      (r["documento"], r["ordem"] - k, r["ordem"] + k)).fetchall()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="corpus.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("colecao"); s.add_argument("caminho")
    s.add_argument("--tipo", default="auto", choices=["auto", "texto", "chat", "pdf"])
    s = sub.add_parser("busca"); s.add_argument("texto"); s.add_argument("-c", "--colecao"); s.add_argument("--autor")
    s.add_argument("-n", type=int, default=8); s.add_argument("--modo", default="bm25",
                                                              choices=["bm25", "literal", "vetor", "hibrido"])
    s.add_argument("--onde", action="append", help="filtro sobre meta, chave=valor (repita para E)")
    s = sub.add_parser("ver"); s.add_argument("pedaco", type=int)
    s = sub.add_parser("janela"); s.add_argument("colecao"); s.add_argument("msg_id"); s.add_argument("-k", type=int, default=5)
    sub.add_parser("colecoes")
    s = sub.add_parser("embed"); s.add_argument("-c", "--colecao"); s.add_argument("--lote", type=int, default=32)
    a = ap.parse_args(argv)
    with conecta() as db:
        if a.cmd == "add":
            for did, st, p in add(db, a.colecao, a.caminho, a.tipo):
                print(f"doc {did} {st}: {p}")
        elif a.cmd == "busca":
            ids = busca(db, a.texto, a.colecao, a.autor, a.n, a.modo, a.onde)
            print("\n".join(linha(pedaco(db, i), a.texto) for i in ids) if ids else
                  "nada. Tente sinônimos, --modo literal ou --modo hibrido antes de concluir que não existe.")
        elif a.cmd == "ver":
            r = pedaco(db, a.pedaco)
            print(f"#{r['id']} {r['colecao']} {r['ref']} {r['kind']} {r['msg_id'] or r['ordem']} "
                  f"{r['ts'] or ''} {r['autor'] or ''}\n{r['texto']}")
        elif a.cmd == "janela":
            for r in janela(db, a.colecao, a.msg_id, a.k):
                print(f"#{r['id']} [msg {r['msg_id']} {(r['ts'] or '')[:16]}] {r['autor']}: {r['texto']}")
        elif a.cmd == "colecoes":
            for r in db.execute("SELECT d.colecao, count(DISTINCT d.id) docs, count(p.id) ped, "
                                "(SELECT count(*) FROM vetor v JOIN pedaco q ON q.id=v.pedaco JOIN documento e ON "
                                "e.id=q.documento WHERE e.colecao=d.colecao) vet FROM documento d LEFT JOIN pedaco p "
                                "ON p.documento=d.id GROUP BY d.colecao"):
                print(f"{r['colecao']}: {r['docs']} documentos, {r['ped']} pedaços, {r['vet']} vetores")
        elif a.cmd == "embed":
            print(f"{embed(db, a.colecao, a.lote)} pedaços vetorizados")


if __name__ == "__main__":
    try:
        main()
    except Erro as e:
        sys.exit(f"corpus: {e}")
