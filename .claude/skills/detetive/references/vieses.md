# Vieses e contramedidas

Saber que o viés existe não o corrige. Só o procedimento corrige. Agente de IA não é imune.

| Viés | Como aparece | Contramedida |
|---|---|---|
| Confirmação | Ler só o que apoia a favorita | Escrever antes o que a refutaria |
| Ancoragem | Primeira leitura ou relatório de agente domina | Julgar antes de ler o alheio; estimar do zero antes de ver o antigo |
| Dado borrado primeiro | Leitura de item ambíguo contamina as seguintes | Marcar como provisória; reler do zero com dado melhor |
| Incrementalismo | Um negativo por dia, nada muda | Revisão do zero periódica |
| Evidência retratada | Impressão sobrevive ao fato que caiu | `estado <id> retratado` e reavaliar ligados (`ver <id>`) |
| Direção centralizada | "Todo detalhe foi intencional" | H-artefato na matriz |
| Semelhança | Problema de tipo X "pede" solução de tipo X | Perguntar se precisa ser do mesmo tipo |
| Narrativa | História coerente parece verdadeira | P(cenário) = produto dos passos |
| Aceitação pela coerência | Dado aceito porque fecha a história | Graduar antes de encaixar |
| Explicar dando nome | "É um caso de X" como explicação | Exigir o teste que separa X das rivais |
| Pequenos números | Poucos dados, todos consistentes | Confiança limitada pelo tamanho |
| Vivacidade | "Alguém jurou que viu" | Grau C até haver material verificável |
| Imersão nos dados | "Vou olhar até ver algo" | Hipótese escrita antes de olhar |
| Orientação ao método | Continuar porque a ferramenta está pronta | Toda ferramenta responde a uma pergunta |
| Taxa-base | Esquecer quantas tentativas assim falharam | Prior pela visão de fora |
| Disponibilidade | Hipótese elaborada parece provável | Trabalho investido não é evidência |
| Retrospectiva | "Era óbvio" depois | `--previsao` no `teste` |
| Custo afundado | Insistir porque já gastou | Regra de parada escrita no início |
| Mais informação | Juntar mais material para ter certeza | Classificar a informação esperada (`hipoteses.md`) |
| Cascata | Hipótese do coordenador escorre para o verificador | Verificador sem o veredito, com chamarizes |
| Bola de neve | Instrumento ajustado no material da hipótese | Instrumento e corpus de fora do caso |
| Planejamento | Prazo estimado no papel | Taxa medida onde vai rodar |
| Ruído | Mesmo agente julga diferente em outra ordem | Julgamentos independentes e média |
| Afogamento | Muito material, plano perdido | Voltar ao `mapa`; declarar o modo |

## Falácias frequentes

Afirmar o consequente; correlação lida como causa; falso dilema (sem H-nada e H-mundano); apelo à
ignorância; atirador do Texas (alvo desenhado em volta dos tiros); espantalho da rival; condicional
transposto; multiplicar evidências dependentes; regressão à média lida como efeito.

## O viés oposto de cada técnica

Depois de usar a técnica, uma linha de contrapeso:

| Técnica | Viés oposto |
|---|---|
| Checar premissas | Culpar a situação demais |
| Checar fontes | Subconfiança; busca sem fim |
| Indicadores | Superconfiança, sobreajuste |
| ACH | Probabilidades incoerentes (somar 1 corrige, se as rivais forem exclusivas) |
| Leitura de sentido | Conexão semântica espúria: tema amplo liga tudo; exija previsão que a rival não faça |
| Conexões candidatas | Coleção de associações imaginárias: grave só a promissora, rejeite com motivo |
| Advogado do diabo; "e se?" | Esquecer a taxa-base |
| Equipe A/B | Polarização |

Às vezes a melhor técnica é nenhuma: técnica não substitui medição.

## Sintomas de investigação doente

Método congelado; levantamento eterno; nunca termina; uma pessoa com uma hipótese; teoria que nunca
pode ser falsificada; mapa desatualizado. Use como autodiagnóstico na revisão do zero.
