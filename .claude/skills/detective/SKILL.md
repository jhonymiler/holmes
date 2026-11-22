---
name: detective
description: "Investigation method for any case with fragmented evidence, competing hypotheses or risk of jumping to conclusions: puzzle, audit, research, data forensics. Use when opening or resuming a case, generating hypotheses, planning or judging a test, deciding whether a pattern is real, or coordinating the agent team. Triggers: investigate, case, hypothesis, clue, evidence, test, pattern, audit, forensics, resume, detetive, investigar, caso, hipótese, pista, evidência, teste, padrão, auditoria, perícia, retomar."
---

# Detective

A short protocol. Details live in `references/`, loaded only when a step calls for them. Command names and
states are the CLI's own tokens.

## Map first

Before any other action, and again at every decision: `python3 -I holmes/holmes.py map`.
The map is the overall plan. If an action does not serve one of its targets or fronts, do not do it.
Before testing or claiming something new: `tried "<term>"`; before summarizing a theme: `dossier "<terms>"`. A previous finding: `show <id>`, and read all of it.
The map's `CURRENT READING` is the story the case seems to tell: every test must make sense within it.
When resuming: `sheet` (where we are and why) and, if needed, `trail` (the whole path to the active branch).
Every action is a step of a branch; with no active branch, pick one (`tree`, `branch use B..`) or open one.

## Meaning before mechanics

Clues and sources are read in layers (literal, figurative, allusion, function, subliminal, absence) before
becoming an operation. Every result gets two judgments: number (null, control, scope) and meaning (what the
output says in context). A hypothesis is a concept; a test is one form of it; a 0 closes the form. → skill
`reading`

## Four laws

1. Looking true is not evidence. What was observed is not what one thinks happened.
2. Evidence compatible with every hypothesis distinguishes none.
3. In a chain, probability is the product of the links. Each extra detail makes the story less likely.
4. A hit is worth the freedom spent to get it. Attempts and analysis choices count.

## Working mode (declare it before acting)

| Mode | Does | Does not |
|---|---|---|
| READING | Reads sources, formulates hypotheses, records facts and threads | Run tests |
| SURGERY | 1 to 3 pinpoint tests, each tied to a hypothesis | Widen the space |
| SWEEP | Broad search | Start without a hypothesis anchored in a primary source and an estimated cost |

When in doubt, READING. Change modes explicitly.

## Record

Every fact, hypothesis and decision goes to the record, not the conversation.

| Mark | Command |
|---|---|
| Literal source excerpt | `quote <corpus chunk> "<claim>"` (copies the text; the fact comes out proven by the source; an interpretation of the excerpt is refused: it is a clue) |
| Fact (a finding already proven) | `new fact "<t>" --nature observation\|measurement\|quote --by source\|measurement\|test\|reproduction [--proof "<command>"\|T..] --source S.. --grade A\|B\|C` |
| Clue (not yet proven) | `new clue "<t>" --nature observation\|measurement\|quote\|report\|inference\|interpretation --origin ..` |
| Proving a clue | `prove K.. "<note>" --by ..` (an observation, measurement, quote or report clue becomes a fact, same id, at grade A, with a `changed` step in the active branch; an inference or interpretation never does) |
| Report from a third party, another AI, an old note | `new clue "<t>" --nature report --origin external` (grade C until proven; proving raises it to A) |
| Dropping a clue | `state K.. dropped "<why>"` |
| Hypothesis | `new hypothesis "<t>" --parent <front> --prob 0.4 --refuted-if "<what would refute it>"` |
| Premise | `new premise "<t>" --parent <front>` + `link <H> depends <R>` |
| Weight of evidence | `ach <E> <H> CC\|C\|N\|I\|II`; `ach <F>` shows the matrix and what is diagnostic |
| Test | `test <hyp> "<t>" --scope .. --why "if + opens X; if − closes Y" --prediction .. --control .. --control-type real --instrument I.. [--script <path>]`; attach the script later with `edit <T> --script <path>` |
| Run | `run <T> --pid <pid> --log <file>` (long) or straight `result` (quick) |
| Cheap hunch | `test <hyp> "<t>" --scope .. --why .. --exploratory` (counts as a lead; needs no `--refuted-if`) |
| Result | `result <T> positive\|negative\|inconclusive\|failed "<note>" [--meaning "<what it says>"\|"none: <why>"\|"revisit: <what>"] --n <size> --control-ok yes\|no` |
| Question | `new question "<question>" --parent <front\|target\|O\|Q>`; a hypothesis that answers it: `link <H> answers <Q>`; `questions` |
| Possible relation | `connections <id\|"concept">` (query) → `connection <from> <to> <relation> "<why>" --rival .. --discriminator ..` → `state C.. confirmed\|rejected "<evidence>"` |
| Source with many units | JSON contract → `extract f.json` (plan) → `--apply` (`references/extraction.md`) |
| Working theory | `reading "<picture>" --supports E.. --rival H.. --question Q.. --gap Q.. --reason "<what changed>"` |
| Hypothesis criterion | `edit <H> --refuted-if "<what would refute it>"` (a confirmatory test requires it) |
| Getting oriented | `next` (what to do and why) · `chain <id>` (what something rests on) · `timeline` |
| Line of reasoning | `branch new "<question>" --from <id> --why "<why open it>"`; `branch use B..`; `sheet` · `trail` · `tree` |
| Go back and take another direction | `branch new ".." --from B.. --step N --why ".."` (fork: inherits only the steps up to N) |
| Reasoning without a test | `step read\|thought\|found\|corrected\|decided\|next ".." --why ".." [--nodes E..,T..]` |
| Rival readings of the same clue | one sibling branch each, under the same question or branch; never a queue |
| Line paused or dead | `state B.. paused\|dead\|concluded "<tested scope or reason>"` |
| Hypothesis or premise refuted | `state <H\|R> refuted "<id of the test or fact that showed it>"`; a front: `state F.. closed\|discarded "<why>"` |
| User decision | `new decision "<t>" --origin user --forbids ".." --allows ".."` (your own choice of method is a clue `new clue --nature inference`) |
| Loose end | `new thread "<t>"` |
| Conflict | `link <E1> contradicts <E2>` (stays on the map until one is retracted) |
| Recurring object | `new entity "<name>" --class .. --alias "synonym,spelling"`; `attribute <N> <key> <value> --fact E..` |

