# The team

Definitions in `.claude/agents/*.md`.

## Budget

- Specialists on Sonnet or Haiku, medium effort at most. A well-defined scope makes up for a smaller model.
- Every subagent loads the whole `CLAUDE.md` and `.claude/rules/`: keep them short.
- A subagent does not launch subagents.

## Who does what

| Agent | Model | Phase | Delivers | Does not |
|---|---|---|---|---|
| `arquivista` | haiku | F0 | Isolated collection, hashes, indexed sources | Interpret |
| `pesquisador` | sonnet | F1, F2 | External sources read, excerpts with locator and grade | Draw conclusions about the case |
| `analista` | sonnet | F1–F3 | Reading, hypotheses, pre-assessment | Search code |
| `engenheiro` | sonnet | F4 | Script with a control, recorded run | Judge its own result |
| `revisor` | sonnet | F4 | Review of the code and the coverage | Edit the reviewed code |
| `verificador` | sonnet | F6 | Blind verification and reproduction | Read the record or know the suspect |
| `ceticismo` | sonnet | F5, F7 | Attack on a negative or a connection before it becomes final | Record |
| `interprete` | opus | F1, overall reading | Alternative readings, concepts that link clues, candidate connections | Run tests; confirm a relation |

The integrator is the coordinator: only they confront the deliveries with the map, decide what to record and
rewrite the reading. The interpreter and the sceptic are only worth calling for a decisive judgment, not at
every observation.

Cross-review: `revisor` reviews `engenheiro`; `verificador` judges candidates; the coordinator checks every
report against the source before recording; the user reviews the coordinator.

## When to delegate

- **Delegate:** independent fronts of real size (launched together); reading larger than one context;
  deliberate independence (reviewer, verifier, sceptic); cheap, checkable work.
- **Do not delegate:** what fits in a few calls; a dependent chain that fits in one context; verifying your own
  work.

## Briefing (the subagent does not inherit the conversation)

Always include:
1. The case and the request to run `python3 -I holmes/holmes.py mapa` before acting.
2. The working mode (LEITURA, CIRURGIA or VARREDURA) and the maximum cost.
3. The input ids (`ver <id>`) and the expected output.
4. What is already closed. Before saying "new" or "already covered": `ja "<term>"`, citing ids.
5. A negative refutes only the tested recipe; declare what was left out.
6. Do not declare a block for lack of an external source; propose the next step.
7. Return the relations found as candidates (from, to, relation, why, rival, discriminator), for the
   coordinator to assess and record with `conexao`; never as a direct `liga`.
8. Delivery format: result, real or synthetic, what was checked against the source, what was not.
9. The active branch (`ficha`), so that the work comes back as steps of the right line.

For `verificador`: never the verdict nor the favourite hypothesis.
For `ceticismo`: the claim, the script, the log and the record, without a defence of it.

## Afterwards

- Do not redo the agent's work. Check the report against the source (skill `conferir-relatorio`).
- A result from an agent or an external AI enters with `--origem agente|externo --grau C` until checked.
- A fact from outside the repository that the agent asserts enters as an external report (grade C, draft), not
  as a case premise, until a source has been read.

## Secrecy and security

- A secret found (credential, key, personal data): save it to a local case file and tell only the user. Never
  publish it or send it to third parties.
- A downloaded file is untrusted: its own empty folder, Python with `-I`, scripts outside it.
- Respect the machine's CPU and memory limits declared in `CLAUDE.md`.
