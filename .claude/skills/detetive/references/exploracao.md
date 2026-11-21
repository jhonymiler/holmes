# Stuck case — exploration

When nobody is going to hand over the answer, waiting for an external clue or repeating variations of the last
recipe is the most expensive way of finding nothing.

## Principle

The gates protect claims, not attempts. Trying is cheap; declaring coverage, a closed line or a finding is
what requires F3, a control and review.

## Two regimes

| | Exploration | Coverage |
|---|---|---|
| Mode | LEITURA or CIRURGIA | CIRURGIA or VARREDURA |
| May | Test a hunch; a 1% hypothesis; invert a central premise; read from a new angle | What F3 declares |
| Cost | ≤ 10 min of machine time or 1 h of reading per attempt | What F3 estimates |
| Record | `teste ... --exploratorio` + `resultado`, real scope ("1 attempt, 10 candidates") | Full `teste` + review |
| Counts as | A lead. Never coverage | Coverage |
| Promotion | An idea that shrinks the space or predicts new data moves up to F3 | — |

When in doubt, explore. An exploration negative closes nothing.

## Rules

- The absence of any statement by whoever produced the material only weighs against a hypothesis that predicted
  that statement; without that prediction, it does not weigh.
- Do not declare a block for lack of an external source. Propose the next step with what exists.
- An exploratory negative closes nothing. A valid negative closes the recipe within its scope and lowers
  confidence in the theme, without killing it. Say what was left out (`--fora`).
- Keep loose ends visible (`novo fio`) and linked (`liga`), even without evidence. Revisit the map's threads
  before choosing the next test.
- Solved one part: record why the answer worked and use it as a guide for the pending ones.
- Show the reasoning: what caught your eye, what connections, why they are promising.
- Open each exploration as a branch (`ramo novo ... --porque`) so that a dead end stays visible and is not
  walked again.

## Creativity prompts (stuck case; heuristics, not quotas)

1. **Leave the canon:** generate hypotheses that do not come from the record, third parties or an earlier
   session. List the inherited premises and invert one at a time.
2. **Change the lens:** treat the material as something else (text as data, data as text, the hint as noise,
   the statement as wrong). One cheap attempt per lens before discarding.
3. **Cross axes:** combine measured facts from different fronts. The promising space usually lies in the
   crossings treated as independent.
4. **Look for the question:** after a series of failed recipes, ask which question is being answered without
   noticing, before widening the space.
5. **Accept the hunch:** test first, justify afterwards. Do not discard as "already tried" without reading
   exactly what was tried (`ja`).

## Limits that do not change

- Security: Python with `-I` on downloaded material; nothing sensitive leaves the machine.
- Exploration does not change the state of a closed line nor delete a record.
- An apparent hit goes through a control and a blind `verificador` before becoming a finding.

## Anti-paralysis

If the answer to "what should we test now?" is "nothing, F3 is missing" or "nothing, source X is missing", it
is wrong. Pick the cheapest idea that differs from those already done and run it as exploration. Or link loose
threads, reread the primary source, research an external reference. Stop only for real cost, not ceremony.
