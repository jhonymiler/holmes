#!/usr/bin/env python3
"""holmes 2.0 — the investigation's reasoning as one SQLite graph per case (model in MODEL.md).

Tree: objective O → target A → front F → hypothesis H / premise R → test T → run X.
Beside it: fact E (quotes a source S), clue K, entity N, user decision D, thread P, instrument I, question Q,
candidate connection C (a suggested relation, outside the graph until confirmed), reading L (working theory).
The plan is the `map` query; raw material lives in the corpus (holmes/corpus.py).

  case       init <case> "<objective>" · use <case> · cases
  plan       map [--all] · next · show <id> · chain <id> · questions · timeline · health
             search "<txt>" [--no-corpus] · tried "<txt>"
  reading    reading "<the picture>" [--supports E,..] [--weakens E,..] [--rival H,..] [--question Q]
                     [--gap Q,..] [--reason "<why it changed>"]          (no text: shows the current one)
  relations  connections <id|"text"> [-n 8]   (candidates by query; nothing is stored)
             connection <from> <to> <relation> "<why>" [--rival] [--discriminator] [--reasons E,..]
             state C.. confirmed|rejected "<reason>"   (confirmed becomes a graph edge)
  extraction extract <file.json> [--apply] [--only id,..] [--reject id,..]   (contract in MODEL.md)
  create     new <type> "<title>" [--parent ID] [--summary] [--origin] [--grade] [--state]
             [--nature --source S --location --quote --by --proof]   (fact / clue)
             [--prob --refuted-if]                       (hypothesis)
             [--class --alias "a,b"]                     (entity)
             [--forbids --allows]                        (decision)
  change     state <id> <state> "<reason>" [--solution]  · edit <id> [--title] [--summary] [--refuted-if]
             link <from> <type> <to> ["note"] · unlink <from> <type> <to>
             prob <H> <0..1> "<reason>" · ach <E> <H> CC|C|N|I|II · ach <F>   (matrix)
  test       test <H> "<title>" --scope .. --why .. [--outside] [--prediction] [--control --control-type]
                  [--instrument I] [--script] [--force] [--exploratory]
             run <T> [--pid] [--log] [--host]  → X       result <T|X> positive|negative|inconclusive|failed
             "<note>" [--meaning "<what it says>"|"none: <why>"|"revisit: <what>"] [--n ..] [--control-ok]
             jobs
  sources    source <file|folder|url> [--provenance] [--reliability A-F] [--no-corpus]
             quote <corpus chunk> "<claim>" [--nature] [--grade]   prove <K|E> "<note>" --by source|measurement|test|reproduction [--proof ..]
  entities   attribute <N> <key> <value> [--fact E]
  branches   branch new "<question>" --from <id> --why ".." [--step N] · branch use B.. · branch release
             step <type> "<text>" --why ".." [--nodes ..] · tree [id] · trail [B..] · sheet
  proofs     instrument <path> "<name>" [--verifier "cmd"] · proof [--execute] [--legacy]
             (without --execute it only lists: they are shell commands stored in the database)

Environment: HOLMES_ROOT, HOLMES_CASES, HOLMES_CASE (forces the case), HOLMES_TUNNEL (default 5), HOLMES_CORPUS,
HOLMES_READING (default 6: results without an overall reading before the map asks for one).
"""
import argparse
import hashlib
import os
import re
import socket
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus as C  # noqa: E402


ROOT = Path(os.environ.get("HOLMES_ROOT") or Path(__file__).resolve().parents[1])
CASES = Path(os.environ.get("HOLMES_CASES") or ROOT / "cases")
STATE_DIR = ROOT / ".holmes"
ACTIVE = STATE_DIR / "active"
TUNNEL = int(os.environ.get("HOLMES_TUNNEL") or 5)
READING_EVERY = int(os.environ.get("HOLMES_READING") or 6)
MAX_FRONTS, MAX_HYP, MAX_MAP = 5, 7, 3500

PREFIX = {"objective": "O", "target": "A", "front": "F", "hypothesis": "H", "premise": "R", "test": "T",
          "fact": "E", "entity": "N", "decision": "D", "thread": "P", "source": "S", "instrument": "I",
          "reading": "L", "question": "Q", "connection": "C", "branch": "B", "clue": "K"}
TYPE_OF = {v: k for k, v in PREFIX.items()}
STATES = {  # the first one is the initial state
    "objective": ["open", "achieved", "abandoned"],
    "target": ["open", "solved", "blocked"],
    "front": ["active", "parked", "closed", "discarded"],
    "hypothesis": ["alive", "supported", "refuted", "parked"],
    "premise": ["assumed", "verified", "refuted"],
    "test": ["planned", "running", "done", "cancelled"],
    "fact": ["current", "contested", "retracted"],  # a fact is an already proven finding: it is born current
    "clue": ["open", "dropped"],  # what is not proven yet; once proven it becomes a fact (`prove`)
    "entity": ["active", "merged"],
    "decision": ["current", "revoked"],
    "thread": ["open", "closed", "parked"],
    "source": ["catalogued", "indexed"],
    "instrument": ["current", "obsolete"],
    "reading": ["current", "superseded"],
    "question": ["open", "answered", "reformulated", "parked"],
    "connection": ["suggested", "confirmed", "rejected"],
    "branch": ["active", "paused", "dead", "merged", "concluded"],
}
NEEDS_REASON = {"achieved", "abandoned", "solved", "blocked", "parked", "closed", "discarded", "dropped", "refuted",
                "verified", "cancelled", "contested", "retracted", "merged", "revoked", "obsolete", "answered",
                "reformulated", "confirmed", "rejected", "paused", "dead", "concluded"}
FALLEN = {"refuted", "retracted", "contested", "discarded", "dropped", "revoked", "abandoned", "cancelled", "rejected",
          "dead"}
PARENTS = {"target": {"objective", "target"}, "front": {"target", "objective"}, "hypothesis": {"front"},
           "premise": {"front", "target", "objective"}, "test": {"hypothesis"},
           "question": {"objective", "target", "front", "question"}}
ORIGINS = ["author", "source", "measured", "user", "agent", "external"]
NATURES = ["observation", "measurement", "quote", "inference", "interpretation", "report"]
FACT_NATURES = ["observation", "measurement", "quote"]  # inference, interpretation and report are clues
# answers: hypothesis → the question it tries to answer · rival: competing explanation (reading/hypothesis → hypothesis)
EDGES = ["supports", "weakens", "contradicts", "refutes", "depends", "duplicates", "supersedes", "about", "derives",
         "answers", "rival"]
# step: a branch's "commit". Manual ones require --why; recorded/changed/opened/forked are automatic.
MANUAL_STEPS = ["read", "thought", "tested", "found", "corrected", "decided", "next"]
# how a fact becomes proven: a fact is a finding, and the proof need not be a source
PROOFS = ["source", "measurement", "test", "reproduction"]
RESULTS = ["positive", "negative", "inconclusive", "failed"]
PROVENANCES = ["primary", "derived", "third-party", "ours"]
CONTROL_TYPES = ["real", "planted", "sabotage", "none"]
ACH = {"CC": 2, "C": 1, "N": 0, "I": -1, "II": -2}

class Error(Exception):
    pass


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def case_dir(case):
    return CASES / case


def cases():
    return sorted({p.parent.name for p in CASES.glob("*/case.db")})


def read_active():
    return ACTIVE.read_text().strip() if ACTIVE.exists() else ""


def write_active(case):
    STATE_DIR.mkdir(exist_ok=True)
    ACTIVE.write_text(case)


def active_case():
    c = os.environ.get("HOLMES_CASE") or read_active()
    if not c:
        raise Error("no active case: `holmes.py use <case>` (or `init`)")
    if c not in cases():
        raise Error(f"case {c!r} does not exist in {CASES}")
    return c


def case_db(case):
    return case_dir(case) / "case.db"


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS node(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL,
  parent INTEGER REFERENCES node(id), title TEXT NOT NULL CHECK(length(title) <= 160),
  summary TEXT CHECK(length(summary) <= 800), state TEXT NOT NULL, origin TEXT, grade TEXT CHECK(grade IN ('A','B','C')),
  created TEXT NOT NULL, updated TEXT NOT NULL, legacy INTEGER NOT NULL DEFAULT 0, branch INTEGER);
CREATE INDEX IF NOT EXISTS node_parent ON node(parent, type, state);
CREATE TABLE IF NOT EXISTS target(node INTEGER PRIMARY KEY REFERENCES node(id), solution TEXT, proof TEXT);
CREATE TABLE IF NOT EXISTS hypothesis(node INTEGER PRIMARY KEY REFERENCES node(id), prob REAL CHECK(prob BETWEEN 0 AND 1),
  refuted_if TEXT);
CREATE TABLE IF NOT EXISTS test(node INTEGER PRIMARY KEY REFERENCES node(id),
  scope TEXT NOT NULL CHECK(length(scope) <= 600), outside TEXT CHECK(length(outside) <= 600),
  why TEXT NOT NULL CHECK(length(why) <= 600), prediction TEXT, predicted_at TEXT, control TEXT,
  control_type TEXT CHECK(control_type IN ('real','planted','sabotage','none')),
  instrument INTEGER REFERENCES node(id), script TEXT, recipe TEXT, mode TEXT);
CREATE TABLE IF NOT EXISTS run(id INTEGER PRIMARY KEY, test INTEGER NOT NULL REFERENCES node(id),
  version INTEGER REFERENCES version(id), script_sha TEXT, host TEXT, pid INTEGER, log TEXT, started TEXT, finished TEXT,
  n TEXT, control_ok INTEGER, result TEXT CHECK(result IN ('positive','negative','inconclusive','failed')),
  note TEXT, meaning TEXT);
