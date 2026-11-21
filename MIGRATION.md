# Migrating from the Portuguese CLI (holmes 2.0 before the English conversion)

holmes used to speak Portuguese: commands, options, states, stored values, file names and output. It now speaks
English everywhere. **Old names keep working**: every old command and option is accepted as an alias, old stored
values are translated, and an existing case database is migrated in place the first time it is opened (back it
up first; the migration is one-way). This table is the complete mapping.

## Ids

Node id prefixes do not change, so every id already written in notes and steps stays valid:
`O` objective · `A` target · `F` front · `H` hypothesis · `R` premise · `T` test · `X` run · `E` fact · `K` clue ·
`N` entity · `D` decision · `P` thread (pending) · `S` source · `I` instrument · `L` reading · `Q` question ·
`C` connection · `B` branch.

## Commands (`holmes.py`)

| Old | New |
|---|---|
| `init` | `init` |
| `usa` | `use` |
| `casos` | `cases` |
| `saude` | `health` |
| `jobs` | `jobs` |
| `questoes` | `questions` |
| `proximo` | `next` |
| `cronologia` | `timeline` |
| `prova` | `proof` |
| `cadeia` | `chain` |
| `conexoes` | `connections` |
| `conexao` | `connection` |
| `extrai` | `extract` |
| `mapa` | `map` |
| `novo` | `new` |
| `edita` | `edit` |
| `leitura` | `reading` |
| `estado` | `state` |
| `liga` / `desliga` | `link` / `unlink` |
| `prob` | `prob` |
| `ach` | `ach` |
| `teste` | `test` |
| `roda` | `run` |
| `resultado` | `result` |
| `busca` | `search` |
| `ja` | `tried` |
| `ver` | `show` |
| `fonte` | `source` |
| `cita` | `quote` |
| `confere` | `prove` |
| `atributo` | `attribute` |
| `ramo novo` / `ramo usa` / `ramo solta` | `branch new` / `branch use` / `branch release` |
| `passo` | `step` |
| `arvore` | `tree` |
| `trilha` | `trail` |
| `ficha` | `sheet` |
| `reorganiza` | `reorganize` |
| `instrumento` | `instrument` |

Corpus (`corpus.py`): `add` · `busca` → `search` · `ver` → `show` · `janela` → `window` · `colecoes` →
`collections` · `embed`. Options: `--autor` → `--author`, `--lote` → `--batch`, `--modo` → `--mode`, `--onde` →
`--where`, `--tipo` → `--type`.

## Options

| Old | New | Old | New |
|---|---|---|---|
| `--alcance` | `--scope` | `--nos` | `--nodes` |
| `--aplica` | `--apply` | `--nota` | `--note` |
| `--canal` | `--channel` | `--origem` | `--origin` |
| `--citacao` | `--quote` | `--pai` | `--parent` |
| `--classe` | `--class` | `--passo` | `--step` |
| `--confiabilidade` | `--reliability` | `--permite` | `--allows` |
| `--controle` | `--control` | `--por` | `--by` |
| `--controle-ok sim\|nao` | `--control-ok yes\|no` | `--porque` | `--why` |
| `--controle-tipo` | `--control-type` | `--previsao` | `--prediction` |
| `--de` | `--from` | `--procedencia` | `--provenance` |
| `--discriminador` | `--discriminator` | `--proibe` | `--forbids` |
| `--enfraquece` | `--weakens` | `--prova` | `--proof` |
| `--estado` | `--state` | `--questao` | `--question` |
| `--executa` | `--execute` | `--ramo` | `--branch` |
| `--exploratorio` | `--exploratory` | `--refuta-se` | `--refuted-if` |
| `--fato` | `--fact` | `--rejeita` | `--reject` |
| `--fonte` | `--source` | `--resumo` | `--summary` |
| `--fora` | `--outside` | `--sem-corpus` | `--no-corpus` |
| `--forca` | `--force` | `--sentido` | `--meaning` |
| `--grau` | `--grade` | `--so` | `--only` |
| `--instrumento` | `--instrument` | `--solucao` | `--solution` |
| `--lacuna` | `--gap` | `--sustenta` | `--supports` |
| `--legado` | `--legacy` | `--titulo` | `--title` |
| `--local` | `--location` | `--tudo` | `--all` |
| `--motivo` | `--reason` | `--verificador` | `--verifier` |
| `--motivos` | `--reasons` | `--nao-usa` | `--no-use` |
| `--natureza` | `--nature` | `--alias`, `--n`, `--pid`, `--log`, `--host`, `--prob`, `--rival`, `--script` | unchanged |

