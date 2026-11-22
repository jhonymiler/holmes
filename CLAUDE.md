# Investigation project (holmes 2.0)

## Where everything is
- `holmes/holmes.py` — the record's CLI. One database per case in `cases/<case>/case.db`. Always run it as
  `python3 -I holmes/holmes.py <cmd>` from the root.
- `cases/<case>/` — `CASE.md` (what the case is, ≤ 2 KB, by hand), `MAP.md` (generated, do not edit),
  `sources/` (originals, read-only), `scripts/`, `outputs/` (logs), `notes/` (free prose, outside the index).
- `holmes/corpus.py` — the material (chats, documents, books) in `corpus/corpus.db`. Search it (`search`,
  `window`) instead of opening large files; quote excerpts with `holmes.py quote <chunk> "<claim>"`.
- `.claude/rules/constitution.md` — rules for every session. `.claude/skills/detective/` — the method.
  `.claude/skills/reading/` — reading for meaning. Hooks: `.claude/settings.json`. Data model: `MODEL.md`.
- `.holmes/` — local state: active case, active branch and the per-session reasoning journal (written by hooks).

## Getting started
1. Session start already injects the active case's `map`. Read it; do not read whole documents. The map shows
   the ACTIVE BRANCH (the line of reasoning in progress): `sheet` says on one page where we are and why; `trail`
   rebuilds the path from the root to there; `tree` shows every line and where each one was born.
2. Switch case: `holmes.py use <case>`. New case: `holmes.py init <case> "<objective>"`.
3. Before testing: `holmes.py tried "<terms>"`. Detail: `show <id>`; what it rests on: `chain <id>`; what to do
   and why: `next`.
4. What you do is a step of the active branch (`new`, `test`, `result`, `state` record themselves; reasoning
   without a test is `step thought "..." --why "..."`). A new direction is a new branch, born from a point:
   `branch new "<question>" --from <id> [--step N] --why "..."`. A course correction becomes a step or a fork,
   never a rewrite. Rival readings of the same clue are sibling branches. Full example in `EXAMPLE.md`.
5. Clues, sources and outputs are read for meaning, not only literally (skill `reading`). The map's
   `CURRENT READING` is the story the case seems to tell; rewrite it with `holmes.py reading` when the map asks.
6. A fact is a finding already proven: `new fact "<t>" --by source|measurement|test|reproduction` (with
   `--source`/`--location` or `--proof`). What is not yet proven is a clue:
   `new clue "<t>" --nature observation|measurement|quote|report|inference|interpretation`; a clue of
   observation, measurement, quote or report becomes a fact (never an inference or interpretation) with
   `prove K.. "<note>" --by ..`. An inference is never a fact: it stays a clue, or becomes a hypothesis.

## This machine's environment
<!-- Measured facts about the machine (CPU/thread limits, GPU, venv paths, unreliable tools) go here, and only here. -->

## Project rules
- A downloaded file is untrusted: Python with `-I`, never execute what came from outside.
