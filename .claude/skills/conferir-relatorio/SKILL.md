---
name: conferir-relatorio
description: "Checks a report from a subagent, an external AI or another session against the primary source before recording it in the case. Use when an agent returns a result, when the user asks to 'check' or 'verify what it said' (confere, verifica o que ele disse), or before bringing anything from outside into the record."
---

# Checking a report against the source

Everything that comes from outside (subagent, external AI, another session, third parties) enters at
**grade C** until checked. Agents frequently get ids, lines and quotes wrong.

## Steps

1. **Write your own judgment before reading the whole report**, if the point is decisive.
2. **Integrity of what it edited.** Compare with the previous version (`diff`, `git diff`). Count removed
   lines. An unrequested removal: show the user before accepting.
3. **Every cited id:** `python3 -I holmes/holmes.py ver <id>`. Does the text say what the report claims?
4. **Every document quote:** open the source at the given line (`sed -n '<a>,<b>p' <file>`). Quote the
   excerpt, not the agent's paraphrase.
5. **Every number or result:** rerun the command or script that produced it, or check the log. Say whether the
   result is **real** (case data) or **synthetic** (test data, simulation, example).
6. **"Never tested" / "not in the record":** `ja "<term>"` and `busca "<term>"` with synonyms. Often the term
   came in under another role. Say which.
7. **A fact from outside the repository** (a work, an event, a specification): without a source read, record
   it as an external report (`novo fato --natureza relato --origem externo`: grade C, draft), never as a proven
   fact nor as a case premise. It becomes a premise only if a line needs to assume it, declared
   (`novo premissa`).
8. **Record only what was checked:**
   - checked against the primary source: `cita <chunk> "<t>"`, or `novo fato "<t>" --origem externo` followed
     by `confere <E> "<where it was checked>" --por fonte`;
   - reproduced by you (rerun, recomputed): `confere <E> "<what was rerun>" --por reproducao --prova "<command>"`;
   - not checked: `novo fato "<t>" --natureza relato --origem externo` (stays a draft, grade C), or do not record;
   - a lead without proof: `novo fio "<t>"`;
   - links: `liga <from> <type> <to>` **only after** seeing the id printed by `novo`.
9. **Fix the document** the agent edited where it was wrong, and tell the user what was discarded and why.

## Output for the user

A short table: item | checked? | where | real or synthetic | recorded as (id).
Then, in a sentence of your own, what was **not** checked and why.
