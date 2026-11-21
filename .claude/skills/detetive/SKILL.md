---
name: detetive
description: "Método de investigação para qualquer caso com evidência fragmentada, hipóteses concorrentes ou risco de conclusão precipitada: enigma, auditoria, pesquisa, perícia de dados. Use ao abrir ou retomar um caso, gerar hipóteses, planejar ou avaliar um teste, julgar se um padrão é real ou coordenar o time de agentes. Gatilhos: investigar, caso, hipótese, pista, evidência, teste, padrão, auditoria, perícia, retomar."
---

# Detetive

Protocolo curto. Detalhes em `references/`, carregados só quando o passo pede.

## Mapa primeiro

Antes de qualquer outra ação, e de novo a cada decisão: `python3 -I holmes/holmes.py mapa`.
O mapa é o plano geral. Se a ação não serve a um alvo ou frente do mapa, não faça.
Antes de testar ou afirmar algo novo: `ja "<termo>"`. Achado anterior: `ver <id>` e leia inteiro.
A `LEITURA ATUAL` do mapa é a história que o caso parece contar: todo teste deve fazer sentido nela.

## Sentido antes de mecânica

Pista e fonte se leem em camadas (literal, figurada, alusão, função, subliminar, ausência) antes de
virar operação. Todo resultado tem dois julgamentos: número (nulo, controle, alcance) e sentido (o que a
saída diz no contexto). Hipótese é conceito; teste é uma forma dele; um 0 fecha a forma. → skill `leitura`

## Quatro leis

1. Parecer verdade não é evidência. O observado não é o que se acha que aconteceu.
2. Evidência compatível com todas as hipóteses não distingue nenhuma.
3. Numa cadeia, a probabilidade é o produto dos elos. Cada detalhe a mais torna a história menos provável.
4. Um acerto vale pela liberdade gasta para obtê-lo. Tentativas e escolhas de análise entram na conta.

## Modo de trabalho (declare antes de agir)

| Modo | Faz | Não faz |
|---|---|---|
| LEITURA | Lê fonte, formula hipótese, registra fatos e fios | Rodar teste |
| CIRURGIA | 1 a 3 testes pontuais, cada um ligado a uma hipótese | Ampliar o espaço |
| VARREDURA | Busca ampla | Começar sem hipótese ancorada em fonte primária e sem custo estimado |

Na dúvida, LEITURA. Mude de modo de forma explícita.

## Registro

Todo fato, hipótese e decisão vai para o registro, não para a conversa.

| Marca | Comando |
|---|---|
| Trecho literal da fonte | `cita <pedaço do corpus> "<afirmação>"` (copia o texto e já sai conferido) |
| Fato medido ou lido | `novo fato "<t>" --natureza observacao\|medicao --origem medido\|fonte --fonte S.. --grau A\|B\|C` |
| Interpretação, inferência | `novo fato "<t>" --natureza interpretacao\|inferencia --origem agente` (nunca vira fala do autor) |
| Relato de terceiro, outra IA, nota antiga | `novo fato "<t>" --natureza relato --origem externo` (grau C, rascunho até `confere`) |
| Hipótese | `novo hipotese "<t>" --pai <frente> --prob 0.4 --refuta-se "<o que a derruba>"` |
| Premissa | `novo premissa "<t>" --pai <frente>` + `liga <H> depende <R>` |
| Peso da evidência | `ach <E> <H> CC\|C\|N\|I\|II`; `ach <F>` mostra a matriz e o que é diagnóstico |
| Teste | `teste <hip> "<t>" --alcance .. --porque "se + abre X; se − fecha Y" --previsao --controle --controle-tipo real --instrumento I..` |
| Rodar | `roda <T> --pid <pid> --log <arquivo>` (longo) ou direto `resultado` (rápido) |
| Palpite barato | `teste <hip> "<t>" --alcance .. --porque .. --exploratorio` (vale como pista; não precisa de `--refuta-se`) |
| Resultado | `resultado <T> positivo\|negativo\|inconclusivo\|falhou "<nota>" [--sentido "<o que diz>"\|"nenhum: <por quê>"] --n <tamanho> --controle-ok sim\|nao` |
| Questão | `novo questao "<pergunta>" --pai <frente\|alvo\|O>`; hipótese que a responde: `liga <H> responde <Q>`; `questoes` |
| Relação possível | `conexoes <id\|"conceito">` (consulta) → `conexao <de> <para> <relação> "<por quê>" --rival .. --discriminador ..` → `estado C.. confirmada\|rejeitada "<evidência>"` |
| Fonte com várias unidades | contrato JSON → `extrai f.json` (plano) → `--aplica` (`references/extracao.md`) |
| Teoria de trabalho | `leitura "<quadro>" --sustenta E.. --rival H.. --questao Q.. --lacuna Q.. --motivo "<o que mudou>"` |
| Critério de hipótese | `edita <H> --refuta-se "<o que a derruba>"` (teste confirmatório exige) |
| Orientar-se | `proximo` (o que fazer e por quê) · `cadeia <id>` (no que algo se apoia) · `cronologia` |
| Linha encerrada | `estado <id> refutada "<id do teste ou fato que mostrou>"` |
| Decisão do usuário | `novo decisao "<t>" --origem usuario --proibe ".." --permite ".."` (escolha de método sua é fato `--natureza inferencia`) |
| Ponta solta | `novo fio "<t>"` |
| Conflito | `liga <E1> contradiz <E2>` (fica no mapa até um ser retratado) |
| Objeto recorrente | `novo entidade "<nome>" --classe .. --alias "sinônimo,grafia"`; `atributo <N> <chave> <valor> --fato E..` |

