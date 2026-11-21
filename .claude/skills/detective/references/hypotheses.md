# F2 — Hypotheses

## Generating

- Real rivals, not a quota. Consider, when plausible: **H-nothing** (chance, transcription error),
  **H-mundane** (index 0/1, encoding, time zone, unit, off-by-one), **H-adversarial** (deception), **H-error**
  (the producer made a mistake) and, for an "intentional detail", **H-artefact** (accident). A hypothesis
  invented to fill a number is noise in the matrix.
- A question still without a plausible explanation stays open as a `question` (a gap), with no forced hypothesis.
- Include hypotheses from third parties and earlier sessions, with credit.
- Generate before diving into detail. Generating and evaluating are separate steps.
- Record the test each hypothesis suggests, not only the favourite's.
- Record: `new hypothesis "<t>" --parent <front>`; rivals linked with `link <a> rival <b>` (`contradicts` is for two facts or clues that cannot both hold). Competing readings
  of the same clue also become sibling branches (`branch new ... --from <same point>`), so the path of each one
  stays visible.

## Prior from the outside view

Before the details: "of N attempts of this kind, how many succeeded?" That is the prior. With many refuted
lines, the prior that "the next one succeeds" is low.

## Premises

For each premise the line requires:
- relevance 0–2 (2 = the line falls without it) × support 0–2. Priority: high relevance, low support.
- "What would we see if it were true, and why don't we see it?"
- Imagine a perfect source said it is wrong. Build the scenario.
- P(A and B) = P(A) × P(B | A). It only becomes a simple product if the premises are independent; premises from
  the same source or the same reasoning tend to move together. Five independent ones at 80% give 33%.
- Review the premises at the start and before concluding.

Premises of identity ("it is the same file"), time and completeness ("it is the whole log") break most often.

## ACH — as a record, not as an oracle

ACH (analysis of competing hypotheses) does not improve accuracy by itself; it serves to find distinguishing
evidence and to keep the reasoning auditable.

1. Rows = evidence, premises and absences. Columns = hypotheses.
2. Fill by row: "if H were true, how likely would it be to see this?" — CC/C (consistent), N (neutral),
   I/II (inconsistent), as in `ach <E> <H> CC|C|N|I|II`. A don't-know cell is left unrecorded ("?" is not
   accepted).
3. A row that is C in every column does not distinguish: it leaves the ranking but stays recorded.
4. Extra column: how easy would it be to forge the item?
5. Read by column. Rank by inconsistencies. Only the refuted one leaves, with the I documented.
6. If you disagree with the matrix, a row is missing. Add it; do not override silently.
7. Convert into probabilities. They sum to 1 (with "other") only if the hypotheses are mutually exclusive;
   readings that can be true together (narrative and operational function) have their own probabilities.
8. Decisive judgment: 2 or 3 independent agents estimate without seeing each other; use the average.
9. Sensitivity: if the decisive I were wrong, would the conclusion change? Check it by another route.
10. Write beforehand what, if it appears, changes the conclusion.

## Deception

Suspect it when: the analysis depends on a single item; the key information arrived at just the right time;
accepting it forces a central premise to change; whoever produced the material sees what you do.

- Motive, channels, risk and cost of the deception.
- Has there been deception from this source before?
- Can the source be manipulated? Direct access or second-hand?
- Was the whole chain checked, including transcriptions? Is there confirmation through a channel the producer
  does not control?

Deception stays a live hypothesis, never a pocket explanation.

## Strong inference and premortem

- Every test answers: which hypothesis does it exclude? A theory that explains any result explains none.
- New result → 2 or 3 explanations → a control that separates them.
- **Premortem:** before running, write "it ended without a finding, or the finding was false. Why?" The answers
  become sanity tests.
- An old consensus calls for a devil's advocate (agent `skeptic`). Then check the base rate.
- An ad hoc patch multiplies probabilities: each one makes the hypothesis less likely.

## Before collecting more

Classify what you expect to obtain: more detail of the same (only raises confidence), a new variable (rarely
changes anything), a new value of a critical variable or a new model (the only ones that change accuracy).

## Open

Two hypotheses with comparable inconsistencies: "open, and here is the test that would decide", with
probabilities. Picking the less ugly one is the most common confident error.
