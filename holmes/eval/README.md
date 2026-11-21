# Evaluating investigative capability

Two levels, which are not to be confused:

| Level | What it measures | Runs without a model? | Command |
|---|---|---|---|
| Mechanism | whether relation discovery puts the right pair among the top 5 candidates | yes | `python3 -I holmes/eval/evaluate.py recall [answer key]` |
| Investigation | whether an agent, using holmes, reaches the solution without fabricating relations | no: needs a real session | protocol below + `evaluate.py score <case.db> [answer key]` |

The answer key defaults to `holmes/eval/watchmaker.json`. The old subcommand names (`recuperacao`, `pontua`) are
still accepted.

## Synthetic case `watchmaker.json`

30 clues in 3 waves (text, object, number, document, symbol), 9 true links (2 literal and 7 by concept only), 4
traps (the same word without a relation) and 13 distractors. The solution is known and kept outside the case. The
answer key's keys: `case`, `objective`, `solution`, `solution_words`, `clues`, `links`, `traps`,
`interpreter_concepts`.

Measured on 2026-11-20 (top 5):

| Mode | Links | Non-literal | Traps in the list |
|---|---|---|---|
| `search` (what existed) | 3/9 | 1/7 | 3/4 |
| `connections` | 3/9 | 1/7 | 2/4 |
| `connections` + the interpreter's concepts | 9/9 | 7/7 | 2/4 |

> [!NOTE]
> The third row is a ceiling, not performance: the concepts came from the answer key.

Reading: the mechanism alone does not discover a relation without a shared word. The gain comes from the abstract
concept recorded as an entity with aliases (what the agent or the `interpreter` proposes) and reused on every
following clue. Traps in the list are expected: a candidate is not a relation; what counts is how many the agent
confirms (measured by `score`).

## Protocol for a round with a model

> [!WARNING]
> This protocol has not been run yet.

1. Clean root: copy the kit into a new folder, `python3 -I holmes/holmes.py init watchmaker "<objective from the
   json>"`.
2. For each wave, give the agent only that wave's clues, as a file registered with `source`. Never the solution,
   the links or the concepts.
3. Fixed request: "Investigate with holmes until you propose the combination. Record what you observe, the
   questions, the hypotheses and the relations." Compact the conversation between waves 2 and 3 (`/compact`) to
   measure resumption.
4. At the end: `python3 -I holmes/eval/evaluate.py score cases/watchmaker/case.db`.
5. Run two variants with the same model: the current kit and the previous kit (without `connections`, `question`,
   `extract`), 3 times each. Compare the medians.

Rubric (what `score` returns, and what is good):

| Metric (`score` key) | Good |
|---|---|
| true links in the graph (`true_links_in_graph`) | high |
| traps accepted into the graph (`traps_accepted_in_graph (false positive)`) | 0 (each one is a false association) |
| traps explicitly rejected (`traps_rejected_explicitly`) | high (avoids rediscovery) |
| interpretations recorded as observations (`interpretations_as_observation (error)`) | 0 |
| suggested connections left without a decision (`suggested_connections_without_decision`) | low at the end |
| the final reading contains the solution (`final_reading_contains_solution`) | yes |
| tests spent (`tests_spent`) | low, for the same result |
| human intervention | count by hand: how many times redirection was needed |

`score` also reports `clues_recorded`, `questions`, `hypotheses`, `hypotheses_without_refuted_if` and
`reading_revisions`.

Open-ended reasoning (the quality of the rival hypotheses, of the chosen discriminator) is not automatic: read the
winning hypothesis' `chain` and judge it with a reviewer who has not seen the solution.
