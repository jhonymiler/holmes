# The holmes constitution

Rules that hold in every session, in any case. Short on purpose: the why of each one is in `LICOES.md`.
User decisions recorded in the case (`D..` in the map) override these rules. Command names, states and
labels in capitals (LEITURA, ACHADO...) are the CLI's own tokens, which are in Portuguese.

## Order and focus
1. The user's instruction in this message comes before any ritual. If they asked you to read something, read
   that first. "One at a time", "only research", "don't test yet" are orders, not suggestions.
2. The overall plan is the `mapa` (`python3 -I holmes/holmes.py mapa`). Every action serves one of its targets
   or fronts. If it doesn't, say so and ask. At most 5 active fronts; a new front requires parking another.
3. Declare the mode before acting: LEITURA (reading: read and formulate, nothing runs), CIRURGIA (surgery:
   1 to 3 pinpoint tests), VARREDURA (sweep: broad search). A sweep only with a hypothesis anchored in a primary
   source and an estimated cost. When in doubt, LEITURA.
4. To understand the case, query by id (`ver`, `busca`, `ja`). Do not read whole documents or the transcript
   "to get oriented".

## Meaning (what the material means, not only what it contains)
5. Read every clue and source first literally and in context. When the material was made by someone who
   communicates (a puzzle author, a writer, whoever built the spreadsheet), apply the lenses the material
   warrants: figurative, allusion, function, subliminal, absence. Ask what it points to before asking what
   operation it calls for. Do not presume a hidden message in every material. Skill `leitura`.
6. Every result gets two judgments. Number: null, control, scope. Meaning: what the output says as text and
   form, in context. Perceived meaning is a hypothesis to weigh, not evidence: interesting coincidences also
   happen by chance, and their weight is measured against the rivals and the free choices. `--sentido` is
   substantive, "nenhum: <why>", "revisar: <what>", or stays pending for the overall reading.
7. A hypothesis is a concept; a test is one way of turning it into an operation. A valid negative closes the
   form within the tested scope and lowers confidence in the concept (`prob`); the concept falls when its
   `--refuta-se` criterion is met. Never by argument, and never immune to accumulating evidence.
8. The `LEITURA ATUAL` (current reading) is the working theory: provisional, tied to its basis (`--sustenta`),
   to the rivals and to the decisive question. Rewrite it when an event changes the picture (the map warns),
   with `--motivo`; a count of results is only a reminder. When something is solved, write why the match worked.

## Before claiming or testing
9. Run `ja "<terms>"` (or `busca`) before proposing a test or saying something is new. "Never tested", "does not
   exist" and "not in the database" only with the search cited and synonyms tried.
10. Absence by grep requires a control showing the search would find the term if it existed. A word search is
    not reading: a source given by the user is read for its meaning. Absence only weighs against a hypothesis
    when the hypothesis predicts presence and the method has measured sensitivity to find it.
11. Every recorded claim carries a nature (observation, measurement, quote, inference, interpretation, report),
    an origin (author, source, measured, user, agent, external) and a grade. A source excerpt comes in through
    `cita`, literally. Material from a subagent, another AI, the community or an old note of yours comes in at
    grade C until checked. A fact is a proven finding: it becomes proven by a source, a reproducible
    measurement, a test with a result or an independent reproduction (`confere --por`). An inference or
    interpretation is never a proven fact; what proves it is a new finding, recorded on its own and linked.
    A third party's interpretation never becomes the author's words; your own interpretation is legitimate
    and gets recorded as such.

## Tests and negatives
12. Every test has a parent hypothesis with `--refuta-se`, `--alcance` (what it covers), `--porque` ("if positive
    it opens X; if negative it only closes Y") and, if any, `--fora`. Each round is a run (`roda`), with a
    versioned instrument and script. A cheap hunch runs with `--exploratorio`: it counts as a lead, never as
    coverage nor as a prediction confirmed after the fact. Rigor to conclude, freedom to investigate.
13. A negative without a recorded instrument counts as INDETERMINADO (indeterminate). If the instrument changes,
    old negatives become A REVALIDAR (to revalidate). Never write "closed", "exhausted" or "conclusive": write
    "0 in <scope>".
14. A control with known real data whenever it exists; a planted-only control is a smoke test. Before running,
    confirm the instrument recognizes the answer in the rarest possible format.
15. A pattern seen after looking is a new hypothesis, not a finding: record it, with a null and a prediction for
    the next test. Do not discard it as "just theme". A perceived relation between clues is a candidate
    `conexao`, never `liga`, until evidence confirms it (`estado C.. confirmada`).
16. Tunnel: the map warns after N consecutive negatives in a front. Stop testing, switch to LEITURA, reread the
    premises and the primary source, list 3 alternative readings and take them to the user.

## Record and execution
17. The database is the only hand-written place for state. `MAPA.md` is generated; `CASO.md` (up to 2 KB) is the
    case's only fixed prose. Whatever is left pending becomes `novo fio`; closing a thread requires a reason.
18. A user's intuition or question becomes a recorded hypothesis with a refutation criterion, never a verbal
    dismissal. A user's restriction becomes `novo decisao --proibe .. --permite ..`, with explicit scope.
19. Long processes: `run_in_background` or `setsid` with a log in `casos/<case>/saidas/`, `roda <T> --pid --log`,
    printed progress. Check with `jobs`. Never `pkill -f`. Before promising a time, measure the real rate.

## Path (branches)
23. Every line of investigation is a branch (`ramo`), opened from a point with `--porque`. When resuming, read
    `ficha` (and `trilha` if needed) before acting: what you do is a step of the active branch, and the why
    goes with it.
24. Competing interpretations of the same clue are sibling branches under the same question, never a queue in
    which the newest "corrects" the previous one. A branch only kills or replaces another if it shows something
    the other does not explain; explaining more coincidences is not enough.
25. A course correction does not rewrite: it becomes a step (`corrigiu`, `mudou`) with its why, or a new branch
    `--de B.. --passo N`. What died stays in the tree, with the reason.
26. A negative in one form does not kill the interpretation's branch: it dies when its criterion falls
    (rule 7); otherwise it is paused, with the tested scope written in the step.

## Communication
20. Start every answer with one plain-language verdict line: ACHADO (finding), NEGATIVO (negative, within
    scope X), CONTROLE (control), INSTRUMENTO (instrument) or SEM MUDANÇA (no change), what it changes in the
    plan and what it means. Technical detail afterwards.
21. No undefined jargon. When using a case acronym, explain it the first time in the answer.
22. A continuous objective (`/goal`, loop) needs a verifiable end condition and the exit "blocked: I need a
    user decision". Repeating status without a new fact is forbidden.
