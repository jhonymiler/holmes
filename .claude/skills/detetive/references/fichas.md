# Record templates per phase

State and data go to the record (`python3 -I holmes/holmes.py`). Long prose goes into a `.md` indexed with
`fonte`. A record sheet (ficha) is the node's summary (`--resumo`), or a `.md` linked to it. Not to be confused
with the `ficha` command, the one-page view of where the case stands.

## Commands per phase

| Phase | Commands |
|---|---|
| Open | `init <case> "<objective>"`, `usa <case>`, `novo alvo`, `novo frente`, `ramo novo "TRUNK..." --de O1 --porque ..` |
| Resume | `mapa`, `ficha`, `trilha` if needed, then `ver <id>` of whatever is active |
| F0 | `fonte <path> --titulo "<t>"` |
| F1 | `cita <chunk> "<t>"`, `novo fato "<t>" --por .. --natureza --origem --fonte --grau` (proven) or `novo pista "<t>"` (not yet); `confere K.. ".." --por ..`; `novo fio`; `novo questao`; many units: `extrai f.json [--aplica]` |
| Relations | `conexoes <id\|"concept">`; `conexao <from> <to> <relation> "<why>" --rival --discriminador`; `estado C.. confirmada\|rejeitada` |
| F2 | `novo hipotese "<t>" --pai <front> --refuta-se ..`; `liga <H> responde <Q>`; `liga <a> rival <b>`; rival readings as sibling branches |
| F3 | `teste <hyp> "<t>" --alcance --porque --fora --controle --controle-tipo --previsao --instrumento` |
| F4 | `instrumento <path> "<name>" --verificador "<cmd>"`; `teste ... --script`; `roda <T> --pid --log`; `jobs` |
| F5, F6 | `resultado <test> positivo\|negativo\|inconclusivo\|falhou "<note>" --sentido --n --controle-ok`; `ach <E> <H> <value>` |
| F7 | `estado <id> <state> "<reason>"`; `novo decisao`; `leitura ".." --sustenta --rival --questao --motivo`; course correction: `passo corrigiu` or `ramo novo --de B.. --passo N` |
| Query | `busca`, `ja`, `ver`, `cadeia`, `questoes`, `proximo`, `cronologia`, `arvore`, `trilha`, `ficha` |

## F1 — Reading

```
Already done (ja): ids read
Own reading (before seeing interpretations): source · message · referents · confidence
Another reading (changes the meaning or the referent)
Discriminator: what would separate the readings
Bridge to the operation + remaining free choices
After the references: "I changed X because I saw Y"
Second reading of data extracted by a tool
Consumption inventory: element → the step that explains it
```

## F2 — Hypotheses

```
Hypotheses: H-nothing, H-mundane, H-adversarial, H-error, H-artefact, third parties'
Prior from the outside view: k of N attempts of the kind succeeded
Premises: premise | relevance 0-2 | support 0-2 | what would break it
ACH matrix (filled by row) + "easy to forge?" column
Status: alive | refuted (by which fact)
Probabilities (sum to 1, with "other", only among exclusive rivals)
Milestones that would change the conclusion
```

## F3 — Pre-assessment (goes into the `teste` fields)

```
titulo:      the recipe in one line
alcance:     the exact space that will be covered
fora:        what is left out
excludes:    which hypothesis the result excludes (in the summary)
results:     hit / weak signal / nothing → P|H, P|H-nothing, LR
previsao:    P(event) = 0.0x
controle:    type (real data, double implementation, rate, sabotage) and measured power
criterion:   FPR, sensitivity, expected alarms = FPR × N
choices:     fixed beforehand (start, index, format, crop)
cost:        space ÷ measured rate
ja:          earlier runs of the same recipe, or "none"
premortem:   why it would end without a finding or with a false finding
```

## F4 — Execution

The script records the recipe, the script's hash, the instrument, N, rate, control, hits and log. Review by the
`revisor`: declared space = executed space, control with power, shared instrument without a local copy, rate
measured in the right place. Without review, it does not count as coverage.

## F5 — Evaluation

```
Propositions: those of F2? yes/no
Best score vs maximum of N under noise
Control with the same freedom · variations
Discrepancies: item | explanation | independent evidence? → verdict
Acceptance criteria 1–7
Level: operation | source | activity | resolution
Conclusion: probability · confidence · verbal LR · change
```

## F6 — Verification (written by the verifier)

```
Received: data + criterion + K candidates (without knowing the suspect)
Reproduction: recipe followed step by step → result obtained
Verdict per candidate
Independent probability (sums to 1 among exclusive rivals)
Disagreements
```

## F7 — Revision

- Decision: options considered, chosen, rejected and why (`novo decisao`).
- Retraction: `estado <id> retratado "<reason>"`; open `ver <id>` and reassess each linked item.
- From-scratch review: a new estimate before seeing the old one, the old one, the difference, surprises reread.
- Repeated negative: an IS / IS NOT table. "If X is the cause, why does it show up here and not there?"
- Change of leading hypothesis: the old one becomes a paused or dead branch with the reason, never erased.
