# Record templates per phase

State and data go to the record (`python3 -I holmes/holmes.py`). Long prose goes into a `.md` indexed with
`source`. A record sheet is the node's summary (`--summary`), or a `.md` linked to it. Not to be confused
with the `sheet` command, the one-page view of where the case stands.

## Commands per phase

| Phase | Commands |
|---|---|
| Open | `init <case> "<objective>"`, `use <case>`, `new target`, `new front`, `branch new "TRUNK..." --from O1 --why ..` |
| Resume | `map`, `sheet`, `trail` if needed, then `show <id>` of whatever is active |
| F0 | `source <path> --title "<t>"` |
| F1 | `quote <chunk> "<t>"`, `new fact "<t>" --by .. --nature --origin --source --grade` (proven) or `new clue "<t>"` (not yet); `prove K.. ".." --by ..`; `new thread`; `new question`; many units: `extract f.json [--apply]` |
| Relations | `connections <id\|"concept">`; `connection <from> <to> <relation> "<why>" --rival --discriminator`; `state C.. confirmed\|rejected` |
| F2 | `new hypothesis "<t>" --parent <front> --refuted-if ..`; `link <H> answers <Q>`; `link <a> rival <b>`; rival readings as sibling branches |
| F3 | `test <hyp> "<t>" --scope --why --outside --control --control-type --prediction --instrument` |
| F4 | `instrument <path> "<name>" --verifier "<cmd>"`; `test ... --script`; `run <T> --pid --log`; `jobs` |
| F5, F6 | `result <test> positive\|negative\|inconclusive\|failed "<note>" --meaning --n --control-ok`; `ach <E> <H> <value>` |
| F7 | `state <id> <state> "<reason>"`; `new decision`; `reading ".." --supports --rival --question --reason`; course correction: `step corrected` or `branch new --from B.. --step N` |
| Query | `search`, `tried`, `show`, `chain`, `questions`, `next`, `timeline`, `tree`, `trail`, `sheet` |

## F1 — Reading

```
Already done (tried): ids read
Own reading (before seeing interpretations): source · message · referents · confidence
Another reading (changes the meaning or the referent)
Discriminator: what would separate the readings
Bridge to the operation + remaining free choices
After the references: "I changed X because I saw Y"
Second reading of data extracted by a tool
Consumption inventory: element → the step that explains it
```

## F2 — Hypotheses

```
Hypotheses: H-nothing, H-mundane, H-adversarial, H-error, H-artefact, third parties'
Prior from the outside view: k of N attempts of the kind succeeded
Premises: premise | relevance 0-2 | support 0-2 | what would break it
ACH matrix (filled by row) + "easy to forge?" column
Status: alive | refuted (by which fact)
Probabilities (sum to 1, with "other", only among exclusive rivals)
Milestones that would change the conclusion
```

## F3 — Pre-assessment (goes into the `test` fields)

```
title:       the recipe in one line
scope:       the exact space that will be covered
outside:     what is left out
excludes:    which hypothesis the result excludes (in the summary)
results:     hit / weak signal / nothing → P|H, P|H-nothing, LR
prediction:  P(event) = 0.0x
control:     type (real data, double implementation, rate, sabotage) and measured power
criterion:   FPR, sensitivity, expected alarms = FPR × N
choices:     fixed beforehand (start, index, format, crop)
cost:        space ÷ measured rate
tried:       earlier runs of the same recipe, or "none"
premortem:   why it would end without a finding or with a false finding
```

## F4 — Execution

The script records the recipe, the script's hash, the instrument, N, rate, control, hits and log. Review by the
`reviewer`: declared space = executed space, control with power, shared instrument without a local copy, rate
measured in the right place. Without review, it does not count as coverage.

## F5 — Evaluation

```
Propositions: those of F2? yes/no
Best score vs maximum of N under noise
Control with the same freedom · variations
Discrepancies: item | explanation | independent evidence? → verdict
Acceptance criteria 1–7
Level: operation | source | activity | resolution
Conclusion: probability · confidence · verbal LR · change
```

## F6 — Verification (written by the verifier)

```
Received: data + criterion + K candidates (without knowing the suspect)
Reproduction: recipe followed step by step → result obtained
Verdict per candidate
Independent probability (sums to 1 among exclusive rivals)
Disagreements
```

## F7 — Revision

- Decision: options considered, chosen, rejected and why (`new decision`).
- Retraction: `state <id> retracted "<reason>"`; open `show <id>` and reassess each linked item.
- From-scratch review: a new estimate before seeing the old one, the old one, the difference, surprises reread.
- Repeated negative: an IS / IS NOT table. "If X is the cause, why does it show up here and not there?"
- Change of leading hypothesis: the old one becomes a paused or dead branch with the reason, never erased.