Ausência só é fato com o alcance: "não há X em Y, procurado por Z". Ela pesa contra uma hipótese
só quando a hipótese prevê a presença e o método tem sensibilidade medida para achá-la.

## Ciclo

**F0 Coleta.** Coletar antes de analisar. Original só leitura; derivado aponta o pai.
`fonte <caminho>`. → `custodia.md`

**F1 Leitura.** Ordem: o que já foi feito (`ja`), fonte bruta com leitura própria escrita antes,
metadados, interpretações anteriores, soluções de terceiros por último. Leia em camadas (skill
`leitura`). Leitura por ferramenta pede segunda leitura independente. Do material à questão:
observação → pista → conexão → questão. → `leitura.md`, `extracao.md`

**F2 Hipóteses.** Rivais de verdade, não cota: considere acaso, erro técnico banal, engano e
artefato quando forem plausíveis. Só sai a refutada. Probabilidades somam 1 só entre rivais
mutuamente exclusivas (com "outra"); explicações que podem coexistir não se normalizam. → `hipoteses.md`

**F3 Pré-avaliação.** Antes de teste que custe mais que minutos: que hipótese o resultado exclui?
Se nenhuma, não roda. Previsão numérica, controle com poder medido, custo estimado, alcance
declarado. → `quantitativo.md`

**F4 Execução.** Controle em cada execução. Script e log no `teste`. Instrumento registrado com
`instrumento`; se mudar, testes antigos ficam "a revalidar". → `validacao.md`

**F5 Avaliação.** Proposições são as de F2? Compare com o máximo sob ruído. Liste discrepâncias.
Leia a saída como texto e forma, não só como contagem (`--sentido`). Positivo sai como candidato,
nunca como achado. → `validacao.md`

**F6 Verificação.** Quem julga não escreveu o teste. Verificador cego, com chamarizes.

**F7 Revisão.** Retratou algo: reavalie dependentes. Troca de hipótese líder: estime do zero
antes de olhar a antiga.

## Proporcionalidade

| Ação | Exige |
|---|---|
| Leitura, pergunta factual | Nada |
| Tentativa barata (< 10 min) | `teste` + `resultado`; vale como pista, não como cobertura |
| Teste citado como evidência | F3 (exclui o quê, custo) e controle |
| Varredura ou encerrar linha | F0 a F5 |
| Declarar achado | F0 a F7 |

Os portões protegem afirmações, não tentativas. "Falta F3" não é motivo para não tentar algo
barato. Caso parado: `exploracao.md`.

## Concluir

Duas frases separadas (`padroes.md`): probabilidade com número ("provável, 55–80%") e confiança
na base (alta, moderada, baixa). Diga o que refutaria e o que mudou desde o último julgamento.
"Em aberto, e eis o teste que decidiria" é conclusão válida. "Parece" sem peso é proibido.

## Parar

- Conclua quando uma hipótese sobrevive, as rivais têm inconsistência dura e uma previsão nova
  se confirmou por via independente.
- Encerre a linha quando só vive com remendos, o custo supera o valor, ou três ações seguidas
  não moveram nenhuma probabilidade. Negativo encerra a receita testada e baixa a confiança no tema.
- Após negativos repetidos, volte às premissas (F1, F2) antes de ampliar o espaço.
- Nunca pare porque a resposta parece óbvia ou porque já investiu muito.

## Time

O coordenador (sessão principal) decide, registra e integra: o papel de integrador é dele, não de um agente. Regras de delegação: `agentes.md`.

| Fase | Agente |
|---|---|
| F0 | `arquivista` |
| F1, F2 com fonte externa | `pesquisador` |
| F1 a F3 | `analista` |
| F1, leitura de conjunto, caso preso na mecânica | `interprete` (sem ver a sua leitura) |
| F4 | `engenheiro`, depois `revisor` |
| F6 | `verificador` |
| Antes de registrar negativo | `ceticismo` |

Relatório de agente entra grau C até conferido na fonte (skill `conferir-relatorio`).

## Anti-padrões

- Agir sem ler o mapa. Refazer o que `ja` mostraria.
- Caçar confirmação da primeira hipótese.
- Ler pista como string: testar a palavra como senha, varrer livro por termo, julgar sentido por p.
- Dar o conceito por morto porque uma forma dele deu 0.
- Padrão achado depois de olhar, sem previsão nem controle.
- Registrar intenção como resultado.
- Delegar sem contexto; ou delegar a verificação com o veredito.

## Referências

| Arquivo | Quando |
|---|---|
| `leitura.md` | F1 |
| `hipoteses.md` | F2 |
| `quantitativo.md` | F3, F5 |
| `validacao.md` | F4 a F6 |
| `custodia.md` | F0 |
| `padroes.md` | Concluir |
| `vieses.md` | Revisão |
| `fichas.md` | Modelos de registro por fase |
| `extracao.md` | Material novo: observação, pista, conexão, questão, contrato JSON |
| `exploracao.md` | Caso parado |
| `agentes.md` | Antes de delegar |
| `cripto.md` | Opcional: casos com cifras |
| `leituras.md` | Bibliografia |
