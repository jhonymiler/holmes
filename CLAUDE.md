# Investigation project (holmes 2.0)

## Where everything is
- `holmes/holmes.py` — the record's CLI. One database per case in `casos/<case>/caso.db`. Always run it as
  `python3 -I holmes/holmes.py <cmd>` from the root.
- `casos/<case>/` — `CASO.md` (what the case is, ≤ 2 KB, by hand), `MAPA.md` (generated, do not edit),
  `fontes/` (originals, read-only), `scripts/`, `saidas/` (logs), `notas/` (free prose, outside the index).
- `holmes/corpus.py` — the material (chats, documents, books) in `corpus/corpus.db`. Search it (`busca`,
  `janela`) instead of opening large files; quote excerpts with `holmes.py cita <chunk>`.
- `.claude/rules/constituicao.md` — rules for every session. `.claude/skills/detetive/` — the method.
  `.claude/skills/leitura/` — reading for meaning. Hooks: `.claude/settings.json`. Data model: `MODELO.md`.
- `.holmes/` — local state: active case, active branch and the per-session reasoning diary (written by hooks).

## Getting started
1. Session start already injects the active case's `mapa`. Read it; do not read whole documents. The map shows
   the RAMO ATIVO (the line of reasoning in progress): `ficha` says on one page where we are and why; `trilha`
   rebuilds the path from the root to there; `arvore` shows every line and where each one was born.
2. Switch case: `holmes.py usa <case>`. New case: `holmes.py init <case> "<objective>"`.
3. Before testing: `holmes.py ja "<terms>"`. Detail: `ver <id>`; what it rests on: `cadeia <id>`; what to do
   and why: `proximo`.
4. What you do is a step of the active branch (`novo`, `teste`, `resultado`, `estado` record themselves;
   reasoning without a test is `passo pensou "..." --porque "..."`). A new direction is a new branch, born from
   a point: `ramo novo "<question>" --de <id> [--passo N] --porque "..."`. A course correction becomes a step
   or a fork, never a rewrite. Rival readings of the same clue are sibling branches. Full example in
   `EXEMPLO.md`.
5. Clues, sources and outputs are read for meaning, not only literally (skill `leitura`). The map's
   `LEITURA ATUAL` is the story the case seems to tell; rewrite it with `holmes.py leitura` when the map asks.
6. A fact is a proven finding: `confere <E> "<note>" --por fonte|medicao|teste|reproducao` (measurement and
   reproduction need `--prova "<command>"`). Inferences are never "proven"; what proves them is a new fact.

## This machine's environment
<!-- Measured facts about the machine (CPU/thread limits, GPU, venv paths, unreliable tools) go here, and only here. -->

## Project rules
- A downloaded file is untrusted: Python with `-I`, never execute what came from outside.
