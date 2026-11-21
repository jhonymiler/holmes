#!/usr/bin/env python3
"""holmes 2.0 shell hooks (declared in .claude/settings.json). Reads the event JSON on stdin.

    start       SessionStart      map of the ACTIVE case (≤ 3.5 KB) + tail of the journal after compacting/resuming
    prompt      UserPromptSubmit  up to 6 database lines about the request (not repeated in the session) + tunnel + pending reading
    guard       PreToolUse(Bash)  denies `pkill -f` (it kills its own shell)
    post        PostToolUse(Bash) a case script ran without a recorded test → reminder visible to the agent
    stop        Stop              rewrites the journal; asks for a record if a case script ran without calling holmes.py
    pre-compact PreCompact        rewrites the journal before the cut

The old Portuguese arguments (abertura, pistas, guarda, pos, fim) are still accepted.
Everything a hook injects stays under 10,000 characters: above that Claude Code swaps the text for a 2 KB
preview. A hook never breaks the session: any error becomes silence + a line on stderr.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import holmes as H  # noqa: E402

STATE = H.STATE_DIR
MAX_JOURNAL = int(H.env("HOLMES_MAX_JOURNAL", "HOLMES_MAX_DIARIO") or 120_000)
SCRIPT = re.compile(r"\b(?:python3?|\S*/bin/python)\b(?:\s+-\S+)*\s+([\w./-]+\.py)\b")


def output(event, text):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text[:9000]}}


def holmes(*args):
    r = subprocess.run([sys.executable, "-I", str(HERE / "holmes.py"), *args], capture_output=True, text=True,
                       timeout=20, cwd=H.ROOT, env={**os.environ, "HOLMES_HOOK": "1"})
    return (r.stdout or r.stderr).strip()


def journal_of(ev):
    return STATE / "journal" / f"{ev.get('session_id', 'session')}.md"


def update_journal(ev):
    """Only user messages and agent text (the reasoning, ~7% of the window); commands and outputs stay out.
    Regenerated from the .jsonl every turn, so it is idempotent and survives compaction."""
    events, whole = tail(ev["transcript_path"], 16 << 20)
    body = build_journal(events)
    if not whole and len(body) < MAX_JOURNAL * 0.9:  # the tail was not enough to fill the journal: read everything
        body = build_journal(tail(ev["transcript_path"], None)[0])
    target = journal_of(ev)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# Journal of session {ev.get('session_id', '?')} (generated; do not edit)\n{body}", encoding="utf-8")
    return target


def tail(transcript, nbytes):
    """Events of the .jsonl reading only the last nbytes (None = everything). The transcript reaches 80 MB, and
    reading it all every turn cost ~4.6 s at Stop; the tail is almost always enough. Returns (events, read_whole_file)."""
    with open(transcript, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        start = 0 if nbytes is None or size <= nbytes else size - nbytes
        f.seek(max(start - 1, 0))
        data = f.read()
    if start:  # drop only the cut line piece (reading 1 byte before: if the cut fell at a line start, nothing is lost)
        data = data[data.find(b"\n") + 1:]
    lines = data.decode("utf-8", errors="replace").split("\n")  # not splitlines: U+2028 is valid text inside JSON
    events = []
    for l in lines:
        try:
            events.append(json.loads(l))
        except ValueError:
            pass
    return events, start == 0


def build_journal(events):
    blocks = []
    for e in events:
        c, when = (e.get("message") or {}).get("content"), (e.get("timestamp") or "")[:16].replace("T", " ")
        if e.get("type") == "user" and not e.get("isMeta") and not e.get("isCompactSummary"):
            for x in [c] if isinstance(c, str) else [b.get("text", "") for b in c or []
                                                     if isinstance(b, dict) and b.get("type") == "text"]:
                if x.strip():
                    blocks.append(f"\n## [{when}] user\n{x.strip()}")
        elif e.get("type") == "assistant":
            for b in c or []:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                    blocks.append(f"\n### [{when}] agent\n{b['text'].strip()}")
    body = ""
    for b in reversed(blocks):  # keeps the most recent; the .jsonl keeps the rest
        if len(body) + len(b) > MAX_JOURNAL:
            body = body or b[-MAX_JOURNAL:]  # one block bigger than the journal: keep its tail, not nothing
            break
        body = b + body
    return body


def start(ev):
    try:
        case = H.active_case()
    except H.Error as e:
        return output("SessionStart", f"[holmes] {e}. Existing cases: {', '.join(H.cases()) or 'none'}.")
    parts = [f"[holmes] Active case: {case}. Follow first what the user asks in this message; the map is "
             "orientation, not a task.", holmes("map")]
    d = journal_of(ev)
    if not d.exists():  # a journal written before the rename
        d = STATE / "diario" / d.name
    if ev.get("source") in ("compact", "resume") and d.exists():
        parts.append(f"[holmes] End of this session's journal (in full at {d.relative_to(H.ROOT)}):\n"
                     + d.read_text(encoding="utf-8")[-2500:])
    return output("SessionStart", "\n\n".join(parts))


def prompt(ev):
    text = ev.get("prompt", "")
    if len(H.C.terms(text)) < 3:
        return None
    try:
        case = H.active_case()
    except H.Error:
        return None
    seen_f = STATE / "sessions" / f"{ev.get('session_id', 'x')}.seen"
    old_f = STATE / "sessoes" / f"{ev.get('session_id', 'x')}.vistos"  # written before the rename
    src = seen_f if seen_f.exists() else old_f
    seen = set(src.read_text().split("\n")) if src.exists() else set()
    key = lambda l: " ".join(l.split(" ", 2)[:2]) if l.startswith("corpus") else l.split(" ", 1)[0]  # "H12" or "corpus #37"
    lines = [l for l in holmes("search", text, "-n", "6").splitlines()
             if l and not l.startswith((" ", "(")) and key(l) not in seen][:6]
    with H.connect(case) as db:
        alert = [f"⚠ tunnel in F{f['id']} ({H.tunnel_warning(*t)}): read before testing"
                 for f in db.execute("SELECT id FROM node WHERE type='front' AND state='active'").fetchall()
                 if (t := H.tunnel(db, f["id"]))[0] >= H.TUNNEL]
        req = H.reading_request(db)
        if req:
            alert.append("⚠ " + req)
    if not lines and not alert:
        return None
    seen_f.parent.mkdir(parents=True, exist_ok=True)
    seen_f.write_text("\n".join(seen | {key(l) for l in lines}))
    body = "\n".join(alert + lines)[:1500]
    return output("UserPromptSubmit", f"[holmes] The database already has this about it (detail: `holmes.py show <id>`):\n{body}")


def guard(ev):
    cmd = (ev.get("tool_input") or {}).get("command", "")
    if re.search(r"\bpkill\s+(-\w*\s+)*-\w*f", cmd):
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": "[holmes] `pkill -f` matches its own shell's command line and kills it. "
                                            "Kill by explicit PID (recorded in the test)."}}
    return None


def runs_case_script(cmd):
    try:
        case = H.active_case()
    except H.Error:
        return None, None
    m = SCRIPT.search(cmd)
    if m and not m[1].endswith(("holmes.py", "hooks.py")) and (
            any(f"{root}/{case}/" in cmd for root in ("cases", "casos", H.CASES.name)) or "/scripts/" in m[1]):
        return case, m[1]
    return None, None


def post(ev):
    case, script = runs_case_script((ev.get("tool_input") or {}).get("command", ""))
    if not script:
        return None
    with H.connect(case) as db:
        ok = db.execute("SELECT 1 FROM test t JOIN node n ON n.id=t.node WHERE n.state IN ('planned','running') "
                        "AND t.script LIKE ?", (f"%{Path(script).name}%",)).fetchone()
    if ok:
        return None
    return output("PostToolUse", f"[holmes] {Path(script).name} ran without an open test that cites it. If it was "
                  "exploration, fine; if the result is going to support or discard something, record it with "
                  "`holmes.py test <H> ... --script` and `result`, with a scope, otherwise it does not count as closing anything.")


def last_turn(transcript):
    events, whole = tail(transcript, 4 << 20)
    if not whole and not any(e.get("type") == "user" and not e.get("isMeta") for e in events):
        events = tail(transcript, None)[0]  # turn bigger than the tail
    begin = max((i for i, e in enumerate(events) if e.get("type") == "user" and not e.get("isMeta") and (
        isinstance((e.get("message") or {}).get("content"), str) or any(
            isinstance(b, dict) and b.get("type") == "text" for b in (e.get("message") or {}).get("content") or []))),
        default=0)
    return [b.get("input") or {} for e in events[begin:] if e.get("type") == "assistant"
            for b in (e.get("message") or {}).get("content") or []
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Bash"]


def stop(ev):
    try:
        update_journal(ev)
    except Exception as e:  # the journal is a bonus; it never brings down the end of the turn
        print(f"[holmes] journal failed: {e}", file=sys.stderr)
    if ev.get("stop_hook_active"):
        return None
    cmds = [i.get("command", "") for i in last_turn(ev["transcript_path"])]
    ran = next((s for c in cmds for _, s in [runs_case_script(c)] if s), None)
    if ran and not any("holmes.py" in c for c in cmds):
        return {"decision": "block", "reason":
                f"[holmes] {Path(ran).name} ran in this turn and nothing was recorded. Record what it showed "
                "(`holmes.py result T.. ` or `new fact`/`new clue`/`new thread`), or say in one line why there is nothing "
                "to record. If it is still running, record the PID and the log in the test."}
    return None


def pre_compact(ev):
    update_journal(ev)
    return None


ACTIONS = {"start": start, "prompt": prompt, "guard": guard, "post": post, "stop": stop, "pre-compact": pre_compact}
OLD_ACTIONS = {"abertura": "start", "pistas": "prompt", "guarda": "guard", "pos": "post", "fim": "stop"}


def mark(action, ok):
    """Proof of execution, not of configuration: when each hook last ran (`holmes.py health`)."""
    f = STATE / "hooks.json"
    try:
        v = json.loads(f.read_text()) if f.exists() else {}
        v = v if isinstance(v, dict) else {}
        v[action] = f"{H.now()} {'ok' if ok else 'FAILED'}"
        f.parent.mkdir(exist_ok=True)
        f.write_text(json.dumps(v, ensure_ascii=False))
    except (OSError, ValueError):
        pass  # the record is a diagnostic; it never brings down the hook


if __name__ == "__main__":
    name = OLD_ACTIONS.get(sys.argv[1], sys.argv[1]) if len(sys.argv) > 1 else ""
    try:
        r = ACTIONS[name](json.load(sys.stdin))
        mark(name, True)
        if r:
            print(json.dumps(r, ensure_ascii=False))
    except Exception as e:
        if name in ACTIONS:  # an unknown or empty argument is not a hook that ran
            mark(name, False)
        print(f"[holmes] hook {sys.argv[1:]} failed: {e}", file=sys.stderr)
