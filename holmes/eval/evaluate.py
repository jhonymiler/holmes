#!/usr/bin/env python3
"""Evaluation of holmes with a synthetic case whose answer is known (default: eval/watchmaker.json).

  python3 -I holmes/eval/evaluate.py recall [answer key]          measures the discovery MECHANISM, without a model
  python3 -I holmes/eval/evaluate.py score <case.db> [answer key]  scores an investigation done by an agent

`recall` records the clues in a temporary case and measures, for each true link and each trap, whether the
pair shows up among the top 5 of: (a) `search` (what existed before), (b) `connections` without concepts,
(c) `connections` after recording the concepts an interpreter would propose. (c) is the mechanism's ceiling, not the
agent's: the concepts come from the answer key. Deciding whether a candidate is a relation is still the agent's job.

`score` does not need the answer key in the case: it matches each clue with the fact of most similar text and counts
confirmed links (true and false), rejected traps, questions, reading revisions and tests spent.
The protocol of a real round with a model is in eval/README.md; it does not run here.
The old command names (recuperacao, pontua) are still accepted.
"""
import json
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOP = 5


OLD_KEYS = {"caso": "case", "objetivo": "objective", "pistas": "clues", "texto": "text", "onda": "wave",
            "ligacoes": "links", "de": "from", "para": "to", "conceito": "concept", "armadilhas": "traps",
            "porque": "why", "conceitos_do_interprete": "interpreter_concepts", "nome": "name",
            "palavras_da_solucao": "solution_words", "solucao": "solution"}


def renamed(x):
    """An answer key written with the old Portuguese keys, with the keys renamed (values untouched)."""
    if isinstance(x, dict):
        return {OLD_KEYS.get(k, k): renamed(v) for k, v in x.items()}
    return [renamed(v) for v in x] if isinstance(x, list) else x


def load(g):
    return renamed(json.loads(Path(g or HERE / "watchmaker.json").read_text(encoding="utf-8")))


def ids_of(lines):
    return [int(m[2]) for l in lines for m in [re.match(r"\s*(?:material )?✗? ?([A-Z])(\d+) \[", l)] if m]


def recall(g):
    root = tempfile.mkdtemp()  # disposable case; holmes reads the environment on import
    os.environ.update(HOLMES_ROOT=root, HOLMES_CASES=f"{root}/cases", HOLMES_CORPUS=f"{root}/corpus/corpus.db")
    for k in ("HOLMES_CASE", "HOLMES_CASO", "HOLMES_RAIZ", "HOLMES_CASOS"):
        os.environ.pop(k, None)
    sys.path.insert(0, str(HERE.parent))
    import holmes as H
    H.main(["init", g["case"], g["objective"]])
    node = {}
    with H.connect(g["case"]) as db:
        for p in g["clues"]:
            node[p["id"]] = H.create(db, "fact", p["text"], nature="observation", origin="source", by="source", quote=p["text"])
        txt = {k: H.text_of(db, H.node_by_id(db, v)) for k, v in node.items()}
        modes = {
            "search (before)": lambda k: [i for i in ids_of(H.search(db, txt[k], TOP + 1, with_corpus=False)) if i != node[k]][:TOP],
            "connections": lambda k: ids_of(H.candidates(db, txt[k], node[k], TOP)[0]),
        }
        res = {m: measure(g, node, f) for m, f in modes.items()}
        for c in g["interpreter_concepts"]:
            H.create(db, "entity", c["name"], cls="concept", alias=c["aliases"])
        res["connections + concepts"] = measure(g, node, modes["connections"])
    return res


def measure(g, node, top):
    found = lambda a, b: node[b] in top(a) or node[a] in top(b)
    links = g["links"]
    return {"links": sum(found(l["from"], l["to"]) for l in links), "of": len(links),
            "non_literal": sum(found(l["from"], l["to"]) for l in links if not l["literal"]),
            "of_non_literal": sum(1 for l in links if not l["literal"]),
            "traps_in_list": sum(found(a["from"], a["to"]) for a in g["traps"]), "of_traps": len(g["traps"])}