CREATE TABLE IF NOT EXISTS instrument(node INTEGER PRIMARY KEY REFERENCES node(id), path TEXT UNIQUE, verifier TEXT);
CREATE TABLE IF NOT EXISTS version(id INTEGER PRIMARY KEY, instrument INTEGER NOT NULL REFERENCES node(id),
  sha TEXT NOT NULL, at TEXT NOT NULL, verified INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS fact(node INTEGER PRIMARY KEY REFERENCES node(id), nature TEXT, source INTEGER REFERENCES node(id),
  location TEXT, quote TEXT CHECK(length(quote) <= 1000), proven_at TEXT, proof TEXT, proven_by TEXT);
CREATE TABLE IF NOT EXISTS source(node INTEGER PRIMARY KEY REFERENCES node(id), ref TEXT UNIQUE, sha TEXT,
  provenance TEXT CHECK(provenance IN ('primary','derived','third-party','ours')),
  reliability TEXT CHECK(reliability IN ('A','B','C','D','E','F')), document INTEGER);
CREATE TABLE IF NOT EXISTS entity(node INTEGER PRIMARY KEY REFERENCES node(id), class TEXT, aliases TEXT);
CREATE TABLE IF NOT EXISTS attribute(entity INTEGER REFERENCES node(id), key TEXT, value TEXT,
  fact INTEGER REFERENCES node(id), at TEXT, PRIMARY KEY(entity, key));
CREATE TABLE IF NOT EXISTS decision(node INTEGER PRIMARY KEY REFERENCES node(id), forbids TEXT, allows TEXT);
CREATE TABLE IF NOT EXISTS edge(src INTEGER NOT NULL REFERENCES node(id), type TEXT NOT NULL,
  dst INTEGER NOT NULL REFERENCES node(id), note TEXT CHECK(length(note) <= 200), created TEXT, PRIMARY KEY(src, type, dst));
CREATE TABLE IF NOT EXISTS ach(fact INTEGER REFERENCES node(id), hypothesis INTEGER REFERENCES node(id), value TEXT NOT NULL,
  note TEXT, PRIMARY KEY(fact, hypothesis));
CREATE TABLE IF NOT EXISTS legacy(ref TEXT PRIMARY KEY, node INTEGER NOT NULL REFERENCES node(id));
CREATE TABLE IF NOT EXISTS connection(node INTEGER PRIMARY KEY REFERENCES node(id), src INTEGER NOT NULL REFERENCES node(id),
  dst INTEGER NOT NULL REFERENCES node(id), relation TEXT NOT NULL, rival TEXT CHECK(length(rival) <= 400),
  discriminator TEXT CHECK(length(discriminator) <= 400), channel TEXT);
CREATE TABLE IF NOT EXISTS event(id INTEGER PRIMARY KEY, node INTEGER, action TEXT NOT NULL, text TEXT, at TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS idx USING fts5(ref UNINDEXED, text, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS branch(node INTEGER PRIMARY KEY REFERENCES node(id), from_step INTEGER REFERENCES step(id));
CREATE TABLE IF NOT EXISTS step(id INTEGER PRIMARY KEY, branch INTEGER NOT NULL REFERENCES node(id), type TEXT NOT NULL,
  text TEXT NOT NULL CHECK(length(text) <= 400), why TEXT CHECK(length(why) <= 400), nodes TEXT,
  at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS step_branch ON step(branch, id);
"""

def connect(case=None):
    db = sqlite3.connect(case_db(case or active_case()), timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def q(db, sql, *a):
    return db.execute(sql, a).fetchall()


def one(db, sql, *a):
    return db.execute(sql, a).fetchone()


def label(r):
    return f"{PREFIX[r['type']]}{r['id']}"


def an(word):
    return f"{'an' if word[:1] in 'aeiou' else 'a'} {word}"


def get_node(db, ref, typ=None):
    if ":" in str(ref):  # id from another system (e.g. ext:42), stored on import
        l = one(db, "SELECT node FROM legacy WHERE ref=?", str(ref).strip())
        if not l:
            raise Error(f"{ref} is not in the legacy id map")
        ref = str(l["node"])
    m = re.fullmatch(r"([A-Z]?)(\d+)", str(ref).strip())
    if not m:
        raise Error(f"invalid id: {ref!r} (use H12, T30…)")
    r = one(db, "SELECT * FROM node WHERE id=?", int(m[2]))
    if not r:
        raise Error(f"{ref} does not exist")
    if m[1] and PREFIX[r["type"]] != m[1] and {m[1], PREFIX[r["type"]]} != {"E", "K"}:
        raise Error(f"{ref}: node {r['id']} is {an(r['type'])} ({label(r)}), not {an(TYPE_OF.get(m[1], m[1]))}")
    if typ and r["type"] not in ({typ} if isinstance(typ, str) else typ):
        raise Error(f"{ref} is {an(r['type'])}, expected {typ if isinstance(typ, str) else ' or '.join(typ)}")
    return r


def node_by_id(db, i):
    return one(db, "SELECT * FROM node WHERE id=?", i)


def event(db, node, action, text=""):
    db.execute("INSERT INTO event(node, action, text, at) VALUES (?,?,?,?)", (node, action, (text or "")[:300], now()))


def branch_file(case):
    return STATE_DIR / f"branch-{case}"


def active_branch(db, case):
    for f in (branch_file(case), STATE_DIR / f"ramo-{case}"):
        if f.exists():
            break
    else:
        return None
    try:
        r = one(db, "SELECT * FROM node WHERE id=? AND type='branch'", int(f.read_text().strip()))
    except ValueError:
        return None
    return r if r and r["state"] == "active" else None


def set_branch(case, node):
    STATE_DIR.mkdir(exist_ok=True)
    (STATE_DIR / f"ramo-{case}").unlink(missing_ok=True)
    if node is None:
        branch_file(case).unlink(missing_ok=True)
    else:
        branch_file(case).write_text(str(node))


CURRENT = {"branch": None}  # active branch of this invocation: create(), state and result record steps in it


def add_step(db, branch, typ, text, why=None, nodes=()):
    why = (why or "")[:400]  # the full reason stays on the node (test, event); the step keeps the summary
    sid = db.execute("INSERT INTO step(branch, type, text, why, nodes, at) VALUES (?,?,?,?,?,?)",
                     (branch, typ, text[:400], why or None, ",".join(nodes) or None, now())).lastrowid
    db.execute("UPDATE node SET updated=? WHERE id=?", (now(), branch))
    index_node(db, branch)
    return sid


def index_node(db, node):
    r = one(db, "SELECT * FROM node WHERE id=?", node)
    parts = [r["title"], r["summary"] or ""] + [x["ref"] for x in q(db, "SELECT ref FROM legacy WHERE node=?", node)]
    for sql in ("SELECT scope, outside, why, prediction FROM test WHERE node=?",
                "SELECT quote, location FROM fact WHERE node=?", "SELECT class, aliases FROM entity WHERE node=?",
                "SELECT forbids, allows FROM decision WHERE node=?", "SELECT refuted_if FROM hypothesis WHERE node=?",
                "SELECT solution FROM target WHERE node=?", "SELECT note, meaning FROM run WHERE test=?",
                "SELECT key || ' ' || value FROM attribute WHERE entity=?",
                "SELECT relation, rival, discriminator FROM connection WHERE node=?"):
        for x in q(db, sql, node):
            parts += [str(v) for v in x if v]
    if r["type"] == "branch":  # the path is searchable: "how was X solved?" finds the branch by its steps
        parts += [f"{p['text']} {p['why'] or ''}" for p in q(db, "SELECT text, why FROM step WHERE branch=?", node)]
    db.execute("DELETE FROM idx WHERE ref=?", (str(node),))
    db.execute("INSERT INTO idx(ref, text) VALUES (?,?)", (str(node), " ".join(parts)))


def touch(db, node, action, text=""):
    # touching an inherited item brings it to the present: it enters the map's alerts again
    db.execute("UPDATE node SET updated=?, legacy=0 WHERE id=?", (now(), node))
    event(db, node, action, text)
    index_node(db, node)


# ---------- create ----------

def proof_of(db, by, proof, where=None):
    """A fact is a proven finding: says how (source, measurement, test, reproduction) and with what.
    `where`: for --by source, the source, quote or locator the proof points to."""
    if by not in PROOFS:
        raise Error("a fact requires --by source|measurement|test|reproduction: how it is proven. "
                    "Without a proof yet, it is a clue (`new clue`)")
    if by == "source" and not (where or "").strip():
        raise Error("--by source must point to the source: --source S.. or --location \"<where it is>\" "
                    "(a fact created with `new fact` may also carry --quote \"<literal excerpt>\"; a literal quote "
                    "from the corpus: use `quote`)")
    if by in ("measurement", "reproduction") and not (proof or "").strip():
        raise Error(f"--by {by} requires --proof \"<command or record that reproduces the finding>\"")
    if by == "test":
        if not (proof or "").strip():
            raise Error("--by test requires --proof T.. (the test whose result proves the finding)")
        t = get_node(db, proof, "test")
        res, v = result_of(db, t["id"]), validity(db, t["id"])
        if res != "positive" or v:
            raise Error(f"{label(t)} proves nothing: result {res or 'none'}" + (f", {v}" if v else "")
                        + ". Only a valid positive (with instrument, control seen, not exploratory) proves")
        proof = label(t)
    return by, proof


def create(db, typ, title, parent=None, summary=None, origin=None, grade=None, state=None, force=False, **x):
    if typ not in STATES:
        raise Error(f"invalid type {typ!r}; use: {', '.join(STATES)}")
    if len(title) > 160:
        raise Error(f"title with {len(title)} characters (max. 160): the detail goes in --summary")
    if summary and len(summary) > 800:
        raise Error(f"summary with {len(summary)} characters (max. 800): one conclusion per item; material goes to the corpus")
    if origin and origin not in ORIGINS:
        raise Error(f"invalid origin; use: {', '.join(ORIGINS)}")
    p = get_node(db, parent) if parent else None
    if typ in PARENTS and (not p or p["type"] not in PARENTS[typ]):
        raise Error(f"{typ} needs --parent of type {' or '.join(sorted(PARENTS[typ]))}")
    if typ == "branch" and not p:
        raise Error("a branch needs --from: the point (question, hypothesis, target, branch…) it grows from")
    if typ == "objective" and one(db, "SELECT 1 FROM node WHERE type='objective'"):
        raise Error("the case already has an objective (only one); sub-problems are targets")
    state = state or None
    if typ == "front" and (state or "active") == "active" and not force:
        n = one(db, "SELECT count(*) FROM node WHERE type='front' AND state='active'")[0]
        if n >= MAX_FRONTS:
            raise Error(f"there are already {n} active fronts (max. {MAX_FRONTS}): park or close one first")
    if typ == "hypothesis" and not force:
        n = one(db, "SELECT count(*) FROM node WHERE type='hypothesis' AND state='alive' AND parent=?", p["id"])[0]
        if n >= MAX_HYP:
            raise Error(f"{label(p)} already has {n} live hypotheses (max. {MAX_HYP}): refute or park one")
    if typ == "fact" and not grade:
        grade = "A"  # a fact is created proven (--by): checked against the source or reproduced is grade A
    if origin == "external" and not grade:
        grade = "C"  # subagent, another AI, community: grade C until proven (`prove --by`)
    state = state or STATES[typ][0]
    if state not in STATES[typ]:
        raise Error(f"state {state!r} is invalid for {typ}; use: {', '.join(STATES[typ])}")
    t = now()
    node = db.execute("INSERT INTO node(type, parent, title, summary, state, origin, grade, created, updated) "
                      "VALUES (?,?,?,?,?,?,?,?,?)", (typ, p["id"] if p else None, title, summary, state,
                                                     origin or "agent", grade, t, t)).lastrowid
    if typ in ("fact", "clue"):
        nat = x.get("nature") or "observation"
        if nat not in NATURES:
            raise Error(f"invalid nature; use: {', '.join(NATURES)}")
        by, proof = None, x.get("proof")
        if typ == "fact":
            if nat not in FACT_NATURES:
                raise Error(f"{nat} is not a fact: a fact is a proven finding. Record it as a clue "
                            f"(`new clue \"..\" --nature {nat}`) or, if it is a testable explanation, as a hypothesis")
            by, proof = proof_of(db, x.get("by"), proof, x.get("source") or x.get("quote") or x.get("location"))
        source = get_node(db, x["source"], "source")["id"] if x.get("source") else None
        db.execute("INSERT INTO fact(node, nature, source, location, quote, proof, proven_at, proven_by) "
                   "VALUES (?,?,?,?,?,?,?,?)", (node, nat, source, x.get("location"), x.get("quote"), proof,
                                                t if by else None, by))
        if source:
            db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (node, "derives", source, None, t))
    elif typ == "hypothesis":
        db.execute("INSERT INTO hypothesis VALUES (?,?,?)", (node, x.get("prob"), x.get("refuted_if")))
    elif typ == "entity":
        db.execute("INSERT INTO entity VALUES (?,?,?)", (node, x.get("cls"), x.get("alias")))
    elif typ == "decision":
        db.execute("INSERT INTO decision VALUES (?,?,?)", (node, x.get("forbids"), x.get("allows")))
    elif typ == "target":
        db.execute("INSERT INTO target(node) VALUES (?)", (node,))
    elif typ == "branch":
        db.execute("INSERT INTO branch VALUES (?,?)", (node, x.get("from_step")))
    rm = CURRENT["branch"]
    if rm and typ not in ("branch", "objective", "source", "instrument"):  # every finding is born inside a line
        db.execute("UPDATE node SET branch=? WHERE id=?", (rm, node))
        add_step(db, rm, "recorded", f"{PREFIX[typ]}{node} {title}", x.get("why"), (f"{PREFIX[typ]}{node}",))
    event(db, node, "created", f"{typ}: {title}")
    index_node(db, node)
    return node


# ---------- tests and runs ----------

def file_sha(c):
    p = Path(c)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def current_version(db, inst):
    return one(db, "SELECT * FROM version WHERE instrument=? ORDER BY id DESC LIMIT 1", inst)


def last_run(db, test):
    """Last run with a valid result (failed does not count)."""
    return one(db, "SELECT * FROM run WHERE test=? AND result IS NOT NULL AND result != 'failed' "
                   "ORDER BY id DESC LIMIT 1", test)


def validity(db, test):
    """Validity stamp of a test's result. Empty = the conclusion is authorized within the declared scope.
    Separates four things: the run happened; the result was observed; the control passed (seen, not
    declared); the conclusion is authorized (current instrument, versioned script, confirmatory test)."""
    x = last_run(db, test)
    if not x:
        return ""
    t = one(db, "SELECT * FROM test WHERE node=?", test)
    if x["control_ok"] == 0:
        return "INVALID (control failed)"
    if t["mode"] == "exploratory":
        return "exploratory (counts as a clue; neither closes nor confirms)"
    if x["result"] not in ("negative", "positive"):
        return ""
    if x["result"] == "negative" and not x["version"]:
        return "INDETERMINATE (no instrument)"
    cur = current_version(db, t["instrument"]) if t["instrument"] else None
    if x["result"] == "negative" and cur and cur["id"] != x["version"]:
        return "TO REVALIDATE (instrument changed)"
    if t["script"] and not x["script_sha"]:
        return "unversioned script (file missing when run)"
    if t["control_type"] in (None, "none", "planted"):
        return "no real control"
    if x["control_ok"] is None:  # declaring a real control is not the same as seeing it pass
        return "control not confirmed (--control-ok)"
    return ""


def result_of(db, test):
    x = last_run(db, test)
    return x["result"] if x else None


def tunnel(db, front):
    """(negatives in a row, how many of them valid). The first number measures stagnation: an indeterminate
    attempt is also effort without progress. The second is what can support a conclusion (instrument and control seen)."""
    hs = q(db, "SELECT id, created FROM node WHERE type='hypothesis' AND parent=?", front)
    if not hs:
        return 0, 0
    date = lambda t: (t or "")[:19].replace("T", " ")  # inherited rows store '2026-11-20T03:30:26Z'; now() uses a space
    mark = max(date(h["created"]) for h in hs)
    runs = q(db, f"SELECT x.*, tt.mode FROM run x JOIN node t ON t.id=x.test JOIN test tt ON tt.node=x.test "
                 f"WHERE t.parent IN ({','.join('?' * len(hs))}) AND x.result IS NOT NULL AND x.result != 'failed'",
             *[h["id"] for h in hs])
    n = valid = 0
    for x in sorted(runs, key=lambda x: (date(x["finished"]), x["id"])):
        if x["result"] != "negative":
            n, valid, mark = 0, 0, max(mark, date(x["finished"]))
        elif x["control_ok"] != 0 and date(x["finished"]) >= mark:
            n += 1
            valid += bool(x["version"]) and x["control_ok"] == 1 and x["mode"] != "exploratory"
    return n, valid


def tunnel_warning(n, valid):
    return (f"{n} negatives in a row without a new hypothesis ({valid} with instrument and control seen; "
            "the others close nothing, but count as effort without progress)")


def current_reading(db):
    return one(db, "SELECT * FROM node WHERE type='reading' AND state='current' ORDER BY id DESC LIMIT 1")


def reading_basis(db, lt):
    """The working theory tied to the record: what supports it, what weakens it, the rivals, the decisive
    question and the gaps. If a basis falls, the reading shows up in 'depend on something that fell'."""
    parts = []
    for name, sql in (("basis", "SELECT dst i FROM edge WHERE src=? AND type='depends'"),
                      ("against", "SELECT src i FROM edge WHERE dst=? AND type='weakens'"),
                      ("rivals", "SELECT dst i FROM edge WHERE src=? AND type='rival'"),
                      ("decisive question", "SELECT dst i FROM edge WHERE src=? AND type='about' AND note='decisive'"),
                      ("gaps", "SELECT dst i FROM edge WHERE src=? AND type='about' AND note='gap'")):
        rs = [node_by_id(db, x["i"]) for x in q(db, sql, lt["id"])]
        if rs:
            parts.append(f"{name}: " + ", ".join(label(r) + ("✗" if r["state"] in FALLEN else "") for r in rs))
    m = one(db, "SELECT note FROM edge WHERE src=? AND type='supersedes'", lt["id"])
    if m and m["note"]:
        parts.append(f"changed because: {m['note'][:120]}")
    return " · ".join(parts)


def results_since_reading(db):
    """Results recorded after the current overall reading (or all of them, without a reading)."""
    l = current_reading(db)
    return one(db, "SELECT count(*) FROM run WHERE result IS NOT NULL AND result != 'failed' "
                   "AND replace(substr(finished, 1, 19), 'T', ' ') > ?", l["created"] if l else "")[0]


RELEVANT = ((("% positive",), "positive result"), (("%→confirmed",), "connection confirmed"),
            (("%→answered",), "question answered"), (("%→reformulated",), "question reformulated"),
            (("%→refuted",), "hypothesis or premise refuted"), (("%→supported",), "hypothesis supported"),
            (("%→retracted",), "fact retracted"), (("%→contested",), "fact contested"),
            (("%→dropped", "%→discarded"), "clue dropped or front discarded"), (("proven by %", "checked"), "clue or fact proven"),
            (("link contradicts",), "contradiction recorded"))


def relevant_events(db):
    """What happened since the current reading that may change the picture (not just how many tests ran)."""
    l = current_reading(db)
    # by the creation event's id, not by the clock: events in the same second as the reading are not lost
    since = one(db, "SELECT max(id) FROM event WHERE node=? AND action='created'", l["id"])[0] if l else 0
    found = []
    for patterns, name in RELEVANT:
        rs = q(db, "SELECT e.node FROM event e JOIN node n ON n.id=e.node WHERE e.id > ? AND ("
                   + " OR ".join("e.action LIKE ?" for _ in patterns) + ") AND n.legacy=0 ORDER BY e.id",
               since or 0, *patterns)
        if rs:
            found.append(f"{len(rs)} {name} ({', '.join(label(node_by_id(db, r['node'])) for r in rs[:3])})")
    if l:  # a central hypothesis (tied to the reading) changed weight by ≥ 0.2: the picture may have changed
        central = {x[0] for x in q(db, "SELECT dst FROM edge WHERE src=? AND type IN ('rival','depends') UNION "
                                       "SELECT a.src FROM edge a JOIN edge s ON s.dst=a.dst WHERE s.src=? AND "
                                       "s.type='about' AND a.type='answers'", l["id"], l["id"])}
        changed = []
        for e in q(db, "SELECT node, action FROM event WHERE id > ? AND action LIKE 'prob %'", since or 0):
            m = re.fullmatch(r"prob (\S+)→(\S+)", e["action"])
            if e["node"] in central and m and m[1] != "None" and abs(float(m[2]) - float(m[1])) >= 0.2:
                changed.append(f"H{e['node']} {m[1]}→{m[2]}")
        if changed:
            found.append("central hypothesis changed weight (" + ", ".join(changed[:3]) + ")")
    return found


def reading_request(db):
    """Revision of the working theory triggered by an event; the result count is only a reminder."""
    ev = relevant_events(db)
    if ev:
        return ("OVERALL READING requested by event: " + "; ".join(ev) + ". Does this change what the case seems "
                "to tell? If it did, `holmes.py reading \"...\" --supports .. --reason ..`; if not, say why.")
    n = results_since_reading(db)
    if n < READING_EVERY:
        return ""
    l = current_reading(db)
    pend = one(db, "SELECT count(*) FROM run x JOIN node t ON t.id=x.test WHERE x.result IS NOT NULL AND "
                   "x.result != 'failed' AND t.legacy=0 AND (x.meaning IS NULL OR x.meaning LIKE 'revisit:%') AND "
                   "replace(substr(x.finished, 1, 19), 'T', ' ') > ?", l["created"] if l else "")[0]
    return (f"OVERALL READING pending: {n} results since the last one" + (f" ({pend} with meaning pending)" if pend else "")
            + ". Read them together (skill `reading`): taken together, do they change the picture? Update with `holmes.py reading`.")


def alive(pid):
    return bool(pid) and Path(f"/proc/{pid}").exists()


def open_run(db, t, pid=None, log=None, host=None):
    tt = one(db, "SELECT * FROM test WHERE node=?", t["id"])
    v = current_version(db, tt["instrument"]) if tt["instrument"] else None
    if tt["instrument"] and v:
        inst = one(db, "SELECT * FROM instrument WHERE node=?", tt["instrument"])
        s = file_sha(inst["path"])
        if s and s != v["sha"]:  # the instrument changed on disk without being registered: register before running
            vid = db.execute("INSERT INTO version(instrument, sha, at, note) VALUES (?,?,?,?)",
                             (tt["instrument"], s, now(), "detected when running")).lastrowid
            event(db, tt["instrument"], "new version", f"{v['sha'][:12]} → {s[:12]} (detected when running)")
            v = one(db, "SELECT * FROM version WHERE id=?", vid)
    script_sha = file_sha(tt["script"]) if tt["script"] else None
    if tt["script"] and not script_sha:
        print(f"warning: script {tt['script']} not found from here: run without a script version (pass the absolute "
              "path in --script); the result shows 'unversioned script'")
    xid = db.execute("INSERT INTO run(test, version, script_sha, host, pid, log, started) VALUES (?,?,?,?,?,?,?)",
                     (t["id"], v["id"] if v else None, script_sha, host or socket.gethostname(), pid, log, now())).lastrowid
    db.execute("UPDATE node SET state='running', updated=? WHERE id=?", (now(), t["id"]))
    event(db, t["id"], "running", f"X{xid}" + (f" pid {pid}" if pid else "") + (f" log {log}" if log else ""))
    return xid


# ---------- queries ----------

def stamp(db, r):
    if r["type"] == "test":
        res = result_of(db, r["id"])
        v = validity(db, r["id"])
        return (f"→{res}" if res else "") + (f" ⚠ {v}" if v else "")
    if r["type"] == "clue":
        f = one(db, "SELECT * FROM fact WHERE node=?", r["id"])
        return f" {f['nature']}/{r['origin']}/{r['grade'] or '-'}" if f else ""
    if r["type"] == "fact":
        f = one(db, "SELECT * FROM fact WHERE node=?", r["id"])
        return f" {f['nature']}/{r['origin']}/{r['grade'] or '-'}" + (f" proven:{f['proven_by']}" if f["proven_at"] and f["proven_by"]
                                                                       else "" if f["proven_at"] else " unproven")
    if r["type"] == "hypothesis":
        h = one(db, "SELECT prob FROM hypothesis WHERE node=?", r["id"])
        return f" p={h['prob']:.2f}" if h and h["prob"] is not None else ""
    return ""


def line(db, r):
    mark = "✗ " if r["state"] in FALLEN else ""
    return f"{mark}{label(r)} [{r['type']}:{r['state']}{stamp(db, r)}] {r['title']}"


def expand(db, text):
    """Adds to the query the aliases of the entities whose name or alias appears in the text."""
    ws = set(C.terms(text))
    extra = []
    for e in q(db, "SELECT n.title, e.aliases FROM entity e JOIN node n ON n.id=e.node"):
        names = [e["title"]] + [a.strip() for a in (e["aliases"] or "").split(",") if a.strip()]
        if any(set(C.terms(nm)) & ws for nm in names):
            extra += names
    return text + " " + " ".join(extra)


def search(db, text, n=8, tests_only=False, with_corpus=True):
    ws = C.terms(expand(db, text))
    out = []
    if ws:
        for h in q(db, "SELECT ref FROM idx WHERE idx MATCH ? ORDER BY bm25(idx) LIMIT ?",
                   " OR ".join(f'"{w}"' for w in ws), n * 4):
            r = node_by_id(db, int(h["ref"]))
            if not r or (tests_only and r["type"] != "test"):
                continue
            s = line(db, r)
            if tests_only:
                t = one(db, "SELECT * FROM test WHERE node=?", r["id"])
                x = last_run(db, r["id"])
                s += f"\n    scope: {t['scope']}" + (f"\n    outside: {t['outside']}" if t["outside"] else "")
                if x and x["note"]:
                    s += f"\n    result: {x['note'][:200]}"
            out.append(s)
            if len(out) >= n:
                break
    if with_corpus and not tests_only and C.exists():
        try:
            with C.connect() as cdb:
                out += [f"corpus {C.line(C.chunk(cdb, i), text)}" for i in C.bm25(cdb, text, n=3)]
        except Exception as e:  # the corpus is auxiliary; searching the case does not depend on it
            out.append(f"(corpus unavailable: {e})")
    return out


def broken_dependencies(db):
    return q(db, "SELECT a.src, a.dst, a.type FROM edge a JOIN node d ON d.id=a.src JOIN node p ON p.id=a.dst "
                 f"WHERE a.type IN ('depends','derives') AND p.state IN ({','.join('?' * len(FALLEN))}) "
                 f"AND d.state NOT IN ({','.join('?' * len(FALLEN))}) AND d.state != 'superseded'", *FALLEN, *FALLEN)


def contradictions(db):
    return q(db, "SELECT a.src, a.dst FROM edge a JOIN node d ON d.id=a.src JOIN node p ON p.id=a.dst "
                 f"WHERE a.type='contradicts' AND p.state NOT IN ({','.join('?' * len(FALLEN))}) "
                 f"AND d.state NOT IN ({','.join('?' * len(FALLEN))})", *FALLEN, *FALLEN)


def target_free(db, a):
    deps = q(db, "SELECT n.state FROM edge x JOIN node n ON n.id=x.dst WHERE x.src=? AND x.type='depends' "
                 "AND n.type='target'", a)
    return all(d["state"] == "solved" for d in deps)


def build_map(db, case, everything=False):
    """General plan in sections with a fixed budget, in order of what matters most: no big section pushes
    alerts, decisions and threads out (the defect of the v1 dashboard)."""
    L = [f"# MAP — {case}  ({now()[:16]} UTC)"]
    rid = lambda i: label(node_by_id(db, i))
    lim = (lambda n: 10 ** 6) if everything else (lambda n: n)
    more = lambda rs, n, hint: [f"    … +{len(rs) - n} ({hint})"] if len(rs) > n and not everything else []
    for o in q(db, "SELECT * FROM node WHERE type='objective'"):
        L.append(f"OBJECTIVE {label(o)} [{o['state']}]: {o['title']}" + (f"\n  {o['summary'][:300]}" if o["summary"] else ""))
    lt = current_reading(db)
    if lt:
        L.append(f"\nCURRENT READING {label(lt)} ({lt['created'][:10]}; {results_since_reading(db)} results since then):\n  "
                 + " ".join((lt["summary"] or lt["title"]).split())[:lim(400)]
                 + ("…" if len(lt["summary"] or "") > 400 and not everything else ""))
        basis = reading_basis(db, lt)
        L.append("  " + (basis or "no basis linked: `reading ... --supports E..` ties the theory to the evidence"))
    else:
        L.append("\nCURRENT READING: none. Write what the case seems to tell and where we are in that story: "
                 "`holmes.py reading \"...\"`.")
    ra = active_branch(db, case)
    nb = {e: c for e, c in q(db, "SELECT state, count(*) FROM node WHERE type='branch' GROUP BY state")}
    if ra:
        ps = steps_of(db, ra["id"])
        L.append(f"\nACTIVE BRANCH {label(ra)}: {ra['title'][:110]}  ({nb.get('active', 0)} active, {nb.get('paused', 0)} "
                 "paused; `sheet`, `trail`, `tree`)")
        L += [f"  {j}. {p['type']}: {p['text'][:110]}" for j, p in list(enumerate(ps, 1))[-2:]]
    elif nb:
        L.append(f"\nACTIVE BRANCH: none ({sum(nb.values())} branches; `tree` shows them, `branch use B..` picks one)")
    px = next_steps(db)
    L.append("NEXT (`next`): " + " | ".join(f"{a} — {p[:90]}" for a, p in px[:lim(2)]))
    targets = q(db, "SELECT * FROM node WHERE type='target' ORDER BY id")
    open_targets = [a for a in targets if a["state"] != "solved"]
    if targets:
        L.append(f"\nTARGETS ({len(open_targets)} open of {len(targets)}):")
        for a in open_targets[:lim(8)]:
            deps = q(db, "SELECT dst FROM edge WHERE src=? AND type='depends'", a["id"])
            free = a["state"] == "open" and deps and target_free(db, a["id"])
            L.append(f"  {label(a)} [{a['state']}{' · UNBLOCKED' if free else ''}] {a['title'][:90]}"
                     + (f" (depends on {', '.join(rid(d['dst']) for d in deps)})" if deps else ""))
        L += more(open_targets, 8, "`map --all`")
        solved = [a for a in targets if a["state"] == "solved"]
        if solved:
            L.append(f"  solved ({len(solved)}): " + ", ".join(label(a) for a in solved) + "  (`show <id>` gives solution and proof)")
    fronts = q(db, "SELECT * FROM node WHERE type='front' AND state='active' ORDER BY id")
    L.append(f"\nACTIVE FRONTS ({len(fronts)}/{MAX_FRONTS}):")
    alerts = []
    for f in fronts:
        L.append(f"  {label(f)} {f['title'][:90]}" + (f" — {f['summary'][:100]}" if f["summary"] else ""))
        hs = q(db, "SELECT n.*, h.prob FROM node n JOIN hypothesis h ON h.node=n.id WHERE n.parent=? AND n.state IN "
                   "('alive','supported') ORDER BY h.prob DESC, n.id", f["id"])
        for h in hs[:lim(2)]:
            ts = q(db, "SELECT id FROM node WHERE parent=? AND type='test'", h["id"])
            neg = sum(1 for t in ts if result_of(db, t["id"]) == "negative")
            p = f" p={h['prob']:.2f}" if h["prob"] is not None else ""
            L.append(f"    {label(h)} [{h['state']}{p}] {h['title'][:80]}" + (f"  (forms tested {len(ts)}, neg {neg})" if ts else ""))
        L += more(hs, 2, f"`show {label(f)}`")
        prem = q(db, "SELECT * FROM node WHERE parent=? AND type='premise' AND state='assumed'", f["id"])
        if prem:
            L.append("    unverified premises: " + ", ".join(label(r) for r in prem[:lim(6)]))
        n, v = tunnel(db, f["id"])
        if n >= TUNNEL:
            alerts.append(("tunnel", f"TUNNEL in {label(f)}: {tunnel_warning(n, v)}. Stop testing: READING, reread premises "
                           "and the primary source, look for alternative readings, take it to the user."))
    prem_obj = q(db, "SELECT id FROM node WHERE type='premise' AND state='assumed' AND parent IN "
                     "(SELECT id FROM node WHERE type IN ('objective','target'))")
    if prem_obj:
        L.append(f"  unverified general premises ({len(prem_obj)}): " + ", ".join(f"R{r['id']}" for r in prem_obj[:lim(8)]))
    qs = q(db, "SELECT * FROM node WHERE type='question' AND state='open' AND legacy=0 ORDER BY id DESC")
    if qs:
        L.append(f"\nOPEN QUESTIONS ({len(qs)}; `questions`):")
        for x in qs[:lim(3)]:
            none_yet = not one(db, "SELECT 1 FROM edge WHERE dst=? AND type='answers'", x["id"])
            L.append(f"  {label(x)} {x['title'][:90]}" + (" [gap: no hypothesis]" if none_yet else ""))
    nc = one(db, "SELECT count(*) FROM node WHERE type='connection' AND state='suggested'")[0]
    if nc:
        L.append(f"  candidate connections to assess: {nc} (`connections` lists them; confirm or reject with `state C..`)")
    open_tests = q(db, "SELECT * FROM node WHERE type='test' AND state IN ('planned','running') ORDER BY id")
    for t in open_tests:
        x = one(db, "SELECT * FROM run WHERE test=? AND result IS NULL ORDER BY id DESC", t["id"])
        if x and x["pid"] and not alive(x["pid"]):
            alerts.append(("pid", f"{label(t)} 'running' with a dead PID: read the log and record the result."))
    req = reading_request(db)
    if req:
        alerts.insert(0, ("reading", req))
    # Items inherited from another system (legacy=1) stay out of the alerts until someone touches them: otherwise
    # the old debt drowns the new signal. They get a count line, and appear in full in `health`.
    leg = lambda i: one(db, "SELECT legacy FROM node WHERE id=?", i)[0]
    inherited = {}
    for d in broken_dependencies(db):
        if leg(d["src"]) and leg(d["dst"]):
            inherited["broken dependencies"] = inherited.get("broken dependencies", 0) + 1
        else:
            alerts.append(("dep", f"{rid(d['src'])} {d['type']} on {rid(d['dst'])}, which fell: reassess {rid(d['src'])}."))
    for c in contradictions(db):
        if leg(c["src"]) and leg(c["dst"]):
            inherited["contradictions"] = inherited.get("contradictions", 0) + 1
        else:
            alerts.append(("contra", f"open contradiction: {rid(c['src'])} × {rid(c['dst'])} (retract one or resolve it)."))
    stamps = [(validity(db, t["node"]), t["legacy"]) for t in q(db, "SELECT t.node, n.legacy FROM test t JOIN node n ON n.id=t.node")]
    for key, txt in (("INDETERMINATE", "negative(s) without an instrument: INDETERMINATE, they close nothing"),
                     ("TO REVALIDATE", "negative(s) judged by an old instrument version: TO REVALIDATE"),
                     ("INVALID", "result(s) with a failed control: INVALID")):
        n = sum(1 for v, lg in stamps if v.startswith(key) and not lg)
        if n:
            alerts.append((key, f"{n} {txt}."))
        nl = sum(1 for v, lg in stamps if v.startswith(key) and lg)
        if nl:
            inherited[{"INDETERMINATE": "indeterminate negatives", "TO REVALIDATE": "negatives to revalidate",
                       "INVALID": "invalid results"}[key]] = nl
    clues = one(db, "SELECT count(*) FROM node WHERE type='clue' AND state='open' AND legacy=0")[0]
    if clues:
        alerts.append(("clue", f"{clues} open clue(s): prove them (`prove K.. --by ..`, becomes a fact) or drop them "
                               "(`state K.. dropped`)."))
    if inherited:
        alerts.append(("legacy", "inherited, outside the alerts: " + ", ".join(f"{v} {k}" for k, v in inherited.items())
                       + ". Triage one target at a time (`health`); touching an item brings it back."))
    if alerts:
        # group the ones of the same kind so that a repeated kind does not hide the others
        groups = {}
        for k, a in alerts:
            groups.setdefault(k, []).append(a)
        vis = [g[0] + (f"  (+{len(g) - 1} of the same kind: `health`)" if len(g) > 1 else "")
               for g in groups.values()] if not everything else [a for _, a in alerts]
        L.append(f"\nALERTS ({len(alerts)}):")
        L += [f"  ⚠ {a}" for a in vis[:lim(7)]]
    frontier = q(db, "SELECT h.* FROM node h JOIN node f ON f.id=h.parent WHERE h.type='hypothesis' AND h.state='alive' "
                     "AND f.state='active' AND NOT EXISTS (SELECT 1 FROM node t WHERE t.parent=h.id AND t.type='test' "
                     "AND t.state IN ('planned','running')) ORDER BY h.id")
    if frontier:
        L.append(f"\nFRONTIER ({len(frontier)} live hypotheses without an open test): " + ", ".join(label(h) for h in frontier[:lim(12)])
                 + (" …" if len(frontier) > 12 and not everything else ""))
    if open_tests:
        L.append("\nOPEN TESTS:")
        for t in open_tests[:lim(5)]:
            x = one(db, "SELECT * FROM run WHERE test=? AND result IS NULL ORDER BY id DESC", t["id"])
            pid = f" X{x['id']} pid {x['pid']} {'alive' if alive(x['pid']) else 'DEAD'}" if x and x["pid"] else ""
            L.append(f"  {label(t)} [{t['state']}{pid}] {t['title'][:90]}" + (f" log {x['log']}" if x and x["log"] else ""))
        L += more(open_tests, 5, "`jobs`")
    for title, sql, n in (("USER DECISIONS (override any rule)",
                           "SELECT * FROM node WHERE type='decision' AND state='current' AND origin='user' ORDER BY id DESC", 3),
                          ("OPEN THREADS", "SELECT * FROM node WHERE type='thread' AND state='open' ORDER BY id DESC", 5)):
        rs = q(db, sql)
        if rs:
            L.append(f"\n{title} ({len(rs)}):")
            for r in rs[:lim(n)]:
                d = one(db, "SELECT * FROM decision WHERE node=?", r["id"])
                L.append(f"  {label(r)} {r['title'][:100]}" + (f" | forbids: {d['forbids'][:60]}" if d and d["forbids"] else "")
                         + (f" | allows: {d['allows'][:60]}" if d and d["allows"] else ""))
            L += more(rs, n, "`map --all`")
    others = one(db, "SELECT count(*) FROM node WHERE type='decision' AND state='current' AND origin!='user'")[0]
    if others:
        L.append(f"  (+{others} method decisions by the agent: look them up with `search`)")
    ev = q(db, "SELECT e.*, n.type, n.id nid FROM event e LEFT JOIN node n ON n.id=e.node ORDER BY e.id DESC LIMIT ?",
           20 if everything else 3)
    if ev:
        L.append("\nLATEST EVENTS:")
        L += [f"  {e['at'][:16]} {PREFIX.get(e['type'], '')}{e['nid'] or ''} {e['action']}: {' '.join((e['text'] or '').split())[:90]}"
              for e in ev]
    L.append("\nDetail on demand: `show <id>`, `search`, `tried`, `health`. "
             "Do not read whole documents to get your bearings.")
    txt = "\n".join(L)
    if not everything and len(txt) > MAX_MAP and "\n\nLATEST EVENTS:" in txt:  # events orient the least
        start = txt.index("\n\nLATEST EVENTS:")
        txt = txt[:start] + txt[txt.index("\n\nDetail on demand", start):]
    if not everything and len(txt) > MAX_MAP:
        txt = txt[:MAX_MAP - 110] + "\n… [map cut to fit the session start; in full: `holmes.py map --all`]"
    return txt


def show(db, r):
    L = [line(db, r), f"  origin {r['origin']} · created {r['created'][:16]} · updated {r['updated'][:16]}"]
    if r["summary"]:
        L.append(f"  {r['summary']}")
    p, chain_up = r, []
    while p["parent"]:
        p = node_by_id(db, p["parent"])
        chain_up.append(f"{label(p)} {p['title'][:50]}")
    if chain_up:
        L.append("  under: " + " ← ".join(chain_up))
    if r["branch"]:
        rm = node_by_id(db, r["branch"])
        L.append(f"  in branch: {label(rm)} [{rm['state']}] {rm['title'][:80]}")
    for tab in ("test", "fact", "hypothesis", "target", "decision", "entity", "source", "instrument", "connection"):
        x = one(db, f"SELECT * FROM {tab} WHERE node=?", r["id"]) if tab == r["type"] or (tab, r["type"]) == ("fact", "clue") else None
        if x:
            L += [f"  {k}: {x[k]}" for k in x.keys() if k != "node" and x[k] not in (None, "")]
    if r["type"] == "test":
        t = one(db, "SELECT * FROM test WHERE node=?", r["id"])
        for x in q(db, "SELECT x.*, v.sha FROM run x LEFT JOIN version v ON v.id=x.version WHERE x.test=? "
                       "ORDER BY x.id", r["id"]):
            before = ("prediction BEFORE" if t["predicted_at"] and t["predicted_at"] <= (x["started"] or "")
                      else "prediction after or absent")
            L.append(f"  X{x['id']} {x['started'][:16]}→{(x['finished'] or '…')[:16]} {x['result'] or 'running'} "
                     f"instr {(x['sha'] or 'none')[:12]} control_ok={x['control_ok']} n={x['n']} {before} "
                     f"{x['host']} pid {x['pid']} log {x['log']}" + (f"\n     {x['note']}" if x["note"] else "")
                     + (f"\n     meaning: {x['meaning']}" if x["meaning"] else ""))
        v = validity(db, r["id"])
        if v:
            L.append(f"  ⚠ {v}")
    if r["type"] == "instrument":
        L += [f"  version {v['id']} {v['sha'][:12]} {v['at'][:16]} verified={v['verified']} {v['note'] or ''}"
              for v in q(db, "SELECT * FROM version WHERE instrument=? ORDER BY id", r["id"])]
    if r["type"] == "entity":
        L += [f"  · {a['key']} = {a['value']}" + (f" (E{a['fact']})" if a["fact"] else "")
              for a in q(db, "SELECT * FROM attribute WHERE entity=? ORDER BY key", r["id"])]
    if r["type"] == "hypothesis":
        for a in q(db, "SELECT a.value, n.* FROM ach a JOIN node n ON n.id=a.fact WHERE a.hypothesis=?", r["id"]):
            L.append(f"  ACH {a['value']:>2} {label(a)} {a['title'][:70]}")
    if r["type"] == "connection":
        c = one(db, "SELECT * FROM connection WHERE node=?", r["id"])
        for k in ("src", "dst"):
            L.append(f"  {k}: {line(db, node_by_id(db, c[k]))[:140]}")
    if r["type"] == "reading":
        L.append("  " + (reading_basis(db, r) or "no basis linked"))
    for c in q(db, "SELECT c.*, n.state, n.title FROM connection c JOIN node n ON n.id=c.node WHERE c.src=? OR c.dst=?",
               r["id"], r["id"]):
        L.append(f"  ~ candidate connection C{c['node']} [{c['state']}] {c['title'][:90]}")
    kids = q(db, "SELECT * FROM node WHERE parent=? ORDER BY id", r["id"])
    if kids:
        L.append("  children:")
        L += [f"    {line(db, f)}" for f in kids[:30]]
    for arrow, sql in (("→", "SELECT a.type t, a.note, n.* FROM edge a JOIN node n ON n.id=a.dst WHERE a.src=?"),
                       ("←", "SELECT a.type t, a.note, n.* FROM edge a JOIN node n ON n.id=a.src WHERE a.dst=?")):
        for x in q(db, sql, r["id"]):
            fell = " (FELL)" if x["state"] in FALLEN else ""
            L.append(f"  {arrow} {x['t']} {label(x)} {x['title'][:70]}{fell}" + (f" — {x['note']}" if x["note"] else ""))
    L += [f"  · {e['at'][:16]} {e['action']}: {e['text']}"
          for e in q(db, "SELECT * FROM event WHERE node=? ORDER BY id DESC LIMIT 8", r["id"])]
    return "\n".join(L)


def ach_matrix(db, f):
    hs = q(db, "SELECT * FROM node WHERE parent=? AND type='hypothesis' AND state IN ('alive','supported') ORDER BY id", f["id"])
    if not hs:
        return f"{label(f)} has no live hypotheses"
    vals = q(db, f"SELECT * FROM ach WHERE hypothesis IN ({','.join('?' * len(hs))})", *[h["id"] for h in hs])
    facts = sorted({v["fact"] for v in vals})
    cell = {(v["fact"], v["hypothesis"]): v["value"] for v in vals}
    L = ["fact/clue  " + " ".join(f"{label(h):>6}" for h in hs) + "  diagnostic?"]
    for e in facts:
        row = [cell.get((e, h["id"]), "·") for h in hs]
        diag = "yes" if len({x for x in row if x != "·"}) > 1 else "no (same for all)"
        L.append(f"{label(node_by_id(db, e)):<10} " + " ".join(f"{x:>6}" for x in row) + f"  {diag}")
    inc = [sum(-ACH[cell[(e, h['id'])]] for e in facts if (e, h["id"]) in cell and ACH[cell[(e, h['id'])]] < 0) for h in hs]
    L.append("inconsist " + " ".join(f"{x:>6}" for x in inc) + "  (lower = less refuted; counts only I/II)")
    return "\n".join(L)


def health(db):
    L = []
    loose = q(db, "SELECT * FROM node WHERE type IN ('fact','clue') AND id NOT IN (SELECT src FROM edge UNION SELECT dst FROM edge "
                  "UNION SELECT fact FROM ach)")
    if loose:
        L.append(f"{len(loose)} loose fact(s)/clue(s), not linked to a hypothesis/entity: " + ", ".join(label(r) for r in loose[:15]))
    no_source = q(db, "SELECT n.* FROM node n JOIN fact f ON f.node=n.id WHERE n.origin IN ('author','source') "
                      "AND f.source IS NULL AND n.state != 'retracted'")
    if no_source:
        L.append(f"{len(no_source)} fact(s)/clue(s) of origin author/source without --source: " + ", ".join(label(r) for r in no_source[:15]))
    stale = q(db, "SELECT * FROM node WHERE type='test' AND state='planned' AND created < datetime('now','-3 day')")
    if stale:
        L.append(f"{len(stale)} test(s) planned more than 3 days ago: " + ", ".join(label(r) for r in stale[:15]))
    deps = broken_dependencies(db)
    if deps:
        L.append(f"{len(deps)} item(s) depend on something that fell (refuted/retracted): "
                 + ", ".join(f"{d['src']}→{d['dst']}" for d in deps[:40]) + (" …" if len(deps) > 40 else ""))
    cs = contradictions(db)
    if cs:
        L.append(f"{len(cs)} open contradiction(s): " + ", ".join(f"{c['src']}×{c['dst']}" for c in cs[:40]))
    hs = q(db, "SELECT n.* FROM node n JOIN hypothesis h ON h.node=n.id WHERE n.state='alive' AND h.refuted_if IS NULL")
    if hs:
        L.append(f"{len(hs)} live hypothesis(es) without a refutation criterion (--refuted-if): " + ", ".join(label(r) for r in hs[:15]))
    hk = STATE_DIR / "hooks.json"  # written by the hooks themselves when they run: execution seen, not configuration
    try:
        import json
        seen = json.loads(hk.read_text()) if hk.exists() else {}
    except (OSError, ValueError):
        seen = {}
    if not isinstance(seen, dict):
        seen = {}
    seen = {k: str(v) for k, v in seen.items()}
    missing = [h for h in ("start", "prompt", "guard", "stop") if h not in seen]
    L.append("hooks seen running: " + (", ".join(f"{k} {v}" for k, v in sorted(seen.items())) or "none")
             + (f" · never seen: {', '.join(missing)} (check .claude/settings.json and that the folder is trusted)" if missing else ""))
    return "\n".join(L)


# ---------- relations: discovery (query) and candidate connections (record) ----------

# Portuguese and English stopwords: existing case material is in either language
STOPWORDS = set("para com que uma por como mais mas não nao das dos nas nos pelo pela este esta isso isto "
                "ser são foi tem the and that this with from have for are was were which what into than then "
                "them they there their about would could should only also".split())
NUM = re.compile(r"\b(?:\d{2,}|[0-9a-f]{6,})\b", re.I)
SALIENT = ("fact", "clue", "hypothesis", "question", "entity", "premise", "thread", "reading")


def text_of(db, r):
    f = one(db, "SELECT quote FROM fact WHERE node=?", r["id"])
    return " ".join([r["title"], r["summary"] or "", (f["quote"] or "") if f else ""])


def all_words(text):  # C.terms stops at 24 terms (good for a query, bad for comparing long texts)
    return set(re.findall(r"\w{3,}", text.lower()))


def words(text):
    return {w for w in all_words(text) if len(w) >= 4 and w not in STOPWORDS and not w.isdigit()}


def neighbours(db, node):
    return {x[0] for x in q(db, "SELECT dst FROM edge WHERE src=? UNION SELECT src FROM edge WHERE dst=?", node, node)}


def fts(db, terms, join="OR", n=30):
    if not terms:
        return []
    return [int(h["ref"]) for h in q(db, "SELECT ref FROM idx WHERE idx MATCH ? ORDER BY bm25(idx) LIMIT ?",
                                     f" {join} ".join(f'"{w}"' for w in terms), n)]


def candidates(db, text, node=None, n=8):
    """Possible relations for an item (or a text), through five cheap channels. Nothing is stored: it is a query.
    Judging that the relation exists is up to the agent, and confirming it, up to evidence (`connection`/`state`).
    Channels: shared terms; bridge through an entity (name ↔ alias of the same entity, the route to what shares
    no word); common neighbour in the graph; same number or sequence; corpus material."""
    ws, nums = words(text), {m.lower() for m in NUM.findall(text)}
    reasons = {}

    def add(i, channel, txt):
        if i != node:
            reasons.setdefault(i, {}).setdefault(channel, txt)

    for i in fts(db, sorted(ws)[:60]):
        shared = ws & words(text_of(db, node_by_id(db, i)))
        if len(shared) >= (2 if len(ws) > 6 else 1):
            add(i, "terms", "shared terms: " + ", ".join(sorted(shared)[:4]))
    for e in q(db, "SELECT n.id, n.title, e.aliases FROM entity e JOIN node n ON n.id=e.node WHERE n.state='active'"):
        names = [e["title"]] + [a.strip() for a in (e["aliases"] or "").split(",") if a.strip()]
        hit = [nm for nm in names if all_words(nm) and all_words(nm) <= all_words(text)]
        if not hit or e["id"] == node:
            continue
        add(e["id"], "bridge", f"entity the text talks about ('{hit[0]}')")
        for nm in names:
            if nm in hit:
                continue
            for i in fts(db, C.terms(nm), "AND", 15):
                other = node_by_id(db, i)
                if not all_words(nm) <= all_words(text_of(db, other)):
                    continue
                add(i, "bridge", f"bridge N{e['id']} {e['title']}: '{hit[0]}' ↔ '{nm}'")
        for i in neighbours(db, e["id"]):
            add(i, "bridge", f"linked to entity N{e['id']} {e['title']} ('{hit[0]}')")
    if node:
        for v in neighbours(db, node):
            for i in neighbours(db, v) - {node}:
                add(i, "graph", f"common neighbour {label(node_by_id(db, v))}")
    for m in nums:
        for i in fts(db, [m], n=15):
            add(i, "number", f"same number/sequence {m}")
    linked = neighbours(db, node) if node else set()
    recorded = {}
    if node:
        for c in q(db, "SELECT c.*, n.state FROM connection c JOIN node n ON n.id=c.node WHERE c.src=? OR c.dst=?", node, node):
            recorded[c["dst"] if c["src"] == node else c["src"]] = (c["node"], c["state"])
    lines, count = [], {"linked": 0, "rejected": 0}
    weight = {"bridge": 3, "number": 2, "graph": 2, "terms": 1}
    order = sorted(reasons.items(), key=lambda kv: (-sum(weight[c] for c in kv[1]), -kv[0]))
    for i, ms in order:
        r = node_by_id(db, i)
        if not r or r["type"] not in SALIENT or r["state"] in FALLEN:
            continue
        if i in linked:
            count["linked"] += 1
            continue
        note = ""
        if i in recorded:
            if recorded[i][1] == "rejected":
                count["rejected"] += 1
                continue
            note = f"  (already recorded: C{recorded[i][0]} {recorded[i][1]})"
        lines.append(f"  {line(db, r)[:150]}{' (v1)' if r['legacy'] else ''}{note}\n      ← " + "; ".join(ms.values()))
    out = lines[:n]
    footer = [f"(+{len(lines) - n} candidates)"] if len(lines) > n else []
    footer += [f"({count['linked']} already linked in the graph, {count['rejected']} already rejected: left out)"] if any(count.values()) else []
    if C.exists():
        try:
            with C.connect() as cdb:
                try:
                    ids = C.search(cdb, text, n=3, mode="hybrid")
                except Exception:  # no vectors: words only
                    ids = C.bm25(cdb, text, n=3)
                out += [f"  material {C.line(C.chunk(cdb, i), text)[:150]}  (corpus, not recorded: `quote` it if it matters)"
                        for i in ids]
        except Exception as e:
            footer.append(f"(corpus unavailable: {e})")
    return out, footer


def dependents(db, node):
    """Everything that rests on `node`, transitively: X depends on/derives from node, or node supports X."""
    seen, queue = [], [node]
    while queue:
        a = queue.pop()
        for x in q(db, "SELECT src i FROM edge WHERE dst=? AND type IN ('depends','derives') "
                       "UNION SELECT dst FROM edge WHERE src=? AND type='supports'", a, a):
            if x["i"] not in seen and x["i"] != node:
                seen.append(x["i"])
                queue.append(x["i"])
    return seen


def chain(db, r, depth=0, seen=None, tag=""):
    """An item's grounding, going down: what it depends on, what supports or weakens it, down to the source."""
    seen = seen if seen is not None else set()
    seen.add(r["id"])
    fell = "  ⚠ FELL" if r["state"] in FALLEN else ""
    L = [("    " * depth) + (f"{tag} " if tag else "") + line(db, r)[:140] + fell]
    if depth >= 4:
        return L
    kids = [(x["type"], x["id"]) for x in q(db, "SELECT a.type, n.id FROM edge a JOIN node n ON n.id=a.dst WHERE a.src=? "
                                               "AND a.type IN ('depends','derives','answers')", r["id"])]
    kids += [(f"←{x['type']}", x["id"]) for x in q(db, "SELECT a.type, n.id FROM edge a JOIN node n ON n.id=a.src "
                                                      "WHERE a.dst=? AND a.type IN ('supports','weakens','refutes',"
                                                      "'contradicts','rival')", r["id"])]
    kids += [(f"ACH {x['value']}", x["fact"]) for x in q(db, "SELECT * FROM ach WHERE hypothesis=?", r["id"])]
    for kid_tag, i in kids:
        if i not in seen:
            L += chain(db, node_by_id(db, i), depth + 1, seen, kid_tag)
    return L


def questions(db):
    L = []
    for x in q(db, "SELECT * FROM node WHERE type='question' AND state='open' ORDER BY legacy, id"):
        hs = q(db, "SELECT n.*, h.prob FROM edge a JOIN node n ON n.id=a.src JOIN hypothesis h ON h.node=n.id "
                   "WHERE a.dst=? AND a.type='answers' AND n.state IN ('alive','supported')", x["id"])
        clues = one(db, "SELECT count(*) FROM edge WHERE dst=? AND type='about'", x["id"])[0]
        L.append(f"{label(x)} {x['title'][:100]}" + (" (v1)" if x["legacy"] else "") + "\n    "
                 + (f"{len(hs)} hypothesis(es): " + ", ".join(label(h) + (f" p={h['prob']:.2f}" if h["prob"] is not None else "")
                                                             for h in hs) if hs else "GAP: no hypothesis yet")
                 + f" · {clues} clue(s) linked")
    done = one(db, "SELECT count(*) FROM node WHERE type='question' AND state!='open'")[0]
    return "\n".join(L or ["no open question: `new question \"<question>\" --parent <front|target|O>`"]) + \
        (f"\n({done} answered, reformulated or parked: `search`)" if done else "")


def next_steps(db):
    """Explained recommendation of the next step, by criteria verifiable in the record (MODEL.md, 'Next
    step'). Not a numeric ranking: the order is that of the criteria, from what changes course most to least."""
    R = []
    for f in q(db, "SELECT * FROM node WHERE type='front' AND state='active' AND legacy=0"):
        n, v = tunnel(db, f["id"])
        if n >= TUNNEL:
            R.append((f"READING of front {label(f)}, without testing", f"tunnel: {tunnel_warning(n, v)}"))
    lt = current_reading(db)
    if lt:
        fell = [label(node_by_id(db, d["dst"])) for d in broken_dependencies(db) if d["src"] == lt["id"]]
        if fell:
            R.append((f"revise the reading {label(lt)}", f"lost its basis: {', '.join(fell)} fell"))
    ev = relevant_events(db)
    if ev:
        R.append(("revise the overall reading", "; ".join(ev)))
    revalidate = [t for t in q(db, "SELECT n.* FROM node n JOIN test t ON t.node=n.id WHERE n.legacy=0")
                  if validity(db, t["id"]).startswith("TO REVALIDATE")]
    if revalidate:
        R.append((f"run {', '.join(label(t) for t in revalidate[:3])} again with the current instrument (`run`)",
                  f"the instrument changed: {len(revalidate)} negative(s) stopped counting and may be supporting decisions"))
    decisive = one(db, "SELECT n.* FROM edge a JOIN node n ON n.id=a.dst WHERE a.src=? AND a.type='about' AND "
                       "a.note='decisive' AND n.state='open'", lt["id"]) if lt else None
    open_qs = ([decisive] if decisive else []) + q(db, "SELECT * FROM node WHERE type='question' AND state='open' "
                                                       "AND legacy=0 ORDER BY id")
    seen = set()
    for x in open_qs:
        if x["id"] in seen or len(seen) >= 2:
            continue
        seen.add(x["id"])
        tag = "decisive question" if decisive and x["id"] == decisive["id"] else "open question"
        hs = q(db, "SELECT n.*, h.refuted_if, h.prob FROM edge a JOIN node n ON n.id=a.src JOIN hypothesis h ON h.node=n.id "
                   "WHERE a.dst=? AND a.type='answers' AND n.state IN ('alive','supported') ORDER BY h.prob DESC", x["id"])
        if not hs:
            R.append((f"formulate explanations for {label(x)}", f"{tag} without any hypothesis (gap): {x['title'][:70]}"))
        elif len(hs) == 1:
            R.append((f"generate at least one rival of {label(hs[0])} for {label(x)}", f"{tag} with only one explanation"))
        else:
            ids = [h["id"] for h in hs]
            cells = q(db, f"SELECT fact, group_concat(DISTINCT value) v FROM ach WHERE hypothesis IN ({','.join('?' * len(ids))}) "
                          "GROUP BY fact", *ids)
            if not any("," in (c["v"] or "") for c in cells):
                R.append((f"find the discriminator between {', '.join(label(h) for h in hs[:3])}",
                          f"{tag}: no recorded evidence (ACH) weighs differently between them"))
            else:
                h = hs[0]
                R.append((f"a test that separates {label(h)} from the rivals" if h["refuted_if"] else f"give --refuted-if to {label(h)}",
                          f"{tag}: there is discrimination, the leader p={h['prob']}"))
    cs = q(db, "SELECT c.*, n.id cid FROM connection c JOIN node n ON n.id=c.node WHERE n.state='suggested' ORDER BY n.id")
    if cs:
        crossing = [c for c in cs if front_root(db, c["src"]) != front_root(db, c["dst"])]
        c = (crossing or cs)[0]
        R.append((f"assess connection C{c['cid']} ({len(cs)} suggested)",
                  "links different fronts" if crossing else "candidate relation sitting still, neither confirmed nor rejected"))
    clues = q(db, "SELECT DISTINCT n.* FROM node n JOIN edge a ON a.dst=n.id WHERE n.type='clue' AND n.state='open' "
                  "AND a.type IN ('depends','derives') AND n.legacy=0")
    if clues:
        R.append((f"prove or drop clue {', '.join(label(r) for r in clues[:3])}", "there is reasoning resting on an unproven clue"))
    if not R:
        h = one(db, "SELECT n.*, h.prob FROM node n JOIN hypothesis h ON h.node=n.id JOIN node f ON f.id=n.parent WHERE n.state='alive' "
                    "AND n.legacy=0 AND f.state='active' AND h.refuted_if IS NOT NULL AND NOT EXISTS (SELECT 1 FROM node t "
                    "WHERE t.parent=n.id AND t.type='test') ORDER BY h.prob DESC LIMIT 1")
        if h:
            R.append((f"a discriminating test for {label(h)}", "live hypothesis with a criterion and no test"))
    return R or [("READING of the primary source or of the last result", "nothing in the record asks for anything else: "
                  "reading better usually pays more than testing more")]


def front_root(db, i):
    r = node_by_id(db, i)
    while r and r["type"] != "front" and r["parent"]:
        r = node_by_id(db, r["parent"])
    return r["id"] if r and r["type"] == "front" else None


def timeline(db):
    """Happenings in the investigated world (entity --class event with a `when` attribute), not the database log."""
    ev = q(db, "SELECT n.*, a.value at, a.fact FROM node n JOIN entity e ON e.node=n.id LEFT JOIN attribute a ON "
               "a.entity=n.id AND a.key='when' WHERE e.class='event' AND n.state != 'merged' ORDER BY a.value IS NULL, a.value, n.id")
    return "\n".join(f"{e['at'] or '????'}  {label(e)} {e['title'][:110]}" + (f"  (E{e['fact']})" if e["fact"] else "  (date without a fact)")
                     for e in ev) or ("no happening: `new entity \"<what happened>\" --class event` and "
                                      "`attribute N.. when 2019-04-01 --fact E..`")


# ---------- branches: the path of the reasoning ----------

def steps_of(db, branch):
    return q(db, "SELECT * FROM step WHERE branch=? ORDER BY id", branch)


def step_line(p, j, ind):
    s = f"{ind}{j}. {p['type']}: {p['text']}"
    return s + (f"\n{ind}   why: {p['why']}" if p["why"] else "")


def node_line(db, n):
    extra = ""
    if n["type"] == "target" and n["state"] == "solved":
        a = one(db, "SELECT solution FROM target WHERE node=?", n["id"])
        extra = f" ✓ {(a['solution'] or '')[:80]}" if a else ""
    return f"{label(n)} [{n['state']}] {n['title'][:100]}{extra}"


def ancestors(db, r):
    """From the trunk down to r, inclusive: a twig never shows without the path that leads to it."""
    path, i = [], r["id"]
    while i:
        n = node_by_id(db, i)
        path.append(n)
        i = n["parent"]
    return path[::-1]


def cut_at(db, branch, child):
    """Steps of `branch` that `child` inherited: up to the step it was born from, or up to the fork that created it."""
    ps = steps_of(db, branch["id"])
    dp = one(db, "SELECT from_step FROM branch WHERE node=?", child["id"])
    lim = dp["from_step"] if dp and dp["from_step"] else next(
        (p["id"] for p in ps if p["type"] == "forked" and f"B{child['id']}" in (p["nodes"] or "").split(",")), None)
    return [(j, p) for j, p in enumerate(ps, 1) if lim is None or p["id"] <= lim]


def trail(db, r, short=False):
    path, L = ancestors(db, r), []
    for k, n in enumerate(path):
        ind = "  " * k
        L.append(ind + node_line(db, n))
        if n["type"] != "branch":
            continue
        ps = cut_at(db, n, path[k + 1]) if k + 1 < len(path) else list(enumerate(steps_of(db, n["id"]), 1))
        if short and len(ps) > 3:
            L.append(f"{ind}  … {len(ps) - 3} steps before (`trail {label(n)}`)")
            ps = ps[-3:]
        L += [step_line(p, j, ind + "  ") for j, p in ps]
    kids = q(db, "SELECT * FROM node WHERE parent=? AND type='branch' ORDER BY id", r["id"])
    if kids:
        L.append("  " * len(path) + "branches from here: " + "; ".join(f"{label(g)} [{g['state']}] {g['title'][:60]}" for g in kids))
    return "\n".join(L)


def tree(db, case, root=None):
    act = active_branch(db, case)
    shown = {r["id"] for r in q(db, "SELECT id FROM node WHERE type IN ('objective','target')")}
    for r in q(db, "SELECT * FROM node WHERE type='branch'"):
        shown |= {n["id"] for n in ancestors(db, r)}
    nodes = {i: node_by_id(db, i) for i in shown}
    kids = {}
    for n in nodes.values():
        kids.setdefault(n["parent"] if n["parent"] in nodes else None, []).append(n)
    L = []

    def down(n, ind):
        mark = "▶ " if act and n["id"] == act["id"] else ""
        txt = ind + mark + node_line(db, n)
        if n["type"] == "branch":
            ps = steps_of(db, n["id"])
            dp = one(db, "SELECT from_step FROM branch WHERE node=?", n["id"])["from_step"]
            if dp:
                pr = one(db, "SELECT branch FROM step WHERE id=?", dp)
                j = [p["id"] for p in steps_of(db, pr["branch"])].index(dp) + 1
                txt += f"  (from step {j})"
            if ps:
                txt += f"\n{ind}    {len(ps)} steps; last: {ps[-1]['type']}: {ps[-1]['text'][:70]}"
        L.append(txt)
        for c in sorted(kids.get(n["id"], []), key=lambda x: x["id"]):
            down(c, ind + "  ")

    roots = [get_node(db, root)] if root else sorted(kids.get(None, []), key=lambda x: x["id"])
    for n in roots:
        down(n, "")
    return "\n".join(L) or "empty tree"


def sheet(db, case):
    """One page: where we are, why, what is solved, what fell and what the next experiment is."""
    L = [f"# SHEET — {case}  ({now()[:16]} UTC)"]
    for o in q(db, "SELECT * FROM node WHERE type='objective'"):
        L.append(f"OBJECTIVE {label(o)}: {o['title']}")
    r = active_branch(db, case)
    if r:
        path = ancestors(db, r)
        L.append(f"\nIMMEDIATE {label(r)}: {r['title']}")
        L.append("  path: " + " › ".join(f"{label(n)} {n['title'][:40]}" for n in path[:-1]))
        ps = steps_of(db, r["id"])
        L.append(f"\nLATEST STEPS ({len(ps)} in the branch; `trail` gives them all):")
        L += [step_line(p, j, "  ") for j, p in list(enumerate(ps, 1))[-6:]]
        nxt = next((p for p in reversed(ps) if p["type"] == "next"), None)
        L.append("\nNEXT EXPERIMENT: " + (f"{nxt['text']}" + (f" — because {nxt['why']}" if nxt["why"] else "")
                                          if nxt else "none recorded: `step next \"...\" --why \"...\"`"))
        lineage = {n["id"] for n in path}
        siblings = q(db, "SELECT * FROM node WHERE type='branch' AND state IN ('dead','merged','concluded') AND parent IN "
                         f"({','.join('?' * len(lineage))}) ORDER BY id", *lineage)
        if siblings:
            L.append("\nALREADY EXPLORED HERE (do not redo without a new reason):")
            for g in siblings:
                m = one(db, "SELECT why FROM step WHERE branch=? AND type='changed' ORDER BY id DESC", g["id"])
                L.append(f"  {label(g)} [{g['state']}] {g['title'][:70]}" + (f" — {m['why'][:100]}" if m and m["why"] else ""))
    else:
        L.append("\nACTIVE BRANCH: none. `tree` shows the branches; `branch use B..` or `branch new \"...\" --from <id> --why \"...\"`")
    solved = q(db, "SELECT n.*, a.solution FROM node n JOIN target a ON a.node=n.id WHERE n.state='solved' ORDER BY n.id")
    if solved:
        L.append("\nSOLVED (trunk):")
        L += [f"  {label(a)} {a['title'][:70]} — {(a['solution'] or '')[:80]}" for a in solved]
    live = q(db, "SELECT * FROM node WHERE type='branch' AND state IN ('active','paused') ORDER BY id")
    others = [g for g in live if not r or g["id"] != r["id"]]
    if others:
        L.append(f"\nOTHER OPEN LINES ({len(others)}):")
        L += [f"  {label(g)} [{g['state']}] {g['title'][:90]}" for g in others[:8]]
    return "\n".join(L)


def new_connection(db, src, dst, relation, why, rival=None, discriminator=None, origin="agent", reasons=(), channel=None):
    if relation not in EDGES:
        raise Error(f"invalid relation; use: {', '.join(EDGES)}")
    if src["id"] == dst["id"]:
        raise Error("connection from an item to itself")
    if not (why or "").strip():
        raise Error("connection without a justification: say why the relation seems to exist")
    same = one(db, "SELECT c.node, n.state FROM connection c JOIN node n ON n.id=c.node WHERE c.relation=? AND "
                   "((c.src=? AND c.dst=?) OR (c.src=? AND c.dst=?))", relation, src["id"], dst["id"], dst["id"], src["id"])
    if same:
        raise Error(f"already recorded: C{same['node']} ({same['state']}); `show C{same['node']}`")
    node = create(db, "connection", f"{label(src)} {relation}? {label(dst)}: {why}"[:160], summary=why[:800], origin=origin)
    db.execute("INSERT INTO connection VALUES (?,?,?,?,?,?,?)", (node, src["id"], dst["id"], relation, rival, discriminator, channel))
    for m in reasons:
        db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (node, "derives", get_node(db, m)["id"], None, now()))
    index_node(db, node)
    return node


# ---------- extraction: JSON contract → record (MODEL.md, "Extraction contract") ----------

EXTRACTION_KEYS = {"source", "observations", "clues", "interpretations", "questions", "hypotheses", "connections",
                   "discriminators", "impact"}


def extract(db, data, apply=False, only=None, reject=()):
    """Validates the contract, shows the plan and, with apply, writes everything in one transaction (an error in
    any item undoes the whole batch). Local ids (o1, q1…) become case ids; case ids (E42, ext:42) are reused."""
    extra = set(data) - EXTRACTION_KEYS
    if extra:
        raise Error(f"unknown key in the contract: {', '.join(sorted(extra))} (valid: {', '.join(sorted(EXTRACTION_KEYS))})")
    id_map, plan = {}, []
    for key in EXTRACTION_KEYS - {"source", "impact"}:
        for d in data.get(key, []):
            if re.fullmatch(r"[A-Z]\d+", str(d.get("id", ""))):
                raise Error(f"local id {d['id']!r} looks like a case id; use lowercase (o1, q1, h1)")
    use = lambda loc: (only is None or loc in only) and loc not in reject
    exists = lambda ref: bool(re.fullmatch(r"[A-Z]\d+", str(ref))) or ":" in str(ref)

    def ref(x):
        if x in id_map:
            return id_map[x]
        if exists(x):
            return get_node(db, x)["id"]
        raise Error(f"reference {x!r} does not exist in the case nor was created in this batch (selected with --only?)")

    def same(typ, text):
        target = " ".join(text.lower().split())[:160]
        return next((r for r in q(db, "SELECT * FROM node WHERE type=? AND state NOT IN ('retracted','rejected','dropped')", typ)
                     if " ".join(r["title"].lower().split()) == target), None)

    source = data.get("source")
    source_id = label(get_node(db, source, "source")) if source and exists(source) else None
    if source and not source_id:
        raise Error("source: use the S.. id of an already registered source (`holmes.py source <file>` first)")

    def item(d, k):
        if not d.get(k):
            raise Error(f"item without {k!r}: {d}")
        return d[k]

    for o in data.get("observations", []):
        loc = item(o, "id")
        if not use(loc):
            continue
        if o.get("existing"):
            id_map[loc] = get_node(db, o["existing"], ("fact", "clue"))["id"]
            plan.append(f"= {loc} → {label(get_node(db, id_map[loc]))} (already recorded)")
            continue
        nat = o.get("nature", "observation")
        if nat in ("interpretation", "inference"):
            raise Error(f"{loc}: an observation cannot have nature {nat}; put it in 'interpretations'")
        r = same("fact", item(o, "text")) or same("clue", item(o, "text"))
        if r:
            id_map[loc] = r["id"]
            plan.append(f"= {loc} → {label(r)} (same text already recorded; not duplicating)")
            continue
        if apply:
            quote, location = o.get("quote"), o.get("location")
            if o.get("chunk"):  # literal corpus excerpt: copied, not paraphrased
                with C.connect() as cdb:
                    p = C.chunk(cdb, int(o["chunk"]))
                quote, location = p["text"][:1000], location or f"chunk #{p['id']}"
            origin = o.get("origin", "source" if source_id or o.get("chunk") else "measured")
            summary = " · ".join(x for x in (o.get("method") and f"method: {o['method']}",
                                             o.get("limits") and f"limits: {o['limits']}") if x) or None
            # a copied literal quote is already proven; external material never declares itself proven
            by = "source" if o.get("chunk") else (None if origin == "external" else o.get("by"))
            typ_o = "fact" if by and nat in FACT_NATURES else "clue"
            node = create(db, typ_o, o["text"], summary=summary, origin=origin, grade=o.get("grade"), nature=nat,
                          source=o.get("source") or source_id, location=location, quote=quote, by=by, proof=o.get("proof"))
            id_map[loc] = node
        proven = (o.get("chunk") or (o.get("by") and o.get("origin") != "external")) and nat in FACT_NATURES
        if proven and not o.get("chunk") and not apply:  # the preview refuses what writing would refuse
            proof_of(db, o.get("by"), o.get("proof"), o.get("source") or source_id or o.get("quote") or o.get("location"))
        plan.append(f"+ {loc} {'fact' if proven else 'clue'}/{nat}: {o['text'][:90]}")
    for x in data.get("questions", []):
        loc = item(x, "id")
        if not use(loc):
            continue
        r = same("question", item(x, "text"))
        if r:
            id_map[loc] = r["id"]
            plan.append(f"= {loc} → {label(r)} (question already recorded)")
            continue
        if apply:
            parent = x.get("parent") or label(one(db, "SELECT * FROM node WHERE type='objective'"))
            id_map[loc] = create(db, "question", x["text"], ref(parent) if parent in id_map else parent, x.get("summary"))
            for m in x.get("motivated_by", []):
                db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (id_map[loc], "derives", ref(m), None, now()))
        plan.append(f"+ {loc} question: {x['text'][:90]}")
    for p in data.get("clues", []):
        obs = item(p, "obs")
        if not use(obs):
            continue
        about = p.get("about") or label(one(db, "SELECT * FROM node WHERE type='objective'"))
        if apply:
            db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)",
                       (ref(obs), "about", ref(about), (p.get("why") or "")[:200] or None, now()))
        plan.append(f"+ clue {obs} about {about}: {(p.get('why') or '')[:80]}")
    for i in data.get("interpretations", []):
        loc = item(i, "id")
        if not use(loc):
            continue
        if apply:
            alt = i.get("alternatives")
            summary = " · ".join(x for x in (alt and f"alternatives: {alt}", i.get("confidence") and f"confidence: {i['confidence']}") if x)
            id_map[loc] = create(db, "clue", item(i, "text"), summary=summary or None, origin=i.get("origin", "agent"),
                                 nature="interpretation")
            if i.get("about"):
                db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (id_map[loc], "about", ref(i["about"]), None, now()))
        plan.append(f"+ {loc} clue/interpretation (not a fact): {i['text'][:80]}")
    for h in data.get("hypotheses", []):
        loc = item(h, "id")
        if not use(loc):
            continue
        r = same("hypothesis", item(h, "text"))
        if r:
            id_map[loc] = r["id"]
            plan.append(f"= {loc} → {label(r)} (hypothesis already recorded)")
            continue
        if apply:
            id_map[loc] = create(db, "hypothesis", h["text"], item(h, "parent"), h.get("summary"), prob=h.get("prob"),
                                 refuted_if=h.get("refuted_if"))
            for typ, key in (("answers", "answers"), ("derives", "motivated_by"), ("depends", "premises")):
                vals = h.get(key) or []
                for v in [vals] if isinstance(vals, str) else vals:
                    db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (id_map[loc], typ, ref(v), None, now()))
        plan.append(f"+ {loc} hypothesis{'' if h.get('refuted_if') else ' exploratory (no --refuted-if)'}: {h['text'][:80]}")
    if apply:  # rivals after every hypothesis of the batch exists
        for h in data.get("hypotheses", []):
            if use(h["id"]):
                for v in h.get("rivals", []):
                    if use(v) or exists(v):
                        db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (ref(h["id"]), "rival", ref(v), None, now()))
    for k, c in enumerate(data.get("connections", [])):
        loc = c.get("id", f"c{k + 1}")
        if not use(loc):
            continue
        if c.get("state", "suggested") != "suggested":
            raise Error(f"{loc}: a connection from extraction enters only as 'suggested'; confirming requires `state C.. confirmed`")
        if apply:
            node_of = lambda k: node_by_id(db, ref(item(c, k)))
            id_map[loc] = new_connection(db, node_of("from"), node_of("to"), item(c, "relation"), item(c, "why"),
                                         c.get("rival"), c.get("discriminator"), c.get("origin", "agent"),
                                         [str(ref(m)) for m in c.get("reasons", [])], c.get("channel"))
        plan.append(f"+ {loc} candidate connection {c['from']} {c['relation']}? {c['to']}: {c['why'][:70]}")
    for k, d in enumerate(data.get("discriminators", [])):
        loc = d.get("id", f"d{k + 1}")
        if not use(loc):
            continue
        if apply:
            between = d.get("between", [])
            names = [label(node_by_id(db, ref(e))) for e in between]
            node = create(db, "thread", f"Discriminate {' × '.join(names)}: {item(d, 'observation')}"[:160], summary=d["observation"][:800])
            for e in between:
                db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (node, "about", ref(e), None, now()))
            id_map[loc] = node
        plan.append(f"+ {loc} discrimination thread: {d['observation'][:80]}")
    imp = data.get("impact") or {}
    for k in ("plan", "reading"):
        if imp.get(k):
            plan.append(f"! impact on the {k} (not applied by itself): {imp[k][:160]}")
    if apply:
        for node in set(id_map.values()):
            index_node(db, node)
    return plan, id_map


