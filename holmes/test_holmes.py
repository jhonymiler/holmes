"""Hermetic tests of holmes 2.0: each test runs in a temporary root (it never touches a real case).

    python3 -m pytest holmes/          or     python3 -I holmes/test_holmes.py
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(root, *args, ok=True, script="holmes.py", stdin=None, old_env=False):
    env = {k: v for k, v in os.environ.items() if not k.startswith("HOLMES_")}
    if old_env:  # the old Portuguese variable names still work
        env.update(HOLMES_RAIZ=str(root), HOLMES_TUNEL="3", HOLMES_LEITURA="4", HOLMES_EMBED_URL="fake")
    else:
        env.update(HOLMES_ROOT=str(root), HOLMES_TUNNEL="3", HOLMES_READING="4", HOLMES_EMBED_URL="fake")
    r = subprocess.run([sys.executable, "-I", str(HERE / script), *args], capture_output=True, text=True,
                       env=env, input=stdin)
    assert (r.returncode == 0) == ok, (args, r.stdout, r.stderr)
    return r.stdout + r.stderr


def case():
    root = Path(tempfile.mkdtemp())
    run(root, "init", "demo", "Find out who wrote the letter")
    return root


def node_id(out, prefix, typ):
    return re.search(rf"\b{prefix}(\d+) \[{typ}", out)[1]


def test_tree_limits_and_targets():
    r = case()
    assert "OBJECTIVE O1" in run(r, "map")
    assert run(r, "new", "target", "Date the paper", "--parent", "O1").strip() == "A2"
    assert run(r, "new", "target", "Find the author", "--parent", "O1").strip() == "A3"
    run(r, "link", "A3", "depends", "A2")
    run(r, "new", "hypothesis", "No front", ok=False)
    run(r, "new", "front", "x" * 200, "--parent", "A2", ok=False)
    run(r, "show", "H2", ok=False)                                       # a wrong prefix is caught
    assert "its own command: `test" in run(r, "new", "test", "No test row", "--parent", "A2", ok=False)
    for i in range(5):
        run(r, "new", "front", f"Front {i}", "--parent", "A2")
    assert "active fronts" in run(r, "new", "front", "Sixth", "--parent", "A2", ok=False)
    run(r, "state", "F4", "parked", ok=False)                            # requires a reason
    run(r, "state", "F4", "parked", "no material for now")
    run(r, "new", "front", "Fits now", "--parent", "A2")
    run(r, "state", "A2", "solved", "T9", ok=False)                      # requires --solution
    run(r, "state", "A2", "solved", "watermark", "--solution", "1897 paper", "--proof", "true")
    assert "UNBLOCKED" in run(r, "map")
    assert "not executed" in run(r, "proof") and "OK     A2" in run(r, "proof", "--execute")


def test_runs_validity_tunnel():
    r = case()
    run(r, "new", "front", "Paper", "--parent", "O1")
    run(r, "new", "hypothesis", "Paper from 1890", "--parent", "F2", "--prob", "0.6", "--refuted-if", "modern fiber")
    judge = r / "judge.py"
    judge.write_text("print(1)\n")
    assert run(r, "instrument", str(judge), "date judge", "--verifier", "true").startswith("I4")
    run(r, "test", "H3", "Mark", "--scope", "mills 1880-1900", ok=False)                    # no --why
    t = run(r, "test", "H3", "Watermark", "--scope", "english mills 1880-1900", "--why",
            "a positive dates the paper; a negative only closes english mills", "--instrument", "I4",
            "--prediction", "matches Whatman", "--control", "known 1895 sheet", "--control-type", "real")
    assert t.startswith("T5") and "no real control" not in t
    assert run(r, "run", "T5", "--pid", "999999", "--log", "outputs/x.log").strip() == "X1"
    m = run(r, "map")
    assert "pid 999999 DEAD" in m and "dead PID" in m
    run(r, "result", "T5", "negative", "no mark matches", "--control-ok", "yes", "--n", "412",
        "--meaning", "no english mill: the paper may come from another country")
    assert "T5 already exists" in run(r, "test", "H3", "Watermark", "--scope", "english mills 1880-1900",
                                      "--why", "x", ok=False)
    v = run(r, "show", "T5")
    assert "prediction BEFORE" in v and "n=412" in v
    judge.write_text("print(2)\n")                                      # fixes the instrument
    assert "1 negative(s) are now TO REVALIDATE" in run(r, "instrument", str(judge))
    assert "TO REVALIDATE" in run(r, "tried", "watermark english mills")
    assert run(r, "run", "T5").strip() == "X2"                          # re-run with the new version
    out = run(r, "result", "T5", "negative", "nothing again", "--control-ok", "yes", "--meaning", "none: the same absence as before")
    assert "TO REVALIDATE" not in out
    for i in range(2):
        run(r, "test", "H3", f"Fiber {i}", "--scope", f"sample {i}", "--why", "p")
        out = run(r, "result", f"T{6 + i}", "negative", "nothing")
    assert "TUNNEL" in out and "INDETERMINATE" in out
    m = run(r, "map")
    assert "TUNNEL in F2" in m and "2 negative(s) without an instrument" in m
    run(r, "test", "H3", "Broken control", "--scope", "a", "--why", "p")
    assert "INVALID" in run(r, "result", "T8", "positive", "found?", "--control-ok", "no")
    run(r, "test", "H3", "Dry seal", "--scope", "b", "--why", "p", "--instrument", "I4",
        "--control", "1895 sheet", "--control-type", "real")
    assert "control not confirmed" in run(r, "result", "T9", "negative", "nothing")


def test_facts_sources_corpus_and_entities():
    r = case()
    doc = r / "cases/demo/sources/letter.md"
    doc.write_text("Dear sir,\n\nThe iron-gall ink from the Café Müller darkens with time.\n\nSigned, M.")
    chat = r / "chat.json"
    chat.write_text(json.dumps({"messages": [
        {"id": i, "type": "message", "date": f"2020-01-0{i + 1}T10:00", "from": "ana", "text": t}
        for i, t in enumerate(["hi", "the lock has three pins", "bye"])]}))
    assert "indexed" in run(r, "source", str(doc), "--reliability", "B")
    assert "unchanged" in run(r, "source", str(doc))
    run(r, "source", str(chat), "--provenance", "third-party")
    b = run(r, "search", "muller ink")                                  # no umlaut still matches
    assert "corpus #" in b
    pid = b.split("corpus #")[1].split(" ")[0]
    e = run(r, "quote", pid, "The letter uses iron-gall ink").strip()
    assert e.startswith("E") and "proven" in e
    eid = e.split()[0]
    v = run(r, "show", eid)
    assert "quote: Dear sir" in v and "derives" in v
    assert "is not a fact" in run(r, "new", "fact", "So-and-so said the letter is fake", "--nature", "report", ok=False)
    run(r, "new", "clue", "So-and-so said the letter is fake", "--origin", "external", "--nature", "report")
    assert "clue:open report/external/C" in run(r, "search", "fake", "--no-corpus")
    assert "1 open clue(s)" in run(r, "map")
    assert "proven:source" in run(r, "search", "iron-gall ink", "--no-corpus")
    run(r, "new", "fact", "Letter without a date", ok=False)                                  # a fact without proof does not exist
    run(r, "new", "fact", "The letter was written by a left-hander", "--nature", "inference", "--by", "source",
        ok=False)                                                                              # an inference is not a fact
    kinf = run(r, "new", "clue", "The letter was written by a left-hander", "--nature", "inference").strip()
    assert kinf.startswith("K")
    assert "does not become a fact" in run(r, "prove", kinf, "looks like it", "--by", "source", ok=False)
    kmed = run(r, "new", "clue", "The ink reacts to iron in the colour test", "--nature", "measurement").strip()
    run(r, "prove", kmed, "redone", "--by", "measurement", ok=False)                        # a measurement requires --proof
    assert "it was clue" in run(r, "prove", kmed, "redone", "--by", "measurement", "--proof", "true")
    assert "proven:measurement" in run(r, "show", kmed) or "measurement" in run(r, "show", kmed)
    assert "fact:current measurement" in run(r, "search", "reacts iron", "--no-corpus")    # the clue became a fact
    assert run(r, "show", "E" + kmed[1:]).startswith("E")                                   # same node, new prefix
    run(r, "new", "fact", "No basis", "--by", "source", ok=False)                           # a source that points to nothing
    assert "clue" in run(r, "quote", pid, "The author meant X", "--nature", "interpretation", ok=False)
    kdrop = run(r, "new", "clue", "Maybe the ink is later", "--nature", "observation").strip()
    run(r, "state", kdrop, "dropped", "there is no way to date the ink")
    assert "proving does not undo" in run(r, "prove", kdrop, "reread", "--by", "source", ok=False)  # it does not resurrect
    j = r / "ext.json"
    j.write_text('{"observations": [{"id": "o1", "text": "External agent says the key fits", '
                 '"origin": "external", "by": "measurement", "proof": "true"}]}')
    assert "clue/observation" in run(r, "extract", str(j))                                  # external does not prove itself
    ksrc = run(r, "new", "clue", "The paper has a watermark", "--nature", "observation").strip()
    run(r, "prove", ksrc, "ok", "--by", "source", ok=False)                                  # a note is not a locator
    assert "proven by source" in run(r, "prove", ksrc, "seen against the light", "--by", "source", "--location", "sheet 1")
    kte = run(r, "new", "clue", "The ink is from 1897", "--nature", "observation").strip()
    assert "requires --proof" in run(r, "prove", kte, "x", "--by", "test", ok=False)
    # entity with an alias: searching "padlock" finds what was written as "lock"
    run(r, "new", "entity", "lock", "--class", "concept", "--alias", "padlock,tumbler")
    run(r, "new", "thread", "Measure the pins of the cellar lock")
    assert "Measure the pins" in run(r, "search", "padlock", "--no-corpus")
    n = node_id(run(r, "search", "lock", "--no-corpus"), "N", "entity")
    run(r, "attribute", f"N{n}", "pins", "3", "--fact", eid)
    assert "pins = 3" in run(r, "show", f"N{n}")
    assert "lock" in run(r, "search", "lock")                            # the chat corpus shows up too


def test_dependencies_contradictions_ach_health():
    r = case()
    run(r, "new", "front", "Authorship", "--parent", "O1")
    run(r, "new", "premise", "The letter is by a single person", "--parent", "F2")      # R3
    run(r, "new", "hypothesis", "It was M.", "--parent", "F2", "--prob", "0.5")         # H4
    run(r, "new", "hypothesis", "It was the secretary", "--parent", "F2", "--prob", "0.3")  # H5
    run(r, "link", "H4", "depends", "R3")
    assert "unverified premises: R3" in run(r, "map")
    assert "depend on it" in run(r, "state", "R3", "refuted", "two handwritings (E9)")
    assert "H4 depends on R3, which fell" in run(r, "map")
    run(r, "new", "fact", "Signature in iron-gall ink", "--state", "current", "--by", "source", "--location", "sheet 1")   # E6
    run(r, "new", "fact", "Signature in aniline ink", "--state", "current", "--by", "source", "--location", "sheet 1")     # E7
    run(r, "link", "E6", "contradicts", "E7")
    assert "open contradiction: E6 × E7" in run(r, "map")
    run(r, "state", "E7", "retracted", "misread")
    assert "open contradiction" not in run(r, "map")
    assert "add up to" not in run(r, "prob", "H5", "0.3", "no change")   # below 1 is "the other one"
    assert "if they can be true together" in run(r, "prob", "H5", "0.7", "coexist?")
    run(r, "prob", "H5", "0.3", "back")
    run(r, "ach", "E6", "H4", "C")
    run(r, "ach", "E6", "H5", "II")
    m = run(r, "ach", "F2")
    assert "yes" in m and "inconsist" in m
    s = run(r, "health")
    assert "without a refutation criterion" in s


def test_reading_meaning_and_legacy():
    r = case()
    assert "CURRENT READING: none" in run(r, "map")
    run(r, "new", "front", "Ink", "--parent", "O1")                                   # F2
    run(r, "new", "hypothesis", "The ink dates the letter", "--parent", "F2")         # H3, no criterion
    assert "does not say what would bring it down" in run(r, "test", "H3", "Iron", "--scope", "a", "--why", "p", ok=False)
    run(r, "edit", "H3", "--refuted-if", "modern aniline ink")
    run(r, "test", "H3", "Iron", "--scope", "a", "--why", "p")                        # T4
    assert "too short" in run(r, "result", "T4", "negative", "0 ions", "--meaning", "s", ok=False)
    out = run(r, "result", "T4", "negative", "0 ions", "--meaning", "no iron: maybe it is not even old ink")
    assert "not the whole concept" in out
    assert "meaning: no iron" in run(r, "show", "T4")
    assert "T4" in run(r, "search", "maybe old", "--no-corpus")                      # the meaning is searchable
    assert run(r, "reading", "The letter pretends to be old; the paper and the ink tell different stories.").startswith("L")
    m = run(r, "map")
    assert "CURRENT READING L" in m and "tell different stories" in m
    for i in range(4):
        run(r, "test", "H3", f"Form {i}", "--scope", f"a{i}", "--why", "p")
        out = run(r, "result", f"T{6 + i}", "inconclusive", "?")
    assert "OVERALL READING pending: 4" in out and "OVERALL READING" in run(r, "map")
    assert "requires --reason" in run(r, "reading", "New reading: a late forgery.", ok=False)
    assert "supersedes L5" in run(r, "reading", "New reading: a late forgery.", "--reason", "4 inconclusive forms")
    assert "OVERALL READING" not in run(r, "map")
    assert "criterion was met: modern aniline ink" in run(r, "state", "H3", "refuted", "T4")
    # inherited from another system: the contradiction leaves the alerts until someone touches one side
    run(r, "new", "fact", "Iron-gall ink", "--state", "current", "--by", "source", "--location", "sheet 1")    # E11
    run(r, "new", "fact", "Aniline ink", "--state", "current", "--by", "source", "--location", "sheet 1")      # E12
    run(r, "link", "E11", "contradicts", "E12")
    with sqlite3.connect(r / "cases/demo/case.db") as db:
        db.execute("UPDATE node SET legacy=1")
    m = run(r, "map")
    assert "open contradiction" not in m and "inherited, outside the alerts: 1 contradictions" in m
    run(r, "edit", "E11", "--summary", "checked again")
    assert "open contradiction: E11 × E12" in run(r, "map")


def test_corpus_modes():
    r = Path(tempfile.mkdtemp())
    (r / "a.md").write_text("Line one\nD\nO\nO\nR\n\nThe key opens the cellar door.")
    run(r, "add", "docs", str(r / "a.md"), script="corpus.py")
    assert "door" in run(r, "search", "key cellar", script="corpus.py")
    assert "#1" in run(r, "search", "D\nO\nO\nR", "--mode", "literal", script="corpus.py")   # raw vertical pattern
    assert "1 chunks embedded" in run(r, "embed", script="corpus.py")
    assert "door" in run(r, "search", "cellar", "--mode", "hybrid", script="corpus.py")


def test_hooks():
    r = case()
    run(r, "new", "front", "Ink", "--parent", "O1")
    run(r, "new", "hypothesis", "Iron-gall ink points to before 1900", "--parent", "F2")
    st = json.loads(run(r, "start", script="hooks.py", stdin=json.dumps({"source": "startup"})))
    assert "Active case: demo" in st["hookSpecificOutput"]["additionalContext"]
    ev = {"session_id": "s1", "prompt": "and the iron-gall ink, have we seen this before?"}
    assert "H3" in run(r, "prompt", script="hooks.py", stdin=json.dumps(ev))
    assert run(r, "prompt", script="hooks.py", stdin=json.dumps(ev)).strip() == ""   # not repeated in the session
    (r / ".holmes/sessoes").mkdir()                                           # seen-list written before the rename
    (r / ".holmes/sessions/s1.seen").rename(r / ".holmes/sessoes/s0.vistos")
    assert run(r, "prompt", script="hooks.py", stdin=json.dumps({**ev, "session_id": "s0"})).strip() == ""
    run(r, "bogus", script="hooks.py", stdin="{}")                            # unknown/empty action: no entry
    run(r, script="hooks.py", stdin="{}")
    assert set(json.loads((r / ".holmes/hooks.json").read_text())) <= {"start", "prompt"}
    g = json.loads(run(r, "guard", script="hooks.py", stdin=json.dumps({"tool_input": {"command": "pkill -f sweep"}})))
    assert g["hookSpecificOutput"]["permissionDecision"] == "deny"
    cmd = "python3 cases/demo/scripts/sweep.py"
    assert "ran without an open test" in run(r, "post", script="hooks.py", stdin=json.dumps({"tool_input": {"command": cmd}}))
    tr = r / "t.jsonl"
    tr.write_text("\n".join(json.dumps(x) for x in [
        {"type": "user", "message": {"content": "run the script"}, "timestamp": "2026-01-01T00:00"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "running"},
                                                      {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}]))
    stop = json.loads(run(r, "stop", script="hooks.py", stdin=json.dumps({"session_id": "s1", "transcript_path": str(tr)})))
    assert stop["decision"] == "block"
    assert "run the script" in (r / ".holmes/journal/s1.md").read_text()
    tr.write_text("\n".join(json.dumps(x) for x in [                          # U+2028 must not split the event
        {"type": "user", "message": {"content": "line same message"}, "timestamp": "2026-01-01T00:00"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "ok end"}]}}]))
    run(r, "stop", script="hooks.py", stdin=json.dumps({"session_id": "s2", "transcript_path": str(tr)}))
    assert "same message" in (r / ".holmes/journal/s2.md").read_text()
    seen = run(r, "health").split("hooks seen running:")[1]                  # execution seen, not configuration
    assert "start" in seen and "stop" in seen and "never seen" not in seen


def test_integrity_exploratory_script_control():
    r = case()
    run(r, "new", "front", "Paper", "--parent", "O1")
    run(r, "new", "hypothesis", "Hunch: Dutch watermark", "--parent", "F2")                         # H3, no criterion
    run(r, "test", "H3", "Look against the light", "--scope", "1 sheet", "--why", "p", ok=False)
    assert "exploratory" in run(r, "test", "H3", "Look against the light", "--scope", "1 sheet", "--why", "p",
                                "--exploratory")                                                   # T4
    assert "exploratory (counts as a clue" in run(r, "result", "T4", "positive", "saw a lion",
                                                  "--meaning", "the lion is Amsterdam's coat of arms")
    run(r, "edit", "H3", "--refuted-if", "a mark from another city")
    judge = r / "judge.py"
    judge.write_text("print(1)\n")
    run(r, "instrument", str(judge), "judge")                                                        # I5
    run(r, "test", "H3", "Catalogue", "--scope", "c", "--why", "p", "--instrument", "I5", "--script",
        str(r / "gone.py"), "--control", "known sheet", "--control-type", "real")                   # T6
    assert "belongs to a test" in run(r, "edit", "H3", "--script", str(judge), ok=False)
    run(r, "edit", "T6", "--script", str(judge))
    assert str(judge) in run(r, "show", "T6")
    run(r, "edit", "T6", "--script", str(r / "gone.py"))
    assert "not found" in run(r, "run", "T6")
    assert "unversioned script" in run(r, "result", "T6", "negative", "nothing", "--control-ok", "yes")
    run(r, "test", "H3", "Magnifier", "--scope", "d", "--why", "p", "--instrument", "I5",
        "--control", "known sheet", "--control-type", "real")                                       # T7
    assert "control not confirmed" in run(r, "result", "T7", "positive", "found it")                # positive too
    k = run(r, "new", "clue", "The magnifier shows the mark", "--nature", "observation").strip()
    assert "proves nothing" in run(r, "prove", k, "x", "--by", "test", "--proof", "T7", ok=False)   # control not seen
    run(r, "result", "T7", "negative", "x", "--meaning", "none: x", ok=False)                       # reason too short
    run(r, "new", "fact", "Empty proof", "--proof", "", "--by", "source", "--location", "sheet 1")
    assert "OK" not in run(r, "proof", "--execute")                                                # empty proves nothing


def test_extraction_connection_and_reading():
    """Full path: material → observation → clue → candidate connection → question → hypothesis → plan,
    with a relation that shares no word (yin-yang ↔ two halves)."""
    r = case()
    run(r, "new", "front", "Poem and drawing", "--parent", "O1")                                     # F2
    old = run(r, "new", "fact", "The poem speaks of two halves that seek each other", "--state", "current", "--by",
              "source", "--location", "sheet 1").strip()
    q = run(r, "new", "question", "What does the poem want joined?", "--parent", "F2").strip()
    assert q.startswith("Q")
    assert "GAP: no hypothesis" in run(r, "questions")
    assert f"formulate explanations for {q}" in run(r, "next")
    contract = {
        "observations": [{"id": "o1", "text": "The footer bears a hand-drawn yin-yang symbol",
                          "method": "visual inspection of sheet 2", "limits": "front of the sheet only"}],
        "clues": [{"obs": "o1", "about": q, "why": "isolated symbol, out of the style of the rest"}],
        "interpretations": [{"id": "i1", "about": "o1", "text": "The symbol may mark where two parts complete each other",
                             "alternatives": "decoration; the draughtsman's signature"}],
        "hypotheses": [{"id": "h1", "text": "The two halves are the two parts of the map, which complete each other",
                        "parent": "F2", "answers": q, "motivated_by": ["o1", old], "prob": 0.3,
                        "refuted_if": "the map parts do not fit along any edge", "rivals": ["h2"]},
                       {"id": "h2", "text": "The symbol is just a decoration common at the time", "parent": "F2", "answers": q,
                        "prob": 0.4, "refuted_if": "the symbol appears at a structural point of the map"}],
        "connections": [{"from": "o1", "to": "h1", "relation": "supports",
                         "why": "yin-yang is the classic image of two complementary halves",
                         "rival": "popular symbol, it shows up anywhere", "discriminator": "is the symbol at the junction of the parts?"}],
        "discriminators": [{"between": ["h1", "h2"], "observation": "position of the symbol relative to the map's edges"}],
        "impact": {"reading": "if h1 holds, the case is about joining parts, not deciphering words"}}
    f = r / "extraction.json"
    f.write_text(json.dumps(contract, ensure_ascii=False))
    count = lambda: sqlite3.connect(r / "cases/demo/case.db").execute("SELECT count(*) FROM node").fetchone()[0]
    before = count()
    plan = run(r, "extract", str(f))
    assert "nothing stored" in plan and "clue/interpretation (not a fact)" in plan and count() == before
    bad = dict(contract, connections=contract["connections"] + [{"from": "o1", "to": "E999", "relation": "about", "why": "x"}])
    (r / "bad.json").write_text(json.dumps(bad))
    run(r, "extract", str(r / "bad.json"), "--apply", ok=False)
    for i, bad in enumerate(([], {"interpretations": [{"id": "i1"}]}, {"observations": [{"id": "H1", "text": "x"}]},
                             {"observations": [{"id": "o1", "text": "x", "chunk": "abc"}]})):
        (r / f"r{i}.json").write_text(json.dumps(bad))
        assert "Traceback" not in run(r, "extract", str(r / f"r{i}.json"), "--apply", ok=False)
    assert count() == before                                                   # transaction: nothing left half-done
    (r / "conf.json").write_text(json.dumps({"connections": [{"from": old, "to": q, "relation": "about", "why": "x",
                                                              "state": "confirmed"}]}))
    assert "only as 'suggested'" in run(r, "extract", str(r / "conf.json"), "--apply", ok=False)
    done = run(r, "extract", str(f), "--apply")
    ids = dict(x.split("→") for x in done.split("stored: ")[1].strip().split(", "))
    o1, h1, h2, c1 = ids["o1"], ids["h1"], ids["h2"], ids["c1"]
    assert "same text already recorded" in run(r, "extract", str(f))          # reapplying does not duplicate
    v = run(r, "show", h1)
    assert f"~ candidate connection {c1} [suggested]" in v and "← supports" not in v   # a candidate is not an edge
    assert "rival" in v and "answers" in v
    # discovery: with no shared word the link does not show up; with the concept recorded as an entity, it does
    assert old not in run(r, "connections", "hand-drawn yin-yang symbol")     # control: neither graph nor concept
    run(r, "new", "entity", "complementarity", "--class", "concept", "--alias", "two halves,yin-yang")
    found = run(r, "connections", "hand-drawn yin-yang symbol")
    assert old in found and "bridge" in found and "'yin-yang' ↔ 'two halves'" in found and "nothing was stored" in found
    assert old in run(r, "connections", "complementary halves")               # free text with the concept
    assert "shared terms" not in run(r, "connections", "what is this after all")  # stopwords link nothing
    # deliberate promotion: only the confirmation creates the edge
    run(r, "state", c1, "confirmed", ok=False)                                # requires a reason
    assert f"{o1} supports {h1}" in run(r, "state", c1, "confirmed", "the symbol is at the junction (inspection 2)")
    assert "← supports" in run(r, "show", h1)
    # working theory tied to the evidence: if its basis falls, the reading shows up as a dependent
    run(r, "reading", "The case is about joining two parts, not deciphering words.", "--supports", f"{o1},{old}",
        "--rival", h2, "--question", q)
    m = run(r, "map")
    assert ("basis: " + ", ".join(sorted([o1, old], key=lambda x: int(x[1:])))) in m and f"rivals: {h2}" in m \
        and f"decisive question: {q}" in m and "NEXT" in m
    fall = run(r, "state", o1, "dropped", "the symbol was an ink stain (magnifier)")
    assert "L" in fall.split("reassessed:")[1] and h1 in fall                 # transitive: reading and hypothesis
    m = run(r, "map")
    assert "which fell" in m and "OVERALL READING requested by event" in m
    assert "lost its basis" in run(r, "next")
    assert "⚠ FELL" in run(r, "chain", h1)
    run(r, "new", "entity", "Poem published", "--class", "event")
    n = node_id(run(r, "search", "poem published", "--no-corpus"), "N", "entity")
    run(r, "attribute", f"N{n}", "when", "1897-03-01", "--fact", old)
    assert "1897-03-01" in run(r, "timeline")


def test_eval_synthetic():
    """The discovery mechanism on the case with a known answer, and the scorer of an investigation."""
    out = run(Path(tempfile.mkdtemp()), "recall", script="eval/evaluate.py")
    assert "connections + concepts links 9/9 (non-literal 7/7)" in out, out
    r = case()
    g = json.loads((HERE / "eval/watchmaker.json").read_text(encoding="utf-8"))
    txt = {p["id"]: p["text"] for p in g["clues"]}
    e = {k: run(r, "new", "fact", txt[k], "--state", "current", "--origin", "source", "--by", "source", "--location", "sheet 1").strip()
         for k in ("c05", "c14", "c08")}
    c = run(r, "connection", e["c14"], e["c05"], "supports", "yin-yang and two halves: complementarity").split()[0]
    run(r, "state", c, "confirmed", "the symbol is in the poem's own footer")
    t = run(r, "connection", e["c08"], e["c05"], "about", "same expression 'two halves'", "--rival", "coincidence").split()[0]
    run(r, "state", t, "rejected", "a flowerbed has nothing to do with the poem")
    p = json.loads(run(r, "score", str(r / "cases/demo/case.db"), script="eval/evaluate.py"))
    assert p["true_links_in_graph"] == "1/9" and p["traps_accepted_in_graph (false positive)"] == 0
    assert p["traps_rejected_explicitly"] == 1 and p["clues_recorded"] == "3/30"


def test_branches_steps_trail_sheet():
    r = case()
    run(r, "new", "target", "Date the paper", "--parent", "O1")                     # A2
    run(r, "state", "A2", "solved", "watermark", "--solution", "1897 paper")
    run(r, "new", "target", "Find the author", "--parent", "O1")                    # A3
    run(r, "new", "question", "Who signs 'J.'?", "--parent", "A3")                  # Q4
    run(r, "new", "branch", "x", "--parent", "Q4", ok=False)                        # a branch only via `branch new`
    run(r, "branch", "new", "J. = John", "--from", "Q4", ok=False)                  # no --why
    assert run(r, "branch", "new", "J. = John", "--from", "Q4", "--why", "the stamp says John & Co").startswith("B5")
    assert run(r, "new", "fact", "John & Co stamp on the back", "--why", "read the back", "--by", "source", "--location", "sheet 1").strip() == "E6"
    run(r, "step", "thought", "John was a partner, not the author", ok=False)       # a step without a reason
    run(r, "step", "thought", "John was a partner, not the author", "--why", "E6 is a commercial stamp")
    # back to step 1 and another direction: the branch inherits only what came before
    assert run(r, "branch", "new", "J. = Jane", "--from", "B5", "--step", "1", "--why",
               "the handwriting matches Jane's letters").startswith("B7")
    run(r, "state", "B5", "dead", ok=False)                                         # dying requires a reason
    run(r, "state", "B5", "dead", "E6: John was just the firm")
    t = run(r, "trail", "B7")
    assert "Q4" in t and "1. opened" in t and "why: the stamp says John" in t
    assert "John was a partner" not in t                                            # step 3 of B5 is after the cut
    assert "the handwriting matches" in t
    t5 = run(r, "trail", "B5")
    assert "recorded: E6" in t5 and "forked: → B7" in t5 and "changed: B5 active → dead" in t5
    a = run(r, "tree")
    assert "▶ B7 [active]" in a and "B5 [dead]" in a and "(from step 1)" in a and "A2 [solved] Date the paper ✓" in a
    run(r, "step", "next", "compare the handwriting with 3 of Jane's letters", "--why", "tells Jane from a copyist")
    sh = run(r, "sheet")
    assert "IMMEDIATE B7" in sh and "NEXT EXPERIMENT: compare the handwriting" in sh
    assert "ALREADY EXPLORED" in sh and "B5 [dead]" in sh and "John was just the firm" in sh and "1897 paper" in sh
    assert "ACTIVE BRANCH B7" in run(r, "map")
    run(r, "state", "B7", "paused", "waiting for the letters")
    assert "ACTIVE BRANCH: none" in run(r, "map")
    assert "opened: grows from B5 (step 1)" in run(r, "show", "B7")
    assert "B7" in run(r, "search", "copyist")                                     # the step is searchable
    run(r, "state", "B7", "active")                                                # a long reason does not lock the branch
    run(r, "branch", "use", "B7")
    run(r, "new", "front", "Handwriting", "--parent", "A3")
    front = node_id(run(r, "search", "Handwriting", "--no-corpus"), "F", "front")
    h = run(r, "new", "hypothesis", "Jane wrote it", "--parent", f"F{front}", "--refuted-if", "different handwriting").strip()
    t = run(r, "test", h, "Same handwriting?", "--scope", "3 letters", "--why", "x" * 550).split()[0]
    assert t.startswith("T")
    run(r, "result", t, "negative", "no match", "--meaning", "nenhum: only a handful of letters seen")
    k = run(r, "new", "clue", "The ink is brown", "--nature", "observation").strip()
    run(r, "prove", k, "redone", "--by", "measurement", "--proof", "true")
    e = "E" + k[1:]
    run(r, "prove", e, "seen again", "--by", "source", "--location", "sheet 2")
    f = run(r, "new", "fact", "Paper is laid", "--by", "source", "--location", "sheet 1").strip()
    g = run(r, "new", "fact", "Paper is thin", "--by", "source", "--location", "sheet 1", "--grade", "B").strip()
    tr = run(r, "trail", "B7")
    assert "why: none: only a handful" in tr                                       # the translated meaning
    assert f"changed: {k} proven by measurement: clue → fact" in tr and f"changed: {e} re-proven by source" in tr
    assert "/agent/A proven" in run(r, "show", e) and "/agent/A proven" in run(r, "show", f)  # proven → grade A
    assert "/agent/B proven" in run(r, "show", g)                                 # an explicit --grade is kept


def test_reorganize_old_database():
    r = case()
    run(r, "new", "fact", "1897 paper", "--by", "source", "--location", "sheet 1")              # E2, outside a branch
    run(r, "branch", "new", "Paper line", "--from", "O1", "--why", "start")                      # B3
    run(r, "step", "thought", "The paper dates the letter", "--why", "watermark", "--nodes", "E2")
    db = sqlite3.connect(r / "cases" / "demo" / "case.db")                                       # database from before the model
    i = db.execute("INSERT INTO node(type, title, state, origin, created, updated) VALUES "
                   "('fact', 'Maybe the letter is by a left-hander', 'current', 'agent', 'x', 'x')").lastrowid
    db.execute("INSERT INTO fact(node, nature) VALUES (?, 'inference')", (i,)); db.commit(); db.close()
    assert "without a recorded proof" in run(r, "map", "--all")                                  # old database: warns
    plan = run(r, "reorganize")
    assert "become clues 1 (inference 1)" in plan and "get a branch 1" in plan and "plan only" in plan
    assert run(r, "show", f"E{i}").startswith(f"E{i} [fact:current")                            # nothing stored without --apply
    run(r, "reorganize", "--apply")
    assert f"K{i} [clue:open inference" in run(r, "search", "left-hander", "--no-corpus")
    assert "in branch: B3" in run(r, "show", "E2")
    assert "become clues 0" in run(r, "reorganize")                                              # idempotent


def test_rereading_revalidation_and_resume():
    """plan.md §7 (rereading on contradiction and on a central hypothesis), §16 (instrument) and §14 (compaction)."""
    r = case()
    run(r, "new", "front", "F", "--parent", "O1")
    run(r, "new", "fact", "A", "--by", "source", "--location", "sheet 1"); run(r, "new", "fact", "B", "--by", "source", "--location", "sheet 1")   # E3 E4
    run(r, "new", "hypothesis", "Central", "--parent", "F2", "--prob", "0.5", "--refuted-if", "r")         # H5
    run(r, "reading", "picture", "--supports", "E3", "--rival", "H5")
    assert "revise the overall reading" not in run(r, "next")
    run(r, "link", "E3", "contradicts", "E4")
    assert "contradiction recorded" in run(r, "next")
    run(r, "prob", "H5", "0.1", "dropped")
    assert "central hypothesis changed weight (H5 0.5→0.1)" in run(r, "map")
    judge = r / "j.py"
    judge.write_text("print(1)\n")
    run(r, "instrument", str(judge), "j")                                                                   # I7
    run(r, "test", "H5", "t", "--scope", "a", "--why", "p", "--instrument", "I7", "--control", "c",
        "--control-type", "real")                                                                         # T8
    run(r, "result", "T8", "negative", "n", "--control-ok", "yes")
    judge.write_text("print(2)\n")
    run(r, "instrument", str(judge))
    assert "run T8 again with the current instrument" in run(r, "next")
    tr = r / "t.jsonl"
    tr.write_text(json.dumps({"type": "user", "message": {"content": "we decided to park front F"},
                              "timestamp": "2026-01-01T00:00"}))
    run(r, "pre-compact", script="hooks.py", stdin=json.dumps({"session_id": "s", "transcript_path": str(tr)}))
    st = json.loads(run(r, "start", script="hooks.py", stdin=json.dumps({"session_id": "s", "source": "compact"})))
    ctx = st["hookSpecificOutput"]["additionalContext"]
    assert "park front F" in ctx and "MAP" in ctx and "CURRENT READING" in ctx    # plan + theory + journal


OLD_SCHEMA = """CREATE TABLE IF NOT EXISTS no(id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL,
  pai INTEGER REFERENCES no(id), titulo TEXT NOT NULL CHECK(length(titulo) <= 160),
  resumo TEXT CHECK(length(resumo) <= 800), estado TEXT NOT NULL, origem TEXT, grau TEXT CHECK(grau IN ('A','B','C')),
  criado TEXT NOT NULL, atualizado TEXT NOT NULL, legado INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS no_pai ON no(pai, tipo, estado);
CREATE TABLE IF NOT EXISTS alvo(no INTEGER PRIMARY KEY REFERENCES no(id), solucao TEXT, prova TEXT);
CREATE TABLE IF NOT EXISTS hipotese(no INTEGER PRIMARY KEY REFERENCES no(id), prob REAL CHECK(prob BETWEEN 0 AND 1),
  refuta_se TEXT);
CREATE TABLE IF NOT EXISTS teste(no INTEGER PRIMARY KEY REFERENCES no(id),
  alcance TEXT NOT NULL CHECK(length(alcance) <= 600), fora TEXT CHECK(length(fora) <= 600),
  porque TEXT NOT NULL CHECK(length(porque) <= 600), previsao TEXT, previsao_em TEXT, controle TEXT,
  controle_tipo TEXT CHECK(controle_tipo IN ('real','plantado','sabotagem','nenhum')),
  instrumento INTEGER REFERENCES no(id), script TEXT, receita TEXT);
CREATE TABLE IF NOT EXISTS execucao(id INTEGER PRIMARY KEY, teste INTEGER NOT NULL REFERENCES no(id),
  versao INTEGER REFERENCES versao(id), script_sha TEXT, host TEXT, pid INTEGER, log TEXT, inicio TEXT, fim TEXT,
  n TEXT, controle_ok INTEGER, resultado TEXT CHECK(resultado IN ('positivo','negativo','inconclusivo','falhou')),
  nota TEXT, sentido TEXT);
CREATE TABLE IF NOT EXISTS instrumento(no INTEGER PRIMARY KEY REFERENCES no(id), caminho TEXT UNIQUE, verificador TEXT);
CREATE TABLE IF NOT EXISTS versao(id INTEGER PRIMARY KEY, instrumento INTEGER NOT NULL REFERENCES no(id),
  sha TEXT NOT NULL, quando TEXT NOT NULL, verificado INTEGER, nota TEXT);
CREATE TABLE IF NOT EXISTS fato(no INTEGER PRIMARY KEY REFERENCES no(id), natureza TEXT, fonte INTEGER REFERENCES no(id),
  local TEXT, citacao TEXT CHECK(length(citacao) <= 1000), conferido TEXT, prova TEXT);
CREATE TABLE IF NOT EXISTS fonte(no INTEGER PRIMARY KEY REFERENCES no(id), ref TEXT UNIQUE, sha TEXT,
  procedencia TEXT CHECK(procedencia IN ('primaria','derivada','terceiros','nossa')),
  confiabilidade TEXT CHECK(confiabilidade IN ('A','B','C','D','E','F')), documento INTEGER);
CREATE TABLE IF NOT EXISTS entidade(no INTEGER PRIMARY KEY REFERENCES no(id), classe TEXT, aliases TEXT);
CREATE TABLE IF NOT EXISTS atributo(entidade INTEGER REFERENCES no(id), chave TEXT, valor TEXT,
  fato INTEGER REFERENCES no(id), quando TEXT, PRIMARY KEY(entidade, chave));
CREATE TABLE IF NOT EXISTS decisao(no INTEGER PRIMARY KEY REFERENCES no(id), proibe TEXT, permite TEXT);
CREATE TABLE IF NOT EXISTS aresta(de INTEGER NOT NULL REFERENCES no(id), tipo TEXT NOT NULL,
  para INTEGER NOT NULL REFERENCES no(id), nota TEXT CHECK(length(nota) <= 200), criado TEXT, PRIMARY KEY(de, tipo, para));
CREATE TABLE IF NOT EXISTS ach(fato INTEGER REFERENCES no(id), hipotese INTEGER REFERENCES no(id), valor TEXT NOT NULL,
  nota TEXT, PRIMARY KEY(fato, hipotese));
CREATE TABLE IF NOT EXISTS legado(ref TEXT PRIMARY KEY, no INTEGER NOT NULL REFERENCES no(id));
CREATE TABLE IF NOT EXISTS conexao(no INTEGER PRIMARY KEY REFERENCES no(id), de INTEGER NOT NULL REFERENCES no(id),
  para INTEGER NOT NULL REFERENCES no(id), relacao TEXT NOT NULL, rival TEXT CHECK(length(rival) <= 400),
  discriminador TEXT CHECK(length(discriminador) <= 400), canal TEXT);
CREATE TABLE IF NOT EXISTS evento(id INTEGER PRIMARY KEY, no INTEGER, acao TEXT NOT NULL, texto TEXT, quando TEXT NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS idx USING fts5(ref UNINDEXED, texto, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS ramo(no INTEGER PRIMARY KEY REFERENCES no(id), de_passo INTEGER REFERENCES passo(id));
CREATE TABLE IF NOT EXISTS passo(id INTEGER PRIMARY KEY, ramo INTEGER NOT NULL REFERENCES no(id), tipo TEXT NOT NULL,
  texto TEXT NOT NULL CHECK(length(texto) <= 400), porque TEXT CHECK(length(porque) <= 400), nos TEXT,
  quando TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS passo_ramo ON passo(ramo, id);"""
OLD_CORPUS = """CREATE TABLE IF NOT EXISTS colecao(nome TEXT PRIMARY KEY, criado TEXT DEFAULT CURRENT_TIMESTAMP);
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
  fmt TEXT DEFAULT 'f4');  -- f4 = float32, f2 = float16 (metade do disco); sempre normalizado"""


def test_old_portuguese_database_and_commands():
    """A case and a corpus created the old way (Portuguese tables, columns, values, files and variables) are
    migrated once on open, and the old commands, options and values keep working on them."""
    r = Path(tempfile.mkdtemp())
    d = r / "casos" / "demo"
    d.mkdir(parents=True)
    (d / "CASO.md").write_text("# demo\n")
    (d / "MAPA.md").write_text("old map\n")
    (r / ".holmes").mkdir()
    (r / ".holmes" / "ativo").write_text("demo")
    (r / ".holmes" / "ramo-demo").write_text("9")
    t = "2026-01-01 00:00:00"
    db = sqlite3.connect(d / "caso.db")
    db.executescript(OLD_SCHEMA)
    db.executemany("INSERT INTO no(id, tipo, pai, titulo, estado, origem, criado, atualizado) VALUES (?,?,?,?,?,?,?,?)", [
        (1, "objetivo", None, "Descobrir quem escreveu a carta", "aberto", "usuario", t, t),
        (2, "frente", 1, "Tinta", "ativa", "agente", t, t),
        (3, "hipotese", 2, "A tinta data a carta", "viva", "agente", t, t),
        (4, "teste", 3, "Ferro", "feito", "agente", t, t),
        (5, "fato", None, "A carta cita a tinta", "vigente", "fonte", t, t),
        (6, "pista", None, "Talvez seja um canhoto", "aberta", "externo", t, t),
        (7, "leitura", None, "A carta finge ser antiga", "vigente", "agente", t, t),
        (8, "questao", 2, "Quando a tinta foi feita?", "aberta", "agente", t, t),
        (9, "ramo", 8, "Linha da tinta", "ativo", "agente", t, t),
        (10, "entidade", None, "Carta escrita", "ativa", "agente", t, t)])
    db.execute("INSERT INTO hipotese VALUES (3, 0.5, 'tinta moderna')")
    db.execute("INSERT INTO teste(no, alcance, porque, controle_tipo) VALUES (4, 'a', 'p', 'plantado')")
    db.execute("INSERT INTO execucao(teste, inicio, fim, resultado, nota, sentido) VALUES "
               "(4, ?, ?, 'negativo', 'nada', 'nenhum: nada legivel aqui')", (t, t))
    db.execute("INSERT INTO fato(no, natureza, local, citacao, conferido) VALUES (5, 'citacao', 'folha 1', 'tinta', ?)", (t,))
    db.execute("INSERT INTO fato(no, natureza) VALUES (6, 'inferencia')")
    db.execute("INSERT INTO entidade VALUES (10, 'evento', NULL)")
    db.execute("INSERT INTO atributo VALUES (10, 'quando', '1897-03-01', 5, ?)", (t,))
    db.executemany("INSERT INTO aresta VALUES (?,?,?,?,?)", [(7, "depende", 5, None, t), (7, "sobre", 8, "decisiva", t),
                                                           (3, "responde", 8, None, t)])
    db.execute("INSERT INTO ramo VALUES (9, NULL)")
    db.execute("INSERT INTO passo(ramo, tipo, texto, porque, quando) VALUES (9, 'abriu', 'nasce de Q8', 'comecar', ?)", (t,))
    db.executemany("INSERT INTO evento(no, acao, texto, quando) VALUES (?,?,?,?)", [
        (7, "criou", "leitura: A carta finge ser antiga", t), (3, "viva→apoiada", "T4", t), (3, "apoiada→viva", "volta", t)])
    db.commit()
    db.close()
    (r / "corpus").mkdir()
    c = sqlite3.connect(r / "corpus" / "corpus.db")
    c.executescript(OLD_CORPUS)
    c.execute("INSERT INTO colecao(nome) VALUES ('demo')")
    c.execute("INSERT INTO documento(id, colecao, ref, titulo, tipo) VALUES (1, 'demo', '/x/carta.md', 'carta.md', 'texto')")
    c.execute("INSERT INTO pedaco(documento, kind, ordem, texto) VALUES (1, 'secao', 0, 'A tinta ferrogalica escurece')")
    c.commit()
    c.close()

    m = run(r, "mapa", old_env=True)                                     # old command, old variables: migrates here
    assert "# MAP — demo" in m and "decisive question: Q8" in m and "ACTIVE BRANCH B9" in m
    assert "1 hypothesis supported (H3)" in m                            # old event actions still drive the alerts
    assert (d / "case.db").exists() and not (d / "caso.db").exists() and (d / "CASE.md").exists() and (d / "MAP.md").exists()
    with sqlite3.connect(d / "case.db") as db:
        tables = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "node" in tables and "no" not in tables and "aresta" not in tables
        assert dict(db.execute("SELECT id, type FROM node WHERE id IN (5, 6, 9)").fetchall()) == {5: "fact", 6: "clue", 9: "branch"}
        assert db.execute("SELECT result, meaning FROM run").fetchone() == ("negative", "none: nada legivel aqui")
        assert db.execute("SELECT control_type FROM test").fetchone()[0] == "planted"
        migrated = lambda: db.execute("SELECT count(*) FROM event WHERE action='migrated'").fetchone()[0]
        assert migrated() == 1
    assert "[fact:current quote/source/-]" in run(r, "ver", "E5", old_env=True)
    assert "K6 [clue:open inference/external/-]" in run(r, "ver", "K6", old_env=True)
    k = run(r, "novo", "pista", "Outra pista", "--natureza", "relato", "--origem", "externo", old_env=True).strip()
    assert k.startswith("K") and "[clue:open report/external/C]" in run(r, "ver", k, old_env=True)
    assert "K6: open → dropped" in run(r, "estado", "K6", "descartada", "sem base", old_env=True)
    assert "F2: active → parked" in run(r, "estado", "F2", "estacionada", "pausa", old_env=True)
    run(r, "estado", "F2", "ativa", "volta", old_env=True)
    run(r, "liga", "E5", "sustenta", "H3", old_env=True)
    assert "→ supports H3" in run(r, "ver", "E5", old_env=True)
    t2 = run(r, "teste", "H3", "Ferro de novo", "--alcance", "b", "--porque", "p", "--controle", "folha",
             "--controle-tipo", "real", old_env=True).split()[0]
    out = run(r, "resultado", t2, "negativo", "nada", "--controle-ok", "sim", "--sentido", "revisar: ler de novo a saida",
              old_env=True)
    assert "→ negative" in out
    assert "INDETERMINATE" in run(r, "ja", "ferro de novo", old_env=True)
    assert "proven by measurement" in run(r, "confere", k, "ok", "--por", "medicao", "--prova", "true", old_env=True)
    assert run(r, "passo", "pensou", "a tinta e antiga", "--porque", "ferro", old_env=True).startswith("B9 step")
    assert "thought: a tinta e antiga" in run(r, "trilha", old_env=True)
    assert "1897-03-01" in run(r, "cronologia", old_env=True)            # class 'evento' and key 'quando' translated
    assert "corpus #1" in run(r, "busca", "tinta ferrogalica", old_env=True)
    assert "#1" in run(r, "busca", "escurece", "--modo", "literal", script="corpus.py", old_env=True)
    st = json.loads(run(r, "abertura", script="hooks.py", stdin=json.dumps({"source": "startup"}), old_env=True))
    assert "Active case: demo" in st["hookSpecificOutput"]["additionalContext"]
    run(r, "ramo", "solta", old_env=True)
    assert "ACTIVE BRANCH: none" in run(r, "mapa", "--tudo", old_env=True)
    with sqlite3.connect(d / "case.db") as db:                           # opened many times, migrated once
        assert db.execute("SELECT count(*) FROM event WHERE action='migrated'").fetchone()[0] == 1
    with sqlite3.connect(r / "corpus" / "corpus.db") as c:
        assert c.execute("SELECT kind, position, text FROM chunk").fetchone() == ("section", 0, "A tinta ferrogalica escurece")


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