## Types and states (stored values)

| Old type | New type | States (old → new) |
|---|---|---|
| `objetivo` | `objective` | aberto → open · atingido → achieved · abandonado → abandoned |
| `alvo` | `target` | aberto → open · resolvido → solved · bloqueado → blocked |
| `frente` | `front` | ativa → active · estacionada → parked · fechada → closed · descartada → discarded |
| `hipotese` | `hypothesis` | viva → alive · apoiada → supported · refutada → refuted · estacionada → parked |
| `premissa` | `premise` | assumida → assumed · verificada → verified · refutada → refuted |
| `teste` | `test` | planejado → planned · rodando → running · feito → done · cancelado → cancelled |
| `fato` | `fact` | vigente → current · contestado → contested · retratado → retracted |
| `pista` | `clue` | aberta → open · descartada → dropped |
| `entidade` | `entity` | ativa → active · fundida → merged |
| `decisao` | `decision` | vigente → current · revogada → revoked |
| `fio` | `thread` | aberto → open · fechado → closed · estacionado → parked |
| `fonte` | `source` | catalogada → catalogued · indexada → indexed |
| `instrumento` | `instrument` | vigente → current · obsoleto → obsolete |
| `leitura` | `reading` | vigente → current · substituida → superseded |
| `questao` | `question` | aberta → open · respondida → answered · reformulada → reformulated · estacionada → parked |
| `conexao` | `connection` | sugerida → suggested · confirmada → confirmed · rejeitada → rejected |
| `ramo` | `branch` | ativo → active · pausado → paused · morto → dead · fundido → merged · concluido → concluded |

Legacy-only fact state `rascunho` (draft): `reorganize --apply` turns a draft without a recorded proof into a clue; a draft that already has a recorded proof stays a fact and becomes `current`.

## Other stored values

| Field | Old → new |
|---|---|
| nature | observacao → observation · medicao → measurement · citacao → quote · inferencia → inference · interpretacao → interpretation · relato → report |
| origin | autor → author · fonte → source · medido → measured · usuario → user · agente → agent · externo → external |
| edge | sustenta → supports · enfraquece → weakens · contradiz → contradicts · refuta → refutes · depende → depends · duplica → duplicates · substitui → supersedes · sobre → about · deriva → derives · responde → answers · rival → rival |
| step | abriu → opened · bifurcou → forked · registrou → recorded · mudou → changed · testou → tested · leu → read · pensou → thought · achou → found · corrigiu → corrected · decidiu → decided · proximo → next |
| proof (`--by`) | fonte → source · medicao → measurement · teste → test · reproducao → reproduction |
| result | positivo → positive · negativo → negative · inconclusivo → inconclusive · falhou → failed |
| provenance | primaria → primary · derivada → derived · terceiros → third-party · nossa → ours |
| control type | real → real · plantado → planted · sabotagem → sabotage · nenhum → none |
| test mode | exploratorio → exploratory |
| meaning (`--meaning`) | `nenhum: <why>` → `none: <why>` · `revisar: <what>` → `revisit: <what>` |
| validity flags | INDETERMINADO → INDETERMINATE · A REVALIDAR → TO REVALIDATE · INVÁLIDO → INVALID · sem controle real → no real control · controle não confirmado → control not confirmed · script não versionado → unversioned script |
| verdict labels | ACHADO → FINDING · NEGATIVO → NEGATIVE · CONTROLE → CONTROL · INSTRUMENTO → INSTRUMENT · SEM MUDANÇA → NO CHANGE |
| working modes | LEITURA → READING · CIRURGIA → SURGERY · VARREDURA → SWEEP |

