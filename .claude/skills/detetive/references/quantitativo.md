# F3/F5 — Quantitative assessment

Without published data, simulate for the case. An order of magnitude with a declared basis is enough. With no
basis at all, say no assessment is possible. Do every calculation in code, not in your head.

## Likelihood ratio (LR)

LR = P(E | H) ÷ P(E | most reasonable alternative). The LR multiplies **odds**, not probability:
odds = p ÷ (1 − p); posterior odds = prior odds × LR; posterior p = odds ÷ (1 + odds).
E.g.: p = 0.2 → odds 0.25; LR = 8 → odds 2 → p ≈ 0.67 (not 0.2 × 8).
- Propositions fixed before the result.
- LRs only multiply if the pieces of evidence are conditionally independent. Three agents repeating the same
  reading, or two clues from the same source, are one piece of evidence, not three.
- The LR says nothing about hypotheses outside the pair; both may be false.
- Do not transpose: "1 in 10⁹ of being chance" is not "1 in 10⁹ of being wrong". In a search of N candidates,
  each one's prior is close to 1/N.

### LR of a coincidence
1. Write E exactly as observed.
2. P(E | H): close to 1 if H predicts E; low if it merely allows it.
3. P(E | H-nothing): simulate with the same procedure that produced E, including every choice.
4. Translate onto the verbal scale in `padroes.md`.

Example: 8 hex digits matching by chance have P = 2⁻³² per attempt. After 10⁶ attempts, LR ≈ 4 × 10³
(strong). After 10⁹, LR ≈ 4 (weak). Same hit, different value.

## Error rate of the acceptance criterion

- **FPR** = P(accepts | wrong). **Sensitivity** = P(accepts | right). Measure both on cases with a known
  answer, similar to the real case.
- Report the 95% upper bound: 0 errors in n → about 3/n.
- **Expected false alarms = FPR × N.** If ≥ 1, the criterion is only a filter and needs an independent second
  stage.
- Do not infer FPR from real searches ("it never gave a false positive"): there the truth is unknown.
- Without measured sensitivity, a negative does not close the recipe.

## Degrees of freedom

- Add up log₂ of each free choice: order, start, format, filter, tolerated errors.
- **Evidence budget:** bits of the result minus log₂(attempts, including discarded ones and those from earlier
  sessions). A margin ≤ 0 is not evidence.
- **Collection choices** (text version, crop, index 0/1) count too. Declared beforehand, they are legitimate;
  chosen afterwards, they are fitting.
- **Garden of forking paths:** a single analysis already inflates the false positive if the details were decided
  while looking at the data. Fix them beforehand, or list them and correct.

## Champion of a large search

A large search always finds a very similar false one. Compare the best score with the distribution of the
maximum of N samples under noise (or p_global ≈ N·p). A candidate coming from the top requires a second
verification before becoming a fact.

## Null and positive

Null = shuffles of the material itself. Positive = synthetics of the supposed type, same size. Finding = outside
the null and inside the positive. Correct for the number of places you looked.

## Correlation

Require the 2×2 table with the 4 counts. Before claiming a relation between A and B, consider: A→B, B→A, C
causes both, coincidence, the data is wrong.

## Calibration

Every prediction (`--previsao`) carries a numerical probability. When recording `resultado`, compare with the
prediction. Track the Brier score (0 perfect; 50/50 gives 0.25). Without that feedback, calibration is self-esteem.

## Time

Time = space ÷ (measured rate × parallelism), with the rate measured on the machine, in the script and with the
real options. If it comes out in centuries, the hypothesis is wrong: go back to the structure. Measure before
optimizing.
