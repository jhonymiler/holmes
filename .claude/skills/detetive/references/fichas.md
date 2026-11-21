# Modelos de registro por fase

Estado e dado vão para o registro (`python3 -I holmes/holmes.py`). Prosa longa vai para um `.md`
indexado com `fonte`. Uma ficha é o resumo (`--resumo`) do nó, ou um `.md` ligado a ele.

## Comandos por fase

| Fase | Comandos |
|---|---|
| Abrir | `init <caso> "<objetivo>"`, `usa <caso>`, `novo alvo`, `novo frente` |
| Retomar | `mapa`, depois `ver <id>` do que estiver ativo |
| F0 | `fonte <caminho> --titulo "<t>"` |
| F1 | `cita <pedaço> "<t>"` ou `novo fato "<t>" --natureza --origem --fonte --grau`; `novo fio`; `novo questao`; várias unidades: `extrai f.json [--aplica]` |
| Relações | `conexoes <id\|"conceito">`; `conexao <de> <para> <relação> "<por quê>" --rival --discriminador`; `estado C.. confirmada\|rejeitada` |
| F2 | `novo hipotese "<t>" --pai <frente> --refuta-se ..`; `liga <H> responde <Q>`; `liga <a> rival <b>` |
| F3 | `teste <hip> "<t>" --alcance --porque --fora --controle --controle-tipo --previsao --instrumento` |
| F4 | `instrumento <caminho> "<nome>" --verificador "<cmd>"`; `teste ... --script`; `roda <T> --pid --log`; `jobs` |
| F5, F6 | `resultado <teste> positivo\|negativo\|inconclusivo\|falhou "<nota>" --sentido --n --controle-ok`; `ach <E> <H> <valor>` |
| F7 | `estado <id> <estado> "<motivo>"`; `novo decisao`; `leitura ".." --sustenta --rival --questao --motivo` |
| Consulta | `busca`, `ja`, `ver`, `cadeia`, `questoes`, `proximo`, `cronologia` |

## F1 — Leitura

```
Já feito (ja): ids lidos
Leitura própria (antes de ver interpretações): fonte · mensagem · referentes · confiança
Outra leitura (muda sentido ou referente)
Discriminador: o que separaria as leituras
Ponte para a operação + escolhas livres restantes
Depois das referências: "mudei X porque vi Y"
Segunda leitura de dado extraído por ferramenta
Inventário de consumo: elemento → etapa que o explica
```

## F2 — Hipóteses

```
Hipóteses: H-nada, H-mundano, H-adversária, H-erro, H-artefato, de terceiros
Prior pela visão de fora: k de N tentativas do tipo acertaram
Premissas: premissa | relevância 0-2 | suporte 0-2 | o que a derrubaria
Matriz ACH (preenchida por linha) + coluna "fácil de forjar?"
Status: viva | refutada (por qual fato)
Probabilidades (somam 1, com "outra", só entre rivais exclusivas)
Marcos que mudariam a conclusão
```

## F3 — Pré-avaliação (vai nos campos do `teste`)

```
titulo:      receita em uma linha
alcance:     espaço exato que será coberto
fora:        o que fica de fora
exclui:      que hipótese o resultado exclui (no resumo)
resultados:  acerto / sinal fraco / nada → P|H, P|H-nada, LR
previsao:    P(evento) = 0,0x
controle:    tipo (dado real, dupla implementação, taxa, sabotagem) e poder medido
criterio:    FPR, sensibilidade, alarmes esperados = FPR × N
escolhas:    fixadas antes (início, índice, formato, recorte)
custo:       espaço ÷ taxa medida
ja:          execuções anteriores da mesma receita, ou "nenhuma"
premortem:   por que terminaria sem achado ou com achado falso
```

## F4 — Execução

O script grava receita, hash do script, instrumento, N, taxa, controle, acertos e log. Revisão do
`revisor`: espaço declarado = espaço executado, controle com poder, instrumento compartilhado sem
cópia local, taxa medida no lugar certo. Sem revisão, não vale como cobertura.

## F5 — Avaliação

```
Proposições: as da F2? sim/não
Melhor escore vs máximo de N sob ruído
Controle com a mesma liberdade · variações
Discrepâncias: item | explicação | evidência independente? → veredito
Critérios de aceitação 1–7
Nível: operação | fonte | atividade | resolução
Conclusão: probabilidade · confiança · LR verbal · mudança
```

## F6 — Verificação (escrita pelo verificador)

```
Recebido: dados + critério + K candidatos (sem saber o suspeito)
Reprodução: receita seguida passo a passo → resultado obtido
Veredito por candidato
Probabilidade independente (soma 1 entre rivais exclusivas)
Discordâncias
```

## F7 — Revisão

- Decisão: opções consideradas, escolhida, rejeitadas e por quê (`novo decisao`).
- Retratação: `estado <id> retratado "<motivo>"`; abra `ver <id>` e reavalie cada ligado.
- Revisão do zero: estimativa nova antes de ver a antiga, a antiga, a diferença, surpresas relidas.
- Negativo repetido: tabela É / NÃO É. "Se X é a causa, por que aparece aqui e não ali?"