## Database schema

`caso.db` → `case.db`. Tables: `no` → `node`, `fato` → `fact` (it also holds the data of clues), `hipotese` →
`hypothesis`, `teste` → `test`, `execucao` → `run`, `instrumento` → `instrument`, `versao` → `version`, `fonte` →
`source`, `entidade` → `entity`, `atributo` → `attribute`, `decisao` → `decision`, `aresta` → `edge`, `legado` →
`legacy`, `conexao` → `connection`, `ramo` → `branch`, `passo` → `step`, `evento` → `event`, `alvo` → `target`,
`ach` and `idx` unchanged. Columns are translated the same way (`tipo` → `type`, `pai` → `parent`, `titulo` →
`title`, `resumo` → `summary`, `estado` → `state`, `origem` → `origin`, `grau` → `grade`, `criado` → `created`,
`atualizado` → `updated`, `conferido` → `proven_at`, `conferido_por` → `proven_by`, ...). Corpus: `colecao` →
`collection`, `documento` → `document`, `pedaco` → `chunk`.

The corpus migrates on the first ordinary command that opens it (`search`, `health`...). It can take a while on a large corpus, so the session hooks skip an unmigrated corpus instead of migrating it inside their timeout.

## Files, folders and environment

| Old | New |
|---|---|
| `casos/<case>/` | `cases/<case>/` (an existing `casos/` is still used while `cases/` holds no case database) |
| `caso.db`, `CASO.md`, `MAPA.md` | `case.db`, `CASE.md`, `MAP.md` (renamed the first time the case is opened; if they are tracked by git, commit the move with `git add -A casos/<case>`) |
| `fontes/`, `saidas/`, `notas/`, `scripts/` | `sources/`, `outputs/`, `notes/`, `scripts/` (new cases; old folders keep working) |
| `.holmes/ativo`, `.holmes/ramo-<case>`, `.holmes/diario/` | `.holmes/active`, `.holmes/branch-<case>`, `.holmes/journal/` |
| `/tmp/holmes-saidas/` | `/tmp/holmes-outputs/` |
| `HOLMES_RAIZ`, `HOLMES_CASOS`, `HOLMES_CASO` | `HOLMES_ROOT`, `HOLMES_CASES`, `HOLMES_CASE` |
| `HOLMES_TUNEL`, `HOLMES_LEITURA` | `HOLMES_TUNNEL`, `HOLMES_READING` |
| `HOLMES_EMBED_MODELO`, `HOLMES_MAX_DIARIO`, `HOLMES_LIMITE_SAIDA` | `HOLMES_EMBED_MODEL`, `HOLMES_MAX_JOURNAL`, `HOLMES_OUTPUT_LIMIT` |
| hook arguments `abertura`, `pistas`, `guarda`, `pos`, `fim`, `pre-compact` | `start`, `prompt`, `guard`, `post`, `stop`, `pre-compact` (unchanged) |

Old environment variables, folders and hook arguments are still read when the new ones are absent.

## Complete schema and other names (filled in during the code conversion)

Case database, every table and column (old → new where it changed):

