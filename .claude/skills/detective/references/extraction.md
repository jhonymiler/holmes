# Investigative extraction: from material to understanding

A conceptual sequence, not an obligation to create one object per stage:
**material → observation → clue → connection → question → hypothesis → evidence → synthesis.**
Stop where the information stops. An observation without a clue is a valid record; a source with nothing
relevant is a result ("nothing extracted from S12, read in full").

## A. Preserve and locate
`source <file>` (sha, provenance). Originals are read-only. Every observation points to where it is (`location`,
`chunk`) and how it was obtained (`method`, `limits`). The interpretation never replaces the original.

## B. Break down into observations
Units verifiable one by one, in the material's own vocabulary:

| Material | Look at |
|---|---|
| Text | terms, names, dates, references, negations, what changed relative to a version or to the quoted original, structure |
| Image | objects, positions, colours, shapes, symmetry, differences, groupings |
| Numbers | values, distribution, sequences, intervals, repetitions |
| Run output | beyond success or failure: format, content, what came out different from expected |
| Event | who, what, when (`new entity --class event` + `attribute <N> when <date>`), alleged or demonstrated cause |

Observation: "cell (3,7) has RGB FEFEFE". Not an observation: "the author marked the cell". That is an
interpretation.

## C. Clue: why look at this
Anomaly, repetition, contrast, symmetry or asymmetry, a difference between versions, a correspondence, a
reference, absence where presence was expected, something contradicting a prediction, something the current
reading does not explain. Do not presume intent: an anomaly may be an error, a processing artefact, noise or
normality. Do not discard the ordinary: it stays searchable and may become a clue when something else appears.

## D. Connections
`connections <id>` or `connections "<the concept in words>"` before recording something as new. If two clues seem to
point to the same idea without sharing a word, name the idea and record it as an entity with aliases
(`new entity "complementarity" --class concept --alias "two halves,yin-yang"`): from then on it links
whatever arrives. For each candidate, write the relation, the rival (chance, generic theme, the same source
repeated) and the discriminator. Record only the promising one (`connection`) and the rejection that would prevent
rediscovery. Three agents repeating the same reading are not three pieces of evidence.

## E. Questions
What remains unexplained? What information is missing? Do two clues point to the same phenomenon? Does the
current question start from a false premise? A question without a hypothesis is legitimate: it stays open and
shows up as a gap.

## F. Hypotheses
For the questions that admit an explanation: what it explains, what motivated it, which premises it depends on,
what it predicts, what would weaken it, what the rivals are. Include chance, error, artefact and deception when
they are plausible rivals, not to fill a number. An exploratory one (without `--refuted-if`) may be explored;
only an operational one gets a confirmatory test.

## G. Integrate into the plan
Does the information reinforce a question, reveal a dependency, open or weaken a hypothesis, link fronts, close
a gap or change a priority? A new front only for a relevant, independent problem (max. 5 active). A new line of
reasoning is a branch born from the point where it arose (`branch new ... --from <id> --why`).

## H. Update the understanding
What changed in the overall understanding? If nothing, the reading stays. If it changed: `reading "..."
--supports .. --rival .. --question .. --reason "<what changed and why>"`.

## Recording at once: the contract
For a source with many units, write the contract's JSON (`MODEL.md`, "Extraction contract"), run
`holmes.py extract f.json` to see the plan and `--apply` to record. Minimal example:

```json
{"source": "S12",
 "observations": [{"id": "o1", "text": "Footer with a yin-yang in ink", "location": "sheet 2", "method": "visual"}],
 "clues": [{"obs": "o1", "about": "Q4", "why": "the sheet's only drawing"}],
 "connections": [{"from": "o1", "to": "E3", "relation": "about", "why": "two halves ↔ yin-yang",
                  "rival": "common decorative symbol", "discriminator": "is it where the parts meet?"}]}
```

When not to record: what only repeats what is already in the corpus and weighs on no question. It stays searchable.
