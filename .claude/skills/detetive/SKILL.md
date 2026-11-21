---
name: detetive
description: "Investigation method for any case with fragmented evidence, competing hypotheses or risk of jumping to conclusions: puzzle, audit, research, data forensics. Use when opening or resuming a case, generating hypotheses, planning or judging a test, deciding whether a pattern is real, or coordinating the agent team. Triggers: investigate, case, hypothesis, clue, evidence, test, pattern, audit, forensics, resume, investigar, caso, hipótese, pista, evidência, teste, padrão, auditoria, perícia, retomar."
---

# Detective

A short protocol. Details live in `references/`, loaded only when a step calls for them. Command names and
states are the CLI's own tokens, in Portuguese.

## Map first

Before any other action, and again at every decision: `python3 -I holmes/holmes.py mapa`.
The map is the overall plan. If an action does not serve one of its targets or fronts, do not do it.
Before testing or claiming something new: `ja "<term>"`. A previous finding: `ver <id>`, and read all of it.
The map's `LEITURA ATUAL` is the story the case seems to tell: every test must make sense within it.
When resuming: `ficha` (where we are and why) and, if needed, `trilha` (the whole path to the active branch).
Every action is a step of a branch; with no active branch, pick one (`arvore`, `ramo usa B..`) or open one.

## Meaning before mechanics

Clues and sources are read in layers (literal, figurative, allusion, function, subliminal, absence) before
becoming an operation. Every result gets two judgments: number (null, control, scope) and meaning (what the
output says in context). A hypothesis is a concept; a test is one form of it; a 0 closes the form. → skill
`leitura`

## Four laws

1. Looking true is not evidence. What was observed is not what one thinks happened.
2. Evidence compatible with every hypothesis distinguishes none.
3. In a chain, probability is the product of the links. Each extra detail makes the story less likely.
4. A hit is worth the freedom spent to get it. Attempts and analysis choices count.

## Working mode (declare it before acting)

| Mode | Does | Does not |
|---|---|---|
| LEITURA (reading) | Reads sources, formulates hypotheses, records facts and threads | Run tests |
| CIRURGIA (surgery) | 1 to 3 pinpoint tests, each tied to a hypothesis | Widen the space |
| VARREDURA (sweep) | Broad search | Start without a hypothesis anchored in a primary source and an estimated cost |

When in doubt, LEITURA. Change modes explicitly.

## Record

Every fact, hypothesis and decision goes to the record, not the conversation.

