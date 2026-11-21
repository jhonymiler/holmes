# Extração investigativa: do material à compreensão

Sequência conceitual, não obrigação de criar um objeto por etapa:
**material → observação → pista → conexão → questão → hipótese → evidência → síntese.**
Pare onde a informação parar. Uma observação sem pista é um registro válido; uma fonte sem nada relevante é
um resultado ("nada extraído de S12, lida inteira").

## A. Preservar e localizar
`fonte <arquivo>` (sha, procedência). Original só leitura. Toda observação aponta para onde está (`local`,
`pedaco`) e como foi obtida (`metodo`, `limites`). A interpretação nunca substitui o original.

## B. Decompor em observações
Unidades verificáveis uma a uma, no vocabulário do material:

| Material | Olhe |
|---|---|
| Texto | termos, nomes, datas, referências, negações, o que mudou em relação a uma versão ou ao original citado, estrutura |
| Imagem | objetos, posições, cores, formas, simetria, diferenças, agrupamentos |
| Números | valores, distribuição, sequências, intervalos, repetições |
| Saída de execução | além do sucesso ou falha: formato, conteúdo, o que saiu diferente do esperado |
| Acontecimento | quem, o quê, quando (`entidade --classe evento` + `atributo quando`), causa alegada ou demonstrada |

Observação: "a célula (3,7) tem RGB FEFEFE". Não é observação: "o autor marcou a célula". Isso é interpretação.

## C. Pista: por que olhar para isto
Anomalia, repetição, contraste, simetria ou assimetria, diferença entre versões, correspondência, referência,
ausência onde a presença era esperada, algo que contraria uma previsão, algo que a leitura atual não explica.
Não presuma intenção: anomalia pode ser erro, artefato de processamento, ruído ou normalidade. Não descarte o
comum: ele fica pesquisável e pode virar pista quando outra coisa aparecer.

## D. Conexões
`conexoes <id>` ou `conexoes "<o conceito em palavras>"` antes de registrar algo como novo. Se duas pistas
parecem apontar para a mesma ideia sem dividir palavra, nomeie a ideia e registre-a como entidade com aliases
(`novo entidade "complementaridade" --classe conceito --alias "duas metades,yin-yang"`): daí em diante, ela liga
o que chegar. Para cada candidata, escreva a relação, a rival (acaso, tema genérico, mesma fonte repetida) e o
discriminador. Grave só a promissora (`conexao`) e a rejeição que evitaria redescoberta. Três agentes repetindo
a mesma leitura não são três evidências.

## E. Questões
O que segue sem explicação? Que informação falta? Duas pistas apontam para o mesmo fenômeno? A pergunta atual
parte de uma premissa falsa? Questão sem hipótese é legítima: fica aberta e aparece como lacuna.

## F. Hipóteses
Para as questões que comportam explicação: o que explica, o que a motivou, de que premissas depende, o que
prevê, o que a enfraqueceria, quais as rivais. Inclua acaso, erro, artefato e engano quando forem rivais
plausíveis, não para cumprir número. Exploratória (sem `--refuta-se`) pode ser explorada; só a operacional
recebe teste confirmatório.

## G. Integrar ao plano
A informação reforça uma questão, revela dependência, abre ou enfraquece hipótese, liga frentes, resolve
lacuna ou muda prioridade? Frente nova só para problema relevante e independente (máx. 5 ativas).

## H. Atualizar a compreensão
O que mudou no entendimento geral? Se nada, a leitura fica. Se mudou: `leitura "..." --sustenta .. --rival ..
--questao .. --motivo "<o que mudou e por quê>"`.

## Registrar de uma vez: o contrato
Para uma fonte com várias unidades, escreva o JSON do contrato (`MODELO.md`, "Contrato de extração"), rode
`holmes.py extrai f.json` para ver o plano e `--aplica` para gravar. Exemplo mínimo:

```json
{"fonte": "S12",
 "observacoes": [{"id": "o1", "texto": "Rodapé com yin-yang a tinta", "local": "folha 2", "metodo": "visual"}],
 "pistas": [{"obs": "o1", "sobre": "Q4", "porque": "único desenho da folha"}],
 "conexoes": [{"de": "o1", "para": "E3", "relacao": "sobre", "porque": "duas metades ↔ yin-yang",
               "rival": "símbolo decorativo comum", "discriminador": "fica onde as partes se juntam?"}]}
```

Quando não registrar: o que só repete o que já está no corpus e não pesa em nenhuma questão. Fica pesquisável.