| Table | Columns |
|---|---|
| `node` | `id`, `type`, `parent`, `title`, `summary`, `state`, `origin`, `grade`, `created`, `updated`, `legacy` (← `legado`), `branch` (← `ramo`) |
| `target` | `node` (← `no`, same in every table), `solution`, `proof` |
| `hypothesis` | `node`, `prob`, `refuted_if` (← `refuta_se`) |
| `test` | `node`, `scope`, `outside`, `why`, `prediction`, `predicted_at` (← `previsao_em`), `control`, `control_type`, `instrument`, `script`, `recipe` (← `receita`), `mode` |
| `run` | `id`, `test`, `version`, `script_sha`, `host`, `pid`, `log`, `started` (← `inicio`), `finished` (← `fim`), `n`, `control_ok`, `result`, `note`, `meaning` (← `sentido`) |
| `instrument` | `node`, `path` (← `caminho`), `verifier` |
| `version` | `id`, `instrument`, `sha`, `at` (← `quando`, same everywhere), `verified`, `note` |
| `fact` | `node`, `nature`, `source`, `location` (← `local`), `quote` (← `citacao`), `proven_at`, `proof`, `proven_by` |
| `source` | `node`, `ref`, `sha`, `provenance`, `reliability`, `document` |
| `entity` | `node`, `class`, `aliases` |
| `attribute` | `entity`, `key` (← `chave`), `value` (← `valor`), `fact`, `at` |
| `decision` | `node`, `forbids`, `allows` |
| `edge` | `src` (← `de`), `type`, `dst` (← `para`), `note`, `created` |
| `ach` | `fact`, `hypothesis`, `value`, `note` |
| `legacy` | `ref`, `node` |
| `connection` | `node`, `src`, `dst`, `relation`, `rival`, `discriminator`, `channel` |
| `event` | `id`, `node`, `action` (← `acao`), `text`, `at` |
| `idx` (FTS5) | `ref`, `text` (rebuilt on migration) |
| `branch` | `node`, `from_step` (← `de_passo`) |
| `step` | `id`, `branch`, `type`, `text`, `why`, `nodes`, `at` |

Indexes: `no_pai` → `node_parent`, `passo_ramo` → `step_branch`.

Corpus: `colecao(nome, criado)` → `collection(name, created)`; `documento(colecao, titulo, tipo)` →
`document(collection, title, type)`; `pedaco(documento, ordem, autor, texto)` → `chunk(document, position, author,
text)`; `vetor(pedaco, modelo)` → `vector(chunk, model)`; `pedaco_fts` → `chunk_fts` (rebuilt on migration, a few
seconds on a large corpus). Chunk kinds `janela` → `window`, `secao` → `section`, `pagina` → `page` (`msg` and
kinds written by other tools are kept); document type `texto` → `text`. Corpus options: `-c/--colecao` →
`-c/--collection`; `--modo vetor|hibrido` → `--mode vector|hybrid`; `--tipo texto` → `--type text`. A chat JSONL
is read with `author`/`text` keys (the old `autor`/`texto` still work).

More stored values:

| Field | Old → new |
|---|---|
| fact state (legacy only) | rascunho → draft |
| entity class the code reads | evento → event · conceito → concept (other classes are kept as written) |
| attribute key the code reads | quando → when |
| edge notes on a reading | decisiva → decisive · lacuna → gap |
| event actions | criou → created · editou → edited · rodando → running · nova versão → new version · substituida → superseded · reclassificado → reclassified · religado → relinked · conferido → checked · `X12 positivo` → `X12 positive` · `liga sustenta` → `link supports` · `desliga ..` → `unlink ..` · `provado por fonte` → `proven by source` · `atributo quando` → `attribute when` · `prova ok/FALHOU` → `proof ok/FAILED` · `<old state>→<new state>` translated per node type; `prob ..` and `ach ..` unchanged; a new `migrated` event marks the migration |
| `version.note` | detectada ao rodar → detected when running |
| `created` event text | its leading type is translated (`fato: ..` → `fact: ..`); the titles and other free text are not |

Not translated on migration (they are records, not values the code reads): titles, summaries, notes, step texts,
event texts other than the type prefix above.

Extraction contract keys (`extract`; the old keys are still accepted): `fonte` → `source`, `observacoes` →
`observations`, `pistas` → `clues`, `interpretacoes` → `interpretations`, `questoes` → `questions`, `hipoteses` →
`hypotheses`, `conexoes` → `connections`, `discriminadores` → `discriminators`, `impacto` → `impact` (`plano` →
`plan`, `leitura` → `reading`). Item keys: `texto` → `text`, `natureza` → `nature`, `origem` → `origin`, `grau` →
`grade`, `local` → `location`, `citacao` → `quote`, `pedaco` → `chunk`, `metodo` → `method`, `limites` → `limits`,
`por` → `by`, `prova` → `proof`, `existente` → `existing`, `pai` → `parent`, `resumo` → `summary`, `motivada_por` →
`motivated_by`, `sobre` → `about`, `porque` → `why`, `alternativas` → `alternatives`, `confianca` → `confidence`,
`refuta_se` → `refuted_if`, `responde` → `answers`, `premissas` → `premises`, `rivais` → `rivals`, `de`/`para` →
`from`/`to`, `relacao` → `relation`, `discriminador` → `discriminator`, `motivos` → `reasons`, `canal` → `channel`,
`estado` → `state`, `entre` → `between`, `observacao` → `observation`; `id` and `obs` unchanged.

