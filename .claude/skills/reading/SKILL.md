---
name: reading
description: "Reading for meaning: interpret clues, sources and test outputs beyond the literal, in layers (literal, figurative, allusion, function, subliminal, absence), and read the results as a whole to understand what story the case tells and where we are in it. Use when reading a new clue or source, when recording a result, when the map asks for an overall reading (OVERALL READING), after repeated negatives, when turning an idea into a test, or when the user asks 'what does this mean?', 'where are we?', 'does it make sense?'. Triggers: meaning, interpret, metaphor, allusion, subliminal, narrative, story, symbolic, too literal, what the author meant, leitura, significado, sentido, interpretar, narrativa, o que o autor quis dizer."
---

# Reading for meaning

A case's material was made by someone who communicates: a puzzle author, whoever drafted a contract, whoever
built a spreadsheet. The information is almost never just the literal words or bytes: it points to other
things, through image, allusion, double meaning and omission. The costliest mistake of v1 was reading
everything as mechanics (a word as a password, a book as a list of terms, an output as a count) and only
seeing meaning when the user insisted. The opposite mistake costs too: finding a message where there is
coincidence. Not every material has a second meaning; the literal and contextual reading is always the base.

## The layers (literal and function always; the others are lenses, when the material and the question warrant)

| Layer | Question |
|---|---|
| Literal | What does the text or the output say, word for word? Read all of it, not the line that matched. |
| Figurative | Is it a metaphor, an allegory, an image? What would it stand for if it were not literal? |
| Allusion | Which work, scene, character, idea or event does it point to? Find the source and read the passage. |
| Function | What does it do in the case: instruct, identify, mark a stage, give a name, mislead? |
| Subliminal | Wordplay, homophony, hidden word (acrostic, initials), double meaning, a number that is an index, what was changed relative to the quoted original (the diff is often the message). |
| Absence | What should be there and is not? What did the author avoid saying? |

Record every reading that matters as a clue: `new clue "<reading>" --nature interpretation`, linked to
the clue (`link K.. about <clue>`). If the reading links two clues, it is a candidate `connection`; if it names a
concept that shows up in several, record it as an entity with aliases (detective skill, `references/extraction.md`, step D). Your
own reading is legitimate: do not demote it for being yours, nor promote it to the author's words. An
interpretation is never a fact: it is a clue, or a hypothesis if it explains something testable.

## Reading a test's output

1. Look at the output as text and form before counting: what word, what pattern, what number appeared? Does it
   echo something from the sources or from the CURRENT READING?
2. Then the number: null, control, scope.
3. `result <T> ... --meaning "<what this says in context>"` (or `"none: <why>"`, or `"revisit: <what>"`, or leave it pending for
   the overall reading). Perceived meaning is a hypothesis, not evidence: estimate how likely it would be to see
   something like it by chance, counting the free choices (detective skill, `references/quantitative.md`). Without that estimate it is
   neither chance nor finding: it is a lead, recorded and confronted with a rival.

## From concept to operation

Ask what references what, not what the verb is. Build the correspondence before operating:
character ↔ piece, relation ↔ relation, event ↔ transformation.

1. Write the concept (the hypothesis) and what would refute it (`--refuted-if`).
2. List ways of turning it into an operation from different families, not variations of one (2 or 3 usually
   suffice; it is a heuristic, not a quota).
3. Pick the one the source determines most. Count the free choices: each one is a degree of freedom.
4. A valid 0 closes that form and lowers confidence in the concept (`prob`). The concept falls when the
   refutation criterion is met; accumulating negatives do not leave it intact.

## Overall reading (when the map asks, or after a tunnel)

1. `show` the latest results: read their `meaning` together, not one by one.
2. Ask: taken together, what do they tell? Which reading does none of them contradict? What was surprising?
3. Where are we in the case's story? What does it predict as the next step?
4. List alternative readings of the whole, at least one outside the lens used so far.
5. If the picture changed: `holmes.py reading "<up to 800 characters>" --supports E.. --rival H.. --question Q..
   --reason "<what changed and why>"`. If it did not, say why and leave the reading as it is.

## Closing the why

When something is solved, record why the correspondence worked (the abstract relation between the clue and
the solution). That is what guides the next step; the recipe that worked rarely repeats unchanged.

## Traps

- **Literalness:** testing the clue's word as a password or bytes instead of asking what it means.
- **Source treated as a string:** sweeping a book for a keyword and calling it exhausted. Read the whole
  passage and summarize the concept it explains.
- **Discarding meaning by an uncomputed p:** without the estimate, the coincidence stays a lead, not noise.
- **Spurious connection:** two clues with a similar theme ("duality", "time") link almost anything. A relation
  counts when it predicts something the rival (generic theme, chance, same source) does not.
- **Story too coherent:** each extra link makes the story less likely, not more.
- **Single lens:** reading everything through the same work or theory. One of the 3 alternative readings comes
  from outside it.
- **Theme without a bridge:** free association turning into a test. The bridge between source and operation
  must be written down.
- **Reading promoted to finding:** without independent verification, a reading is a lead or a hypothesis.
- **Forgetting the object's role:** an object in the case has a role in the story (who it is), not just a value.

## Partners

For reading for meaning, a second reader helps: the `interpreter` agent (an independent reading, without seeing
yours) or another model through a briefing. What comes back enters at grade C until checked.