def words(t):
    return {w for w in re.findall(r"\w{4,}", t.lower())}


def score(path, g):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='no'").fetchone():
        sys.exit(f"{path} is a case database in the old (Portuguese) schema: open the case once with "
                 "`python3 -I holmes/holmes.py use <case>` to migrate it, then score again")
    facts = db.execute("SELECT n.id, n.title || ' ' || coalesce(f.quote,'') t FROM node n JOIN fact f ON f.node=n.id "
                       "WHERE f.nature IN ('observation','measurement','quote')").fetchall()
    match = {}
    for p in g["clues"]:
        w = words(p["text"])
        best = max(((len(w & words(f["t"])) / len(w | words(f["t"]) or {1}), f["id"]) for f in facts), default=(0, None))
        if best[0] >= 0.5:
            match[p["id"]] = best[1]
    linked = lambda a, b: a in match and b in match and db.execute(
        "SELECT 1 FROM edge WHERE (src=? AND dst=?) OR (src=? AND dst=?) UNION SELECT 1 FROM connection c JOIN node n ON "
        "n.id=c.node WHERE n.state='confirmed' AND ((c.src=? AND c.dst=?) OR (c.src=? AND c.dst=?))",
        (match[a], match[b], match[b], match[a]) * 2).fetchone() is not None
    rejected = lambda a, b: a in match and b in match and db.execute(
        "SELECT 1 FROM connection c JOIN node n ON n.id=c.node WHERE n.state='rejected' AND ((c.src=? AND c.dst=?) OR "
        "(c.src=? AND c.dst=?))", (match[a], match[b], match[b], match[a])).fetchone() is not None
    count = lambda sql: db.execute(sql).fetchone()[0]
    reading = db.execute("SELECT summary FROM node WHERE type='reading' AND state='current' ORDER BY id DESC").fetchone()
    return {
        "clues_recorded": f"{len(match)}/{len(g['clues'])}",
        "true_links_in_graph": f"{sum(linked(l['from'], l['to']) for l in g['links'])}/{len(g['links'])}",
        "traps_accepted_in_graph (false positive)": sum(linked(a["from"], a["to"]) for a in g["traps"]),
        "traps_rejected_explicitly": sum(rejected(a["from"], a["to"]) for a in g["traps"]),
        "suggested_connections_without_decision": count("SELECT count(*) FROM node WHERE type='connection' AND state='suggested'"),
        "interpretations_as_observation (error)": count("SELECT count(*) FROM node n JOIN fact f ON f.node=n.id WHERE "
                                                        "f.nature='observation' AND n.origin='agent'"),
        "questions": count("SELECT count(*) FROM node WHERE type='question'"),
        "hypotheses": count("SELECT count(*) FROM node WHERE type='hypothesis'"),
        "hypotheses_without_refuted_if": count("SELECT count(*) FROM hypothesis WHERE refuted_if IS NULL"),
        "reading_revisions": count("SELECT count(*) FROM node WHERE type='reading'"),
        "final_reading_contains_solution": bool(reading) and any(p.lower() in (reading["summary"] or "").lower()
                                                                 for p in g["solution_words"]),
        "tests_spent": count("SELECT count(*) FROM node WHERE type='test'"),
    }


if __name__ == "__main__":
    a = sys.argv[1:]
    if a:
        a[0] = {"recuperacao": "recall", "pontua": "score"}.get(a[0], a[0])
    if not a or a[0] not in ("recall", "score"):
        sys.exit(__doc__)
    if a[0] == "recall":
        for mode, r in recall(load(a[1] if len(a) > 1 else None)).items():
            print(f"{mode:22} links {r['links']}/{r['of']} (non-literal {r['non_literal']}/{r['of_non_literal']})"
                  f" · traps in list {r['traps_in_list']}/{r['of_traps']}  [top {TOP}]")
    else:
        print(json.dumps(score(a[1], load(a[2] if len(a) > 2 else None)), ensure_ascii=False, indent=2))
