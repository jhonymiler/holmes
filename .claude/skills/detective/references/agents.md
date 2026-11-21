# The team

Definitions in `.claude/agents/*.md`.

## Budget

- Specialists on Sonnet or Haiku, medium effort at most, except `interpreter` (opus, high), called only for
  decisive readings. A well-defined scope makes up for a smaller model.
- Every subagent loads the whole `CLAUDE.md` and `.claude/rules/`: keep them short.
- A subagent does not launch subagents.

## Who does what

| Agent | Model | Phase | Delivers | Does not |
|---|---|---|---|---|
| `archivist` | haiku | F0 | Isolated collection, hashes, indexed sources | Interpret |
| `researcher` | sonnet | F1, F2 | External sources read, excerpts with locator and grade | Draw conclusions about the case |
| `analyst` | sonnet | F1–F3 | Reading, hypotheses, pre-assessment | Search code |
| `engineer` | sonnet | F4 | Script with a control, recorded run | Judge its own result |
| `reviewer` | sonnet | F4 | Review of the code and the coverage | Edit the reviewed code |
| `verifier` | sonnet | F6 | Blind verification and reproduction | Read the record or know the suspect |
| `skeptic` | sonnet | F5, F7 | Attack on a negative or a connection before it becomes final | Record |
| `interpreter` | opus | F1, overall reading | Alternative readings, concepts that link clues, candidate connections | Run tests; confirm a relation |

The integrator is the coordinator: only they confront the deliveries with the map, decide what to record and
rewrite the reading. The interpreter and the skeptic are only worth calling for a decisive judgment, not at
every observation.

Cross-review: `reviewer` reviews `engineer`; `verifier` judges candidates; the coordinator checks every
report against the source before recording; the user reviews the coordinator.

## When to delegate

- **Delegate:** independent fronts of real size (launched together); reading larger than one context;
  deliberate independence (reviewer, verifier, skeptic); cheap, checkable work.
- **Do not delegate:** what fits in a few calls; a dependent chain that fits in one context; verifying your own
  work.

## Briefing (the subagent does not inherit the conversation)

Always include:
1. The case and the request to run `python3 -I holmes/holmes.py map` before acting.
2. The working mode (READING, SURGERY or SWEEP) and the maximum cost.
3. The input ids (`show <id>`) and the expected output.
4. What is already closed. Before saying "new" or "already covered": `tried "<term>"`, citing ids.
5. A negative refutes only the tested recipe; declare what was left out.
6. Do not declare a block for lack of an external source; propose the next step.
7. Return the relations found as candidates (from, to, relation, why, rival, discriminator), for the
   coordinator to assess and record with `connection`; never as a direct `link`.
8. Delivery format: result, real or synthetic, what was checked against the source, what was not.
9. The active branch (`sheet`), so that the work comes back as steps of the right line.

For `verifier`: never the verdict nor the favourite hypothesis.
For `skeptic`: the claim, the script, the log and the record, without a defence of it.

## Afterwards

- Do not redo the agent's work. Check the report against the source (skill `check-report`).
- A result from an agent or an external AI enters with `--origin agent|external --grade C`, as a clue, until proven.
- A fact from outside the repository that the agent asserts enters as a clue (`clue`, grade C), not as a
  fact nor a case premise, until it is proven; proving it (`prove`) raises it to grade A.

## Secrecy and security

- A secret found (credential, key, personal data): save it to a local case file and tell only the user. Never
  publish it or send it to third parties.
- A downloaded file is untrusted: its own empty folder, Python with `-I`, scripts outside it.
- Respect the machine's CPU and memory limits declared in `CLAUDE.md`.