| Mark | Command |
|---|---|
| Literal source excerpt | `cita <corpus chunk> "<claim>"` (copies the text and comes out proven by source) |
| Measured or read fact | `novo fato "<t>" --natureza observacao\|medicao --origem medido\|fonte --fonte S.. --grau A\|B\|C` |
| Proving a fact | `confere <E> "<note>" --por fonte\|medicao\|teste\|reproducao [--prova "<command>"\|T..]` (a fact is a proven finding; the proof need not be a source) |
| Interpretation, inference | `novo fato "<t>" --natureza interpretacao\|inferencia --origem agente` (never becomes the author's words, never "proven") |
| Report from a third party, another AI, an old note | `novo fato "<t>" --natureza relato --origem externo` (grade C, draft until `confere`) |
| Hypothesis | `novo hipotese "<t>" --pai <front> --prob 0.4 --refuta-se "<what would refute it>"` |
| Premise | `novo premissa "<t>" --pai <front>` + `liga <H> depende <R>` |
| Weight of evidence | `ach <E> <H> CC\|C\|N\|I\|II`; `ach <F>` shows the matrix and what is diagnostic |
| Test | `teste <hyp> "<t>" --alcance .. --porque "if + opens X; if − closes Y" --previsao --controle --controle-tipo real --instrumento I..` |
| Run | `roda <T> --pid <pid> --log <file>` (long) or straight `resultado` (quick) |
| Cheap hunch | `teste <hyp> "<t>" --alcance .. --porque .. --exploratorio` (counts as a lead; needs no `--refuta-se`) |
| Result | `resultado <T> positivo\|negativo\|inconclusivo\|falhou "<note>" [--sentido "<what it says>"\|"nenhum: <why>"] --n <size> --controle-ok sim\|nao` |
| Question | `novo questao "<question>" --pai <front\|target\|O>`; a hypothesis that answers it: `liga <H> responde <Q>`; `questoes` |
| Possible relation | `conexoes <id\|"concept">` (query) → `conexao <from> <to> <relation> "<why>" --rival .. --discriminador ..` → `estado C.. confirmada\|rejeitada "<evidence>"` |
| Source with many units | JSON contract → `extrai f.json` (plan) → `--aplica` (`references/extracao.md`) |
| Working theory | `leitura "<picture>" --sustenta E.. --rival H.. --questao Q.. --lacuna Q.. --motivo "<what changed>"` |
| Hypothesis criterion | `edita <H> --refuta-se "<what would refute it>"` (a confirmatory test requires it) |
| Getting oriented | `proximo` (what to do and why) · `cadeia <id>` (what something rests on) · `cronologia` |
| Line of reasoning | `ramo novo "<question>" --de <id> --porque "<why open it>"`; `ramo usa B..`; `ficha` · `trilha` · `arvore` |
| Go back and take another direction | `ramo novo ".." --de B.. --passo N --porque ".."` (fork: inherits only the steps up to N) |
| Reasoning without a test | `passo leu\|pensou\|achou\|corrigiu\|decidiu\|proximo ".." --porque ".." [--nos E..,T..]` |
| Rival readings of the same clue | one sibling branch each, under the same question or branch; never a queue |
| Line paused or dead | `estado B.. pausado\|morto\|concluido "<tested scope or reason>"` |
| Line closed | `estado <id> refutada "<id of the test or fact that showed it>"` |
| User decision | `novo decisao "<t>" --origem usuario --proibe ".." --permite ".."` (your own choice of method is a fact `--natureza inferencia`) |
| Loose end | `novo fio "<t>"` |
| Conflict | `liga <E1> contradiz <E2>` (stays on the map until one is retracted) |
| Recurring object | `novo entidade "<name>" --classe .. --alias "synonym,spelling"`; `atributo <N> <key> <value> --fato E..` |

Absence is only a fact with its scope: "there is no X in Y, searched by Z". It weighs against a hypothesis
only when the hypothesis predicts presence and the method has measured sensitivity to find it.

## Cycle

**F0 Collection.** Collect before analysing. Originals are read-only; a derivative points to its parent.
`fonte <path>`. → `custodia.md`

**F1 Reading.** Order: what has already been done (`ja`), the raw source with your own reading written first,
metadata, earlier interpretations, third-party solutions last. Read in layers (skill `leitura`). A reading by
tool calls for an independent second reading. From material to question: observation → clue → connection →
question. → `leitura.md`, `extracao.md`

**F2 Hypotheses.** Real rivals, not a quota: consider chance, plain technical error, deception and artefact
when plausible. Only the refuted one leaves. Probabilities sum to 1 only among mutually exclusive rivals (with
"other"); explanations that can coexist are not normalized. → `hipoteses.md`

**F3 Pre-assessment.** Before a test costing more than minutes: which hypothesis does the result exclude? If
none, it does not run. Numerical prediction, control with measured power, estimated cost, declared scope.
→ `quantitativo.md`

**F4 Execution.** A control in every run. Script and log in the `teste`. Instrument recorded with
`instrumento`; if it changes, old tests become "to revalidate". → `validacao.md`

**F5 Evaluation.** Are the propositions those of F2? Compare with the maximum under noise. List
discrepancies. Read the output as text and form, not just as a count (`--sentido`). A positive comes out as a
candidate, never as a finding. → `validacao.md`

**F6 Verification.** Whoever judges did not write the test. Blind verifier, with decoys.

**F7 Revision.** Retracted something: reassess what depends on it. Change of leading hypothesis: estimate from
scratch before looking at the old one. The old one does not vanish: it becomes a paused or dead branch with
the reason; the new one only defeats it by showing something it does not explain.

## Proportionality

| Action | Requires |
|---|---|
| Reading, factual question | Nothing |
| Cheap attempt (< 10 min) | `teste` + `resultado`; counts as a lead, not as coverage |
| Test cited as evidence | F3 (excludes what, cost) and a control |
| Sweep or closing a line | F0 to F5 |
| Declaring a finding | F0 to F7 |

The gates protect claims, not attempts. "F3 is missing" is no reason not to try something cheap. Stuck case:
`exploracao.md`.

## Concluding

Two separate sentences (`padroes.md`): probability with a number ("likely, 55–80%") and confidence in the
basis (high, moderate, low). Say what would refute it and what changed since the last judgment. "Open, and
here is the test that would decide it" is a valid conclusion. "Seems" without weight is forbidden.

## Stopping

- Conclude when one hypothesis survives, the rivals have hard inconsistencies and a new prediction has been
  confirmed by an independent route.
- Close the line when it only survives with patches, the cost exceeds the value, or three consecutive actions
  moved no probability. A negative closes the tested recipe and lowers confidence in the theme.
- After repeated negatives, go back to the premises (F1, F2) before widening the space.
- Never stop because the answer seems obvious or because you have already invested a lot.

## Team

The coordinator (main session) decides, records and integrates: the integrator role is theirs, not an
agent's. Delegation rules: `agentes.md`.

| Phase | Agent |
|---|---|
| F0 | `arquivista` |
| F1, F2 with an external source | `pesquisador` |
| F1 to F3 | `analista` |
| F1, overall reading, case stuck in mechanics | `interprete` (without seeing your reading) |
| F4 | `engenheiro`, then `revisor` |
| F6 | `verificador` |
| Before recording a negative | `ceticismo` |

An agent's report comes in at grade C until checked against the source (skill `conferir-relatorio`).

## Anti-patterns

- Acting without reading the map. Redoing what `ja` would show.
- Opening a new direction without a branch, or correcting course by rewriting instead of recording the step.
- Treating competing readings as a succession (the newest "corrects" the previous one).
- Hunting for confirmation of the first hypothesis.
- Reading a clue as a string: testing the word as a password, sweeping a book for a term, judging meaning by p.
- Declaring the concept dead because one form of it gave 0.
- A pattern found after looking, with no prediction or control.
- Recording intention as a result.
- Calling an inference a proven fact.
- Delegating without context; or delegating verification together with the verdict.

## References

| File | When |
|---|---|
| `leitura.md` | F1 |
| `hipoteses.md` | F2 |
| `quantitativo.md` | F3, F5 |
| `validacao.md` | F4 to F6 |
| `custodia.md` | F0 |
| `padroes.md` | Concluding |
| `vieses.md` | Revision |
| `fichas.md` | Record templates per phase |
| `extracao.md` | New material: observation, clue, connection, question, JSON contract |
| `exploracao.md` | Stuck case |
| `agentes.md` | Before delegating |
| `cripto.md` | Optional: cases with ciphers |
| `leituras.md` | Bibliography |