def run_proof(cmd):
    try:
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=600)
        return r.returncode == 0, (r.stdout + r.stderr).strip()[-200:]
    except subprocess.TimeoutExpired:
        return False, "timeout of 600 s"


# ---------- CLI ----------

def parser():
    ap = argparse.ArgumentParser(prog="holmes.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init"); s.add_argument("case"); s.add_argument("objective")
    s = sub.add_parser("use"); s.add_argument("case")
    for name in ("cases", "health", "jobs", "questions", "next", "timeline", "sheet"):
        sub.add_parser(name)
    s = sub.add_parser("proof"); s.add_argument("--execute", action="store_true"); s.add_argument("--legacy", action="store_true")
    s = sub.add_parser("chain"); s.add_argument("id")
    s = sub.add_parser("connections"); s.add_argument("target", nargs="?"); s.add_argument("-n", type=int, default=8)
    s = sub.add_parser("connection"); s.add_argument("src", metavar="from"); s.add_argument("dst", metavar="to")
    s.add_argument("relation", choices=EDGES); s.add_argument("why"); s.add_argument("--rival")
    s.add_argument("--discriminator"); s.add_argument("--reasons")
    s.add_argument("--origin", default="agent", choices=ORIGINS); s.add_argument("--channel")
    s = sub.add_parser("extract"); s.add_argument("file"); s.add_argument("--apply", action="store_true")
    s.add_argument("--only"); s.add_argument("--reject")
    s = sub.add_parser("map"); s.add_argument("--all", action="store_true")
    s = sub.add_parser("new"); s.add_argument("type"); s.add_argument("title")
    for o in ("--parent", "--summary", "--origin", "--grade", "--state", "--nature", "--source", "--location",
              "--quote", "--proof", "--refuted-if", "--alias", "--forbids", "--allows", "--why", "--by"):
        s.add_argument(o)
    s.add_argument("--class", dest="cls"); s.add_argument("--prob", type=float)
    s = sub.add_parser("edit"); s.add_argument("id"); s.add_argument("--title"); s.add_argument("--summary")
    s.add_argument("--refuted-if"); s.add_argument("--script")
    s = sub.add_parser("reading"); s.add_argument("text", nargs="?"); s.add_argument("--title")
    for o in ("--supports", "--weakens", "--rival", "--question", "--gap", "--reason"):
        s.add_argument(o)
    s = sub.add_parser("state"); s.add_argument("id"); s.add_argument("state"); s.add_argument("reason", nargs="?", default="")
    s.add_argument("--solution"); s.add_argument("--proof")
    for name in ("link", "unlink"):
        s = sub.add_parser(name); s.add_argument("src", metavar="from"); s.add_argument("type", choices=EDGES)
        s.add_argument("dst", metavar="to")
        if name == "link":
            s.add_argument("note", nargs="?")
    s = sub.add_parser("prob"); s.add_argument("hypothesis"); s.add_argument("p", type=float); s.add_argument("reason")
    s = sub.add_parser("ach"); s.add_argument("target"); s.add_argument("hypothesis", nargs="?")
    s.add_argument("value", nargs="?", choices=list(ACH)); s.add_argument("--note")
    s = sub.add_parser("test"); s.add_argument("hypothesis"); s.add_argument("title")
    s.add_argument("--scope", required=True); s.add_argument("--why", required=True)
    for o in ("--outside", "--prediction", "--control", "--instrument", "--script", "--summary"):
        s.add_argument(o)
    s.add_argument("--control-type", choices=CONTROL_TYPES)
    s.add_argument("--force", action="store_true"); s.add_argument("--exploratory", action="store_true")
    s = sub.add_parser("run"); s.add_argument("test"); s.add_argument("--pid", type=int); s.add_argument("--log")
    s.add_argument("--host")
    s = sub.add_parser("result"); s.add_argument("target")
    s.add_argument("result", choices=RESULTS); s.add_argument("note")
    s.add_argument("--n"); s.add_argument("--control-ok", choices=["yes", "no"])
    s.add_argument("--meaning")
    for name in ("search", "tried"):
        s = sub.add_parser(name); s.add_argument("text"); s.add_argument("-n", type=int, default=8)
        s.add_argument("--no-corpus", action="store_true")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("source"); s.add_argument("path"); s.add_argument("--title")
    s.add_argument("--provenance", choices=PROVENANCES, default="primary")
    s.add_argument("--reliability", choices=list("ABCDEF")); s.add_argument("--no-corpus", action="store_true")
    s = sub.add_parser("quote"); s.add_argument("chunk", type=int); s.add_argument("claim")
    s.add_argument("--nature", default="quote", choices=NATURES); s.add_argument("--grade", default="B")
    s = sub.add_parser("prove"); s.add_argument("fact", help="clue K.. (becomes a fact) or fact E.. (renews the proof)"); s.add_argument("note")
    s.add_argument("--by", required=True, choices=PROOFS); s.add_argument("--proof")
    s.add_argument("--source"); s.add_argument("--location")
    s = sub.add_parser("attribute"); s.add_argument("entity"); s.add_argument("key"); s.add_argument("value")
    s.add_argument("--fact")
    s = sub.add_parser("branch"); s.add_argument("action", nargs="?", choices=["new", "use", "release"])
    s.add_argument("text", nargs="?", help="new: the line's question · use: the branch id (B..)")
    s.add_argument("--from", dest="src", help="new (required): the node or branch it grows from")
    s.add_argument("--step", type=int, help="new: fork from this step of the --from branch")
    s.add_argument("--why", help="new (required): why this line exists")
    s.add_argument("--summary", help="new: longer description")
    s.add_argument("--no-use", action="store_true", help="new: open it without making it active")
    s = sub.add_parser("step"); s.add_argument("type", choices=MANUAL_STEPS); s.add_argument("text")
    s.add_argument("--why"); s.add_argument("--nodes"); s.add_argument("--branch")
    s = sub.add_parser("tree"); s.add_argument("id", nargs="?")
    s = sub.add_parser("trail"); s.add_argument("id", nargs="?")
    s = sub.add_parser("instrument"); s.add_argument("path"); s.add_argument("name", nargs="?")
    s.add_argument("--verifier")
    return ap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a = parser().parse_args(argv)

    if a.cmd == "init":
        if not re.fullmatch(r"[\w-]+", a.case):
            raise Error("case name: letters, digits, _ and -")
        d = case_dir(a.case)
        if a.case in cases():
            raise Error(f"{a.case} already exists")
        for sd in ("sources", "scripts", "outputs", "notes"):
            (d / sd).mkdir(parents=True, exist_ok=True)
        (d / "CASE.md").write_text(f"# {a.case}\n\nObjective: {a.objective}\n\n<!-- up to 2 KB, by hand: what the case is, "
                                   "local rules, where the sources are. State and plan do NOT go here: they are the `map`. -->\n",
                                   encoding="utf-8")
        with connect(a.case) as db:
            create(db, "objective", a.objective[:160], summary=a.objective if len(a.objective) > 160 else None, origin="user")
        write_active(a.case)
        return print(f"case {a.case} created in {d} and active")
    if a.cmd == "use":
        if a.case not in cases():
            raise Error(f"{a.case} does not exist; cases: {', '.join(cases()) or 'none'}")
        write_active(a.case)
        return print(f"active case: {a.case}")
    if a.cmd == "cases":
        cur = read_active()
        return print("\n".join(f"{'*' if c == cur else ' '} {c}" for c in cases()) or "no case")

    case = active_case()
    with connect(case) as db:
        ra = active_branch(db, case)
        CURRENT["branch"] = ra["id"] if ra else None
        if a.cmd == "map":
            txt = build_map(db, case, a.all)
            (case_dir(case) / "MAP.md").write_text(txt + "\n", encoding="utf-8")  # generated view; never edit
            print(txt)
        elif a.cmd == "new":
            typ = a.type
            if typ == "branch":
                raise Error("a branch is opened with `branch new \"<question>\" --from <id> --why \"<why this line>\"`")
            own = {"source": "source <path>", "instrument": "instrument <path> \"<name>\"",
                   "reading": "reading \"<picture>\" --supports ..", "connection": "connection <from> <to> <relation> \"<why>\"",
                   "test": "test <H> \"<title>\" --scope .. --why .."}
            if typ in own:  # these carry required data that `new` cannot collect
                raise Error(f"{an(typ)} has its own command: `{own[typ]}`")
            node = create(db, typ, a.title, a.parent, a.summary, a.origin, a.grade, a.state, nature=a.nature,
                          source=a.source, location=a.location, quote=a.quote, proof=a.proof, prob=a.prob,
                          refuted_if=a.refuted_if, cls=a.cls, alias=a.alias, forbids=a.forbids, allows=a.allows,
                          why=a.why, by=a.by)
            print(f"{PREFIX[typ]}{node}")
            if typ == "hypothesis" and not a.refuted_if:
                print("tip: --refuted-if \"<what would bring it down>\" makes the hypothesis testable")
        elif a.cmd == "edit":
            r = get_node(db, a.id)
            if a.title:
                if len(a.title) > 160:
                    raise Error("title max. 160")
                db.execute("UPDATE node SET title=? WHERE id=?", (a.title, r["id"]))
            if a.summary is not None:
                if len(a.summary) > 800:
                    raise Error("summary max. 800")
                db.execute("UPDATE node SET summary=? WHERE id=?", (a.summary, r["id"]))
            if a.refuted_if:
                if r["type"] != "hypothesis":
                    raise Error("--refuted-if belongs to a hypothesis")
                db.execute("UPDATE hypothesis SET refuted_if=? WHERE node=?", (a.refuted_if, r["id"]))
            if a.script:
                if r["type"] != "test":
                    raise Error("--script belongs to a test")
                db.execute("UPDATE test SET script=? WHERE node=?", (a.script, r["id"]))
            touch(db, r["id"], "edited", f"before: {r['title']}")
            print(f"{label(r)} edited")
        elif a.cmd == "reading":
            cur = current_reading(db)
            if not a.text:
                if not cur:
                    return print("no overall reading yet: `holmes.py reading \"<what the case seems to tell>\"`")
                return print(show(db, cur) + f"\n  {results_since_reading(db)} result(s) since this reading")
            if len(a.text) > 800:
                raise Error(f"reading with {len(a.text)} characters (max. 800): it is the picture, not the dossier")
            if cur and not (a.reason or "").strip():
                raise Error(f"replacing L{cur['id']} requires --reason: what evidence or event changed the picture?")
            ids = lambda s: [get_node(db, x.strip()) for x in (s or "").split(",") if x.strip()]
            links = ([("depends", e["id"], None, "src") for e in ids(a.supports)]
                     + [("weakens", e["id"], None, "dst") for e in ids(a.weakens)]
                     + [("rival", h["id"], None, "src") for h in ids(a.rival)]
                     + [("about", x["id"], "decisive", "src") for x in ids(a.question)]
                     + [("about", x["id"], "gap", "src") for x in ids(a.gap)])
            title = a.title or " ".join(a.text.split())[:157] + ("…" if len(a.text) > 157 else "")
            node = create(db, "reading", title[:160], summary=a.text, origin="agent")
            for typ, other, note, side in links:  # 'src' = the reading points; 'dst' = the evidence points to the reading
                pair = (node, typ, other) if side == "src" else (other, typ, node)
                db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (*pair, note, now()))
            if cur:
                db.execute("UPDATE node SET state='superseded' WHERE id=?", (cur["id"],))
                db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (node, "supersedes", cur["id"], a.reason[:200], now()))
                touch(db, cur["id"], "superseded", f"L{node}: {a.reason}")
            print(f"L{node} is the current reading" + (f" (supersedes L{cur['id']})" if cur else ""))
            if not a.supports:
                print("warning: reading without --supports: if one of its pieces of evidence falls, no one will warn you")
        elif a.cmd == "state":
            r = get_node(db, a.id)
            new = a.state
            if new not in STATES[r["type"]]:
                raise Error(f"invalid state for {r['type']}; use: {', '.join(STATES[r['type']])}")
            if new in NEEDS_REASON and not a.reason.strip():
                raise Error(f"'{new}' requires a reason (the id of the test, fact or decision that showed it)")
            if r["type"] == "front" and new == "active" and r["state"] != "active":
                if one(db, "SELECT count(*) FROM node WHERE type='front' AND state='active'")[0] >= MAX_FRONTS:
                    raise Error(f"there are already {MAX_FRONTS} active fronts")
            if r["type"] == "hypothesis" and new == "refuted":
                h = one(db, "SELECT refuted_if FROM hypothesis WHERE node=?", r["id"])
                print(f"reminder: refute {label(r)} only if the criterion was met: "
                      f"{h['refuted_if'] or '(no criterion recorded)'}. If it was not, but valid negatives are "
                      "piling up, lower the confidence with `prob` instead of keeping it intact.")
            if r["type"] == "connection" and new == "confirmed":
                c = one(db, "SELECT * FROM connection WHERE node=?", r["id"])
                db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)",
                           (c["src"], c["relation"], c["dst"], f"C{r['id']}: {a.reason}"[:200], now()))
                print(f"relation promoted to the graph: {label(node_by_id(db, c['src']))} {c['relation']} "
                      f"{label(node_by_id(db, c['dst']))}")
            if r["type"] == "connection" and r["state"] == "confirmed" and new != "confirmed":
                c = one(db, "SELECT * FROM connection WHERE node=?", r["id"])
                db.execute("DELETE FROM edge WHERE src=? AND type=? AND dst=? AND note LIKE ?",
                           (c["src"], c["relation"], c["dst"], f"C{r['id']}:%"))
            if r["type"] == "target" and new == "solved":
                if not a.solution:
                    raise Error("a solved target requires --solution (and, if there is one, --proof \"<command that re-proves it>\")")
                db.execute("UPDATE target SET solution=?, proof=? WHERE node=?", (a.solution, a.proof, r["id"]))
            db.execute("UPDATE node SET state=? WHERE id=?", (new, r["id"]))
            touch(db, r["id"], f"{r['state']}→{new}", a.reason)
            where = r["id"] if r["type"] == "branch" else CURRENT["branch"]
            if where:  # a course correction stays in the path, with its reason
                add_step(db, where, "changed", f"{label(r)} {r['state']} → {new}", a.reason.strip() or None, (label(r),))
            if r["type"] == "branch" and new != "active" and CURRENT["branch"] == r["id"]:
                set_branch(case, None)
                print("active branch released: `tree` shows the others; `branch use B..` picks one")
            print(f"{label(r)}: {r['state']} → {new}")
            dep = dependents(db, r["id"])
            if new in FALLEN and dep:
                print("⚠ these depend on it (directly or indirectly) and must be reassessed: "
                      + ", ".join(label(node_by_id(db, d)) for d in dep[:20])
                      + (f" … +{len(dep) - 20}" if len(dep) > 20 else ""))
        elif a.cmd in ("link", "unlink"):
            src, dst = get_node(db, a.src), get_node(db, a.dst)
            if src["id"] == dst["id"]:
                raise Error("edge to itself")
            if a.cmd == "link":
                db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (src["id"], a.type, dst["id"], a.note, now()))
            else:
                db.execute("DELETE FROM edge WHERE src=? AND type=? AND dst=?", (src["id"], a.type, dst["id"]))
            event(db, src["id"], f"{a.cmd} {a.type}", label(dst))
            print(f"{label(src)} {a.type} {label(dst)}" + (" (undone)" if a.cmd == "unlink" else ""))
        elif a.cmd == "prob":
            h = get_node(db, a.hypothesis, "hypothesis")
            if not 0 <= a.p <= 1:
                raise Error("probability between 0 and 1")
            old = one(db, "SELECT prob FROM hypothesis WHERE node=?", h["id"])["prob"]
            db.execute("UPDATE hypothesis SET prob=? WHERE node=?", (a.p, h["id"]))
            touch(db, h["id"], f"prob {old}→{a.p}", a.reason)
            sisters = q(db, "SELECT h.prob FROM node n JOIN hypothesis h ON h.node=n.id WHERE n.parent=? AND n.state IN "
                            "('alive','supported') AND h.prob IS NOT NULL", h["parent"])
            s = sum(x["prob"] for x in sisters)
            # summing to 1 is only required of mutually exclusive rivals; explanations that coexist may exceed 1
            print(f"{label(h)} p={a.p}" + (f"  (the front's live hypotheses add up to {s:.2f}: if they are exclusive rivals, "
                                           "it exceeds 1 and needs adjusting; if they can be true together, ignore it)"
                                           if s > 1.05 and len(sisters) > 1 else ""))
        elif a.cmd == "ach":
            target = get_node(db, a.target)
            if target["type"] == "front" and not a.hypothesis:
                print(ach_matrix(db, target))
            else:
                if not (a.hypothesis and a.value):
                    raise Error("usage: ach <E> <H> CC|C|N|I|II   or   ach <F>")
                e, h = get_node(db, a.target, ("fact", "clue")), get_node(db, a.hypothesis, "hypothesis")
                db.execute("INSERT OR REPLACE INTO ach VALUES (?,?,?,?)", (e["id"], h["id"], a.value, a.note))
                event(db, h["id"], f"ach {a.value}", label(e))
                print(f"{label(e)} × {label(h)} = {a.value}")
        elif a.cmd == "test":
            h = get_node(db, a.hypothesis, "hypothesis")
            if h["state"] not in ("alive", "supported"):
                raise Error(f"{label(h)} is {h['state']}: reopen it before testing")
            if not a.exploratory and not one(db, "SELECT refuted_if FROM hypothesis WHERE node=?", h["id"])["refuted_if"]:
                raise Error(f"{label(h)} does not say what would bring it down. Before testing: `holmes.py edit {label(h)} --refuted-if "
                            "\"<observation that would refute it>\"`. Without it, no result weighs against it. To just "
                            "explore a cheap hunch, use --exploratory (counts as a clue, not as coverage).")
            recipe = hashlib.sha256(" ".join(re.findall(r"\w+", (a.title + " " + a.scope).lower())).encode()).hexdigest()[:16]
            same = one(db, "SELECT t.node FROM test t JOIN node n ON n.id=t.node WHERE t.recipe=? AND n.state != 'cancelled' "
                           "AND coalesce(t.mode, '') = ?", recipe, "exploratory" if a.exploratory else "")
            if same and not a.force:
                raise Error(f"T{same['node']} already exists with the same title+scope (`show T{same['node']}`; "
                            f"to repeat after fixing the instrument use `run T{same['node']}`; --force creates another)")
            similar = search(db, a.title + " " + a.scope, 3, tests_only=True)
            inst = get_node(db, a.instrument, "instrument") if a.instrument else None
            node = create(db, "test", a.title, h["id"], a.summary, "agent", why=a.why)
            db.execute("INSERT INTO test(node, scope, outside, why, prediction, predicted_at, control, control_type, "
                       "instrument, script, recipe, mode) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       (node, a.scope, a.outside, a.why, a.prediction, now() if a.prediction else None, a.control,
                        a.control_type or ("none" if not a.control else None), inst["id"] if inst else None,
                        a.script, recipe, "exploratory" if a.exploratory else None))
            index_node(db, node)
            print(f"T{node}")
            if a.exploratory:
                print("exploratory: the result counts as a clue. It does not confirm a prediction or close a scope; if it "
                      "yields something, record the idea as a hypothesis and do the confirmatory test later.")
            if similar:
                print("similar ones already recorded (check it is not a repeat):\n  " + "\n  ".join(similar))
            if not inst:
                print("warning: without --instrument, a negative counts as INDETERMINATE")
            if not a.control_type or a.control_type in ("none", "planted"):
                print("warning: no real control (known data the instrument must recognize)")
        elif a.cmd == "run":
            t = get_node(db, a.test, "test")
            print(f"X{open_run(db, t, a.pid, a.log, a.host)}")
        elif a.cmd == "result":
            if a.target.startswith("X"):
                x = one(db, "SELECT * FROM run WHERE id=?", int(a.target[1:]))
                if not x:
                    raise Error(f"{a.target} does not exist")
                t = get_node(db, x["test"])
            else:
                t = get_node(db, a.target, "test")
                x = one(db, "SELECT * FROM run WHERE test=? AND result IS NULL ORDER BY id DESC", t["id"])
                if not x:  # quick attempt: opens and closes the run at once
                    x = one(db, "SELECT * FROM run WHERE id=?", open_run(db, t))
            meaning = " ".join((a.meaning or "").split()) or None
            if meaning:  # four states: substantive · "none: <why>" · "revisit: <what>" · absent = pending
                pref, _, rest = meaning.partition(":")
                pref = pref.strip().lower()
                if pref in ("none", "revisit"):
                    meaning = f"{pref}:{rest}"
                    if len(rest.strip()) < 8:
                        raise Error(f"--meaning \"{pref}: ...\" must say {'why there is no readable meaning' if pref == 'none' else 'what to revisit'}")
                elif len(meaning) < 15:
                    raise Error("--meaning too short to say anything. Write what the output says in context, or "
                                "\"none: <why>\", or \"revisit: <what>\", or leave it out (it stays pending for the overall reading)")
            ok = {"yes": 1, "no": 0}.get(a.control_ok)
            db.execute("UPDATE run SET result=?, note=?, n=?, control_ok=?, finished=?, meaning=? WHERE id=?",
                       (a.result, a.note, a.n, ok, now(), meaning, x["id"]))
            still_open = one(db, "SELECT 1 FROM run WHERE test=? AND result IS NULL", t["id"])
            db.execute("UPDATE node SET state=? WHERE id=?", ("running" if still_open else "done", t["id"]))
            touch(db, t["id"], f"X{x['id']} {a.result}", a.note)
            if CURRENT["branch"]:
                add_step(db, CURRENT["branch"], "tested", f"{label(t)} X{x['id']} → {a.result}: {t['title']}",
                         (meaning or a.note or "")[:400] or None, (label(t),))
            v = validity(db, t["id"])
            print(f"{label(t)} X{x['id']} → {a.result}" + (f" ⚠ {v}" if v else ""))
            print("Tell the user in one line what this changes in the plan (FINDING / NEGATIVE within the scope / CONTROL / "
                  "INSTRUMENT / NO CHANGE) and what it means.")
            if a.result == "negative":
                print("A negative closes this form within the tested scope, not the whole concept; valid negatives that "
                      "pile up should lower the confidence (`prob`).")
            if not meaning and a.result != "failed":
                print("meaning pending: it will be read in the overall reading (or record --meaning now, if the output "
                      "says something as text or form).")
            n, v = tunnel(db, get_node(db, t["parent"])["parent"])
            if a.result == "negative" and n >= TUNNEL:
                print(f"⚠ TUNNEL: {tunnel_warning(n, v)}. Stop and switch to READING before the next test.")
            req = reading_request(db)
            if req:
                print("⚠ " + req)
        elif a.cmd in ("search", "tried"):
            r = search(db, a.text, a.n, tests_only=a.cmd == "tried", with_corpus=not a.no_corpus)
            print("\n".join(r) if r else "nothing recorded with these terms. Try synonyms and `corpus.py search --mode "
                                         "literal` before concluding it is new: absence in a search does not prove absence.")
        elif a.cmd == "show":
            r = get_node(db, a.id)
            print(show(db, r) + ("\n" + trail(db, r, short=True) if r["type"] == "branch" else ""))
        elif a.cmd == "branch":
            if a.action == "new":
                if not a.text or not a.src or not (a.why or "").strip():
                    raise Error('usage: branch new "<question of the line>" --from <id it grows from> --why "<why open it>"'
                                " [--step N, if it grows from a step of another branch]")
                origin, dp = get_node(db, a.src), None
                if a.step is not None:
                    if origin["type"] != "branch":
                        raise Error("--step only works with --from B..")
                    ps = steps_of(db, origin["id"])
                    if not 1 <= a.step <= len(ps):
                        raise Error(f"{label(origin)} has {len(ps)} steps")
                    dp = ps[a.step - 1]["id"]
                CURRENT["branch"] = None  # opening a branch is not a step of the branch that was active
                node = create(db, "branch", a.text, origin["id"], a.summary, from_step=dp)
                add_step(db, node, "opened", f"grows from {label(origin)}" + (f" (step {a.step})" if dp else "")
                         + f": {origin['title'][:200]}", a.why.strip())
                if origin["type"] == "branch":
                    add_step(db, origin["id"], "forked", f"→ B{node} {a.text}", a.why.strip(), (f"B{node}",))
                if not a.no_use:
                    set_branch(case, node)
                print(f"B{node}" + ("" if a.no_use else " (active)"))
            elif a.action == "use":
                r = get_node(db, a.text or "", "branch")
                if r["state"] != "active":
                    raise Error(f"{label(r)} is {r['state']}: `state {label(r)} active` before using it")
                set_branch(case, r["id"])
                print(f"active branch: {label(r)}\n" + trail(db, r, short=True))
            elif a.action == "release":
                set_branch(case, None)
                print("no active branch")
            else:
                print(trail(db, ra, short=True) if ra else "no active branch (`tree`, `branch use B..`)")
        elif a.cmd == "step":
            r = get_node(db, a.branch, "branch") if a.branch else ra
            if not r:
                raise Error("no active branch: `branch use B..` or --branch B..")
            if not (a.why or "").strip():
                raise Error("a step without --why does not rebuild the reasoning: say what led to it")
            nodes = tuple(label(get_node(db, x.strip())) for x in (a.nodes or "").split(",") if x.strip())
            add_step(db, r["id"], a.type, a.text, a.why.strip(), nodes)
            print(f"{label(r)} step {len(steps_of(db, r['id']))}")
        elif a.cmd == "tree":
            print(tree(db, case, a.id))
        elif a.cmd == "trail":
            r = get_node(db, a.id, "branch") if a.id else ra
            print(trail(db, r) if r else "no active branch: `trail B..`")
        elif a.cmd == "sheet":
            print(sheet(db, case))
        elif a.cmd == "health":
            print(health(db))
        elif a.cmd == "chain":
            print("\n".join(chain(db, get_node(db, a.id))))
        elif a.cmd == "questions":
            print(questions(db))
        elif a.cmd == "timeline":
            print(timeline(db))
        elif a.cmd == "next":
            for i, (action, why) in enumerate(next_steps(db), 1):
                print(f"{i}. {action}\n   why: {why}")
        elif a.cmd == "connections":
            if not a.target:
                cs = q(db, "SELECT * FROM node WHERE type='connection' AND state='suggested' ORDER BY id")
                return print("\n".join(line(db, c) for c in cs) or "no candidate connection to assess")
            target = get_node(db, a.target) if re.fullmatch(r"[A-Z]?\d+|\w+:\w+", a.target) else None
            out, footer = candidates(db, text_of(db, target) if target else a.target, target["id"] if target else None, a.n)
            print(f"candidates for {label(target) if target else repr(a.target)} (query; nothing was stored):")
            print("\n".join(out + footer) if out else "  none: the absence of a connection is also a result. For what "
                  "shares no word, describe the abstract concept in text (`connections \"duality halves\"`) or "
                  "record it as an entity with aliases.")
            if out:
                print("A candidate is not a relation. For each one: what relation it would be, what rival explanation (chance, "
                      "same source repeated, generic theme) and what observation would separate them. Store only the promising one with `connection`.")
        elif a.cmd == "connection":
            node = new_connection(db, get_node(db, a.src), get_node(db, a.dst), a.relation, a.why, a.rival, a.discriminator,
                                  a.origin, [m.strip() for m in (a.reasons or "").split(",") if m.strip()], a.channel)
            print(f"C{node} (suggested: not a graph edge until `state C{node} confirmed \"<evidence>\"`)")
            if not a.rival:
                print("warning: no --rival. What would the explanation without a relation be (chance, generic theme, same source)?")
        elif a.cmd == "extract":
            import json
            try:
                data = json.loads(Path(a.file).read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise Error(f"unreadable contract: {e}")
            as_set = lambda s: {x.strip() for x in (s or "").split(",") if x.strip()}
            if not isinstance(data, dict):
                raise Error("contract: the JSON must be an object with the keys of MODEL.md")
            try:
                plan, ids = extract(db, data, a.apply, as_set(a.only) or None, as_set(a.reject))
            except (KeyError, TypeError, ValueError, AttributeError) as e:  # an error here undoes the whole batch
                raise Error(f"invalid contract ({type(e).__name__}: {e}); nothing was stored")
            print("\n".join(plan) or "nothing to extract")
            if a.apply:
                print("stored: " + ", ".join(f"{k}→{label(node_by_id(db, v))}" for k, v in ids.items()))
            else:
                print("(plan only; nothing stored. `--apply` stores everything in one transaction; `--only`/`--reject` pick items)")
        elif a.cmd == "jobs":
            rs = q(db, "SELECT x.*, n.title FROM run x JOIN node n ON n.id=x.test WHERE x.result IS NULL")
            for x in rs:
                print(f"X{x['id']} (T{x['test']}) pid {x['pid']} {'alive' if alive(x['pid']) else 'DEAD: record it'} "
                      f"log {x['log']}: {x['title']}")
            print("" if rs else "no open run")
        elif a.cmd == "source":
            target = a.path
            is_local = Path(target).exists()
            ref = str(Path(target).resolve()) if is_local else target
            r = one(db, "SELECT * FROM source WHERE ref=?", ref)
            sha = file_sha(ref) if is_local else None
            if r:
                node = r["node"]
                if sha and sha != r["sha"]:
                    db.execute("UPDATE source SET sha=? WHERE node=?", (sha, node))
                    touch(db, node, "new version", f"{(r['sha'] or '')[:12]} → {sha[:12]}")
            else:
                node = create(db, "source", (a.title or Path(target).name or target)[:160], summary=ref[:800], origin="source",
                              state="catalogued")
                db.execute("INSERT INTO source(node, ref, sha, provenance, reliability) VALUES (?,?,?,?,?)",
                           (node, ref, sha, a.provenance, a.reliability))
            print(f"S{node} {ref}")
            if is_local and not a.no_corpus:
                with C.connect() as cdb:
                    for did, st, p in C.add(cdb, case, ref):
                        print(f"  corpus doc {did} {st}: {p}")
                        db.execute("UPDATE source SET document=? WHERE node=?", (did, node)) if Path(ref).is_file() else None
                db.execute("UPDATE node SET state='indexed' WHERE id=?", (node,))
        elif a.cmd == "quote":
            with C.connect() as cdb:
                p = C.chunk(cdb, a.chunk)
            ref = p["ref"]
            f = one(db, "SELECT * FROM source WHERE ref=?", ref)
            fno = f["node"] if f else None
            if not fno:
                fno = create(db, "source", p["title"][:160], summary=ref[:800], origin="source", state="indexed")
                db.execute("INSERT INTO source(node, ref, provenance, document) VALUES (?,?,?,?)",
                           (fno, ref, "primary", p["document"]))
            location = f"chunk #{p['id']} " + (f"msg {p['msg_id']}" if p["msg_id"] else f"{p['kind']} {p['position']}")
            if a.nature not in FACT_NATURES:
                raise Error(f"quote records what the source says, literally (a fact). {a.nature.capitalize()} about the excerpt is a clue: "
                            f"`new clue \"..\" --nature {a.nature}` linked `about` the quote's fact")
            node = create(db, "fact", a.claim, origin="source", grade=a.grade, nature=a.nature, by="source",
                          source=f"S{fno}", location=location, quote=p["text"][:1000])
            print(f"E{node} (literal quote copied from the corpus, proven now)")
        elif a.cmd == "prove":
            e = get_node(db, a.fact, ("fact", "clue"))
            if e["state"] in FALLEN or e["state"] == "contested":
                raise Error(f"{label(e)} is {e['state']}: proving does not undo that. If the fall was wrong, reopen it "
                            f"first with `state {label(e)} {'open' if e['type'] == 'clue' else 'current'} \"<why>\"`")
            nat = one(db, "SELECT nature FROM fact WHERE node=?", e["id"])["nature"]
            if nat in ("inference", "interpretation"):
                raise Error(f"{label(e)} is an {nat}: it does not become a fact. A fact is a proven finding; what supports an {nat} is "
                            f"another fact (`new fact .. --by ..` and `link E<new> supports {label(e)}`), and if it explains "
                            "something testable, it is a hypothesis")
            had = one(db, "SELECT source, quote, location FROM fact WHERE node=?", e["id"])
            source = get_node(db, a.source, "source")["id"] if a.source else had["source"]
            where = str(source or "") or had["quote"] or a.location or had["location"]
            by, proof = proof_of(db, a.by, a.proof, where)
            if a.source or a.location:
                db.execute("UPDATE fact SET source=coalesce(?, source), location=coalesce(?, location) WHERE node=?",
                           (source if a.source else None, a.location, e["id"]))
                if a.source:
                    db.execute("INSERT OR IGNORE INTO edge VALUES (?,?,?,?,?)", (e["id"], "derives", source, None, now()))
            if nat not in FACT_NATURES:  # a proven report: what counts is what was found, not who told it
                nat = "quote" if by == "source" else "observation"
            db.execute("UPDATE fact SET nature=?, proven_at=?, proven_by=?, proof=? WHERE node=?",
                       (nat, now(), by, proof, e["id"]))
            was = e["type"]
            # proven = checked against the primary source or reproduced: that is grade A on the scale
            db.execute("UPDATE node SET type='fact', state='current', grade='A' WHERE id=?", (e["id"],))
            touch(db, e["id"], f"proven by {by}", f"{a.note}" + (f" · proof: {proof}" if proof else ""))
            if CURRENT["branch"]:
                add_step(db, CURRENT["branch"], "changed", f"{label(e)} proven by {by}: clue → fact" if was == "clue"
                         else f"{label(e)} re-proven by {by}", f"{a.note}" + (f" · proof: {proof}" if proof else ""),
                         (label(get_node(db, e["id"])),))
            print(f"{label(get_node(db, e['id']))} proven by {by}" + (f" (it was clue K{e['id']}; now it is a fact)" if was == "clue" else ""))
        elif a.cmd == "attribute":
            n = get_node(db, a.entity, "entity")
            fact = get_node(db, a.fact, "fact")["id"] if a.fact else None
            old = one(db, "SELECT value FROM attribute WHERE entity=? AND key=?", n["id"], a.key)
            db.execute("INSERT OR REPLACE INTO attribute VALUES (?,?,?,?,?)", (n["id"], a.key, a.value, fact, now()))
            touch(db, n["id"], f"attribute {a.key}", f"{old['value'] if old else '∅'} → {a.value}")
            print(f"{label(n)}.{a.key} = {a.value}" + ("" if fact else "  (no --fact: where does this value come from?)"))
        elif a.cmd == "instrument":
            ref = a.path
            if re.fullmatch(r"I?\d+", ref) and not Path(ref).exists():
                raise Error("to register, pass the file's path; to verify, use `proof`")
            p = str(Path(ref).resolve())
            s = file_sha(p)
            if not s:
                raise Error(f"{p} is not a file")
            r = one(db, "SELECT * FROM instrument WHERE path=?", p)
            if not r:
                node = create(db, "instrument", a.name or Path(p).name, summary=p, origin="measured")
                db.execute("INSERT INTO instrument VALUES (?,?,?)", (node, p, a.verifier))
                db.execute("INSERT INTO version(instrument, sha, at) VALUES (?,?,?)", (node, s, now()))
                print(f"I{node} registered ({s[:12]})")
            else:
                node = r["node"]
                if a.verifier:
                    db.execute("UPDATE instrument SET verifier=? WHERE node=?", (a.verifier, node))
                v = current_version(db, node)
                if v["sha"] == s:
                    print(f"I{node} unchanged ({s[:12]})")
                else:
                    db.execute("INSERT INTO version(instrument, sha, at) VALUES (?,?,?)", (node, s, now()))
                    touch(db, node, "new version", f"{v['sha'][:12]} → {s[:12]}")
                    n = sum(1 for t in q(db, "SELECT node FROM test WHERE instrument=?", node)
                            if validity(db, t["node"]).startswith("TO REVALIDATE"))
                    print(f"I{node} changed ({v['sha'][:12]} → {s[:12]}): {n} negative(s) are now TO REVALIDATE")
        elif a.cmd == "proof":
            leg = "" if a.legacy else " AND n.legacy=0"
            items = [(f"E{r['node']}", r["proof"], "fact") for r in q(db, "SELECT f.* FROM fact f JOIN node n ON n.id=f.node AND n.type='fact' "
                                                                         "AND coalesce(f.proven_by, 'measurement') = 'measurement' "
                                                                         f"WHERE trim(coalesce(f.proof, '')) != ''{leg}")]
            items += [(f"A{r['node']}", r["proof"], "target") for r in q(db, "SELECT x.* FROM target x JOIN node n ON n.id=x.node "
                                                                           f"WHERE trim(coalesce(x.proof, '')) != ''{leg}")]
            items += [(f"I{r['node']}", r["verifier"], "instrument")
                      for r in q(db, f"SELECT i.* FROM instrument i JOIN node n ON n.id=i.node WHERE trim(coalesce(i.verifier, '')) != ''{leg}")]
            if not items:
                print("no proof recorded (--proof on a fact/target, --verifier on an instrument)"
                      + ("" if a.legacy else "; inherited ones only with --legacy"))
            if items and not a.execute:  # these are shell commands from the database: whoever runs them must see them first
                print("\n".join(f"  {rid} ({typ}): {cmd}" for rid, cmd, typ in items))
                return print("(listed, not executed: check each command and run `proof --execute`)")
            for rid, cmd, typ in items:
                ok, out = run_proof(cmd)
                print(f"{'OK    ' if ok else 'FAILED'} {rid} ({typ}): {cmd}" + ("" if ok else f"\n      {out}"))
                node = int(rid[1:])
                if typ == "instrument":
                    db.execute("UPDATE version SET verified=? WHERE id=?", (int(ok), current_version(db, node)["id"]))
                event(db, node, "proof " + ("ok" if ok else "FAILED"), cmd)


if __name__ == "__main__":
    try:
        main()
    except (Error, C.Error) as e:
        sys.exit(f"holmes: {e}")
    except sqlite3.IntegrityError as e:
        sys.exit(f"holmes: value refused by the database ({e})")