Absence is only a fact with its scope: "there is no X in Y, searched by Z". It weighs against a hypothesis
only when the hypothesis predicts presence and the method has measured sensitivity to find it.

## Cycle

**F0 Collection.** Collect before analysing. Originals are read-only; a derivative points to its parent.
`source <path>`. → `custody.md`

**F1 Reading.** Order: what has already been done (`tried`), the raw source with your own reading written first,
metadata, earlier interpretations, third-party solutions last. Read in layers (skill `reading`). A reading by
tool calls for an independent second reading. From material to question: observation → clue → connection →
question. → `reading.md`, `extraction.md`

**F2 Hypotheses.** Real rivals, not a quota: consider chance, plain technical error, deception and artefact
when plausible. Only the refuted one leaves. Probabilities sum to 1 only among mutually exclusive rivals (with
"other"); explanations that can coexist are not normalized. → `hypotheses.md`

**F3 Pre-assessment.** Before a test costing more than minutes: which hypothesis does the result exclude? If
none, it does not run. Numerical prediction, control with measured power, estimated cost, declared scope.
→ `quantitative.md`

**F4 Execution.** A control in every run. Script and log in the `test` (`test .. --script <path>` at creation, or
`edit <T> --script <path>` later). Instrument recorded with `instrument`; if it changes, old negatives become
TO REVALIDATE. → `validation.md`

**F5 Evaluation.** Are the propositions those of F2? Compare with the maximum under noise. List
discrepancies. Read the output as text and form, not just as a count (`--meaning`). A positive comes out as a
candidate, never as a finding. → `validation.md`

**F6 Verification.** Whoever judges did not write the test. Blind verifier, with decoys.

**F7 Revision.** Retracted something: reassess what depends on it. Change of leading hypothesis: estimate from
scratch before looking at the old one. The old one does not vanish: it becomes a paused or dead branch with
the reason; the new one only defeats it by showing something it does not explain.

## Proportionality

| Action | Requires |
|---|---|
| Reading, factual question | Nothing |
| Cheap attempt (< 10 min) | `test --exploratory` + `result`; counts as a lead, not as coverage |
| Test cited as evidence | F3 (excludes what, cost) and a control |
| Sweep or closing a line | F0 to F5 |
| Declaring a finding | F0 to F7 |

The gates protect claims, not attempts. "F3 is missing" is no reason not to try something cheap. Stuck case:
`exploration.md`.

## Concluding

Two separate sentences (`scales.md`): probability with a number ("likely, 55–80%") and confidence in the
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
agent's. Delegation rules: `agents.md`.

| Phase | Agent |
|---|---|
| F0 | `archivist` |
| F1, F2 with an external source | `researcher` |
| F1 to F3 | `analyst` |
| F1, overall reading, case stuck in mechanics | `interpreter` (without seeing your reading) |
| F4 | `engineer`, then `reviewer` |
| F6 | `verifier` |
| Before recording a negative | `skeptic` |

An agent's report comes in at grade C, as a clue, until checked against the source (skill `check-report`) and proven; proving raises it to A.

## Anti-patterns

- Acting without reading the map. Redoing what `tried` would show.
- Opening a new direction without a branch, or correcting course by rewriting instead of recording the step.
- Treating competing readings as a succession (the newest "corrects" the previous one).
- Hunting for confirmation of the first hypothesis.
- Reading a clue as a string: testing the word as a password, sweeping a book for a term, judging meaning by p.
- Declaring the concept dead because one form of it gave 0.
- A pattern found after looking, with no prediction or control.
- Recording intention as a result.
- Recording an inference, an interpretation or an unproven report as a fact: it is a clue (or a hypothesis).
- Delegating without context; or delegating verification together with the verdict.

## References

| File | When |
|---|---|
| `reading.md` | F1 |
| `hypotheses.md` | F2 |
| `quantitative.md` | F3, F5 |
| `validation.md` | F4 to F6 |
| `custody.md` | F0 |
| `scales.md` | Concluding |
| `biases.md` | Revision |
| `templates.md` | Record templates per phase |
| `extraction.md` | New material: observation, clue, connection, question, JSON contract |
| `exploration.md` | Stuck case |
| `agents.md` | Before delegating |
| `crypto.md` | Optional: cases with ciphers |
| `bibliography.md` | Bibliography |
