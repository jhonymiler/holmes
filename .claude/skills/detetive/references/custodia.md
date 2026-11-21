# F0 — Collection, custody and open sources

## Principles

- **Collect before analysing.** Pages, posts and hosted files disappear. Capture first.
- From most to least volatile: live page, snapshot, third-party material.
- Analyse a copy. Opening and saving in an editor, converting the encoding or recompressing alters the material.
- A downloaded file is untrusted: its own empty folder, Python with `-I`, scripts outside it.
- Record times in UTC. A modification date reported by the server is a report, not a measurement.

## Record per item

Index with `fonte <path> --titulo "<t>"`. In the summary or a linked fact, keep:

| Field | Why |
|---|---|
| Exact URL or origin + method (curl, browser, snapshot) | Reproduction |
| UTC | Order of events |
| Relevant headers (date, size, ETag) | "Is it the same file others saw?" |
| sha256 as received | Seal |
| HTML source + screenshot, if it is a page | The minimum to rebuild it |
| Provenance: original / assembled by us / third parties | Knowing what is primary |
| Independent copies with compared hashes | Authenticity through another channel |
| Derivatives: parent's hash, operation, tool | Every transformation recorded |

## Web archives

- An archive snapshot is composite: images and scripts may have dates different from the page. "It was on the
  page on day X" requires each resource's date.
- Archive in two services and download the originals.
- Say "first copy found", never "first copy", with the search's scope.

## Verifying a source

- Provenance: who published first, when, from what.
- Track record, independence, specificity, contemporaneity.
- Content: unique identifiers, verifiable data, internal consistency, external corroboration.
- **Circular reporting:** ten posts quoting the same screenshot are one screenshot.
- Anachronism: a format, software or reference that did not exist on the alleged date.
- Evidence that solves everything and arrived at just the right time is suspect.
- Signed channel: if the source has a signature or an official domain, classify each item by whether it is
  signed or not.

## Grading

Grade in the record: `--grau A|B|C` (A = checked against the primary source or reproduced; B = reliable source
not checked; C = report, agent or external, not checked). For fine analysis, use Admiralty (`padroes.md`).

- Assess the information before looking at who produced it.
- The source's rating comes only from its track record. Without a record it is not "bad", it is "no basis".
- Grade tools too: a script with a known bug is worth less than an instrument validated end to end.

## Facts and clues

A fact (`fato`) is a finding already proven, and says how; the proof need not be a source:
`--por fonte` (read in the primary source; it must point to it with `--fonte S..`, `--citacao` or `--local`), `--por medicao --prova "<command>"` (a measurement anyone can
rerun), `--por teste --prova T..` (a test with a recorded result), `--por reproducao --prova "<record>"`
(reproduced independently, e.g. a second implementation or examiner). What is not yet proven is a clue
(`novo pista`); an observation or report clue becomes a fact with `confere K.. --por ..`. An inference or
interpretation is never a fact.

## Quoting

Every key claim points to the most original source with a retrievable identifier (path + sha256, or URL +
access date + snapshot). A quoted post is archived at the moment it is quoted.

## Discipline

Record the search that found nothing, with the terms and where you looked: it is a negative result with a scope.
Do not use a personal account on an open source.