Evaluation (`holmes/eval/evaluate.py`): `recuperacao` → `recall`, `pontua` → `score`. Answer-key JSON:
`caso` → `case`, `objetivo` → `objective`, `solucao` → `solution`, `palavras_da_solucao` → `solution_words`,
`pistas` → `clues` (`onda` → `wave`, `texto` → `text`), `ligacoes` → `links` (`conceito` → `concept`),
`armadilhas` → `traps` (`porque` → `why`), `conceitos_do_interprete` → `interpreter_concepts` (`nome` → `name`);
in links and traps, `de`/`para` → `from`/`to`. Old answer keys are read as they are, with no conversion needed.
Score keys: `clues_recorded`, `true_links_in_graph`, `traps_accepted_in_graph (false positive)`,
`traps_rejected_explicitly`, `suggested_connections_without_decision`, `interpretations_as_observation (error)`,
`questions`, `hypotheses`, `hypotheses_without_refuted_if`, `reading_revisions`, `final_reading_contains_solution`,
`tests_spent`. The watchmaker clues are now in English; the recall numbers did not change.

Output labels: `MAPA` → `MAP`, `OBJETIVO` → `OBJECTIVE`, `LEITURA ATUAL` → `CURRENT READING`, `RAMO ATIVO` →
`ACTIVE BRANCH`, `PRÓXIMO` → `NEXT`, `ALVOS` → `TARGETS` (`DESBLOQUEADO` → `UNBLOCKED`), `FRENTES ATIVAS` →
`ACTIVE FRONTS`, `QUESTÕES ABERTAS` → `OPEN QUESTIONS`, `ALERTAS` → `ALERTS`, `TÚNEL` → `TUNNEL`, `LEITURA DE
CONJUNTO` → `OVERALL READING`, `FRONTEIRA` → `FRONTIER`, `TESTES ABERTOS` → `OPEN TESTS`, `DECISÕES DO USUÁRIO` →
`USER DECISIONS`, `FIOS ABERTOS` → `OPEN THREADS`, `ÚLTIMOS EVENTOS` → `LATEST EVENTS`; `FICHA` → `SHEET`,
`IMEDIATO` → `IMMEDIATE`, `ÚLTIMOS PASSOS` → `LATEST STEPS`, `PRÓXIMA EXPERIÊNCIA` → `NEXT EXPERIMENT`, `JÁ
PERCORRIDO AQUI` → `ALREADY EXPLORED HERE`, `RESOLVIDO (tronco)` → `SOLVED (trunk)`, `OUTRAS LINHAS ABERTAS` →
`OTHER OPEN LINES`; fact stamp `provado:<by>` / `não-provado` → `proven:<by>` / `unproven`; `CAIU` → `FELL`;
`LACUNA` → `GAP`; `porque:` → `why:` in trails and `next`; `proof --execute` prints `OK`/`FAILED`.

Local state: `.holmes/sessoes/<id>.vistos` → `.holmes/sessions/<id>.seen` (the hooks still read the old file
when the new one is absent); the keys of `.holmes/hooks.json` become the new hook names (old keys are read as
their new names by `health`), and an old `FALHOU` status shows as `FAILED`. The trimming mod writes to
`/tmp/holmes-outputs/` and reads `HOLMES_OUTPUT_LIMIT` (then `HOLMES_LIMITE_SAIDA`). Corpus vectors read
`HOLMES_EMBED_MODEL` (then `HOLMES_EMBED_MODELO`).
