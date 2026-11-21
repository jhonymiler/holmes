# F4–F6 — Controle, validação e verificação

## Controle: poder medido, nunca dado plantado

Declarar `--controle-tipo real` não é ver o controle passar: sem `resultado ... --controle-ok sim`, o
resultado sai "controle não confirmado" e não sustenta conclusão. Teste `--exploratorio` nunca sustenta.

Plantar um dado gerado pela própria função e ver se ela o acha prova só o comparador: f(x) == f(x).
Consistência interna tem o mesmo defeito. Quem escreve o teste já sabe a resposta.

Preferir, nesta ordem:

1. **Dado real já publicado:** vetor oficial, valor que outra pessoa publicou, ou resposta que o
   próprio caso já tem.
2. **Duas implementações independentes**, feitas em momentos diferentes.
3. **Taxa observada contra prevista em dado real:** afrouxe o critério até aparecerem acertos por
   acaso e compare com a taxa esperada. Prova que o caminho inteiro roda sobre dado real.
4. **Contar o que o teste fez:** número de candidatos realmente gerados.
5. **Sabotagem:** plante um defeito no código, não um dado, e exija que o controle acuse. Controle
   que sobrevive à sabotagem é decoração. Defeito que nenhum controle vê é achado grave: declare-o.

Declare o negativo com o poder do controle ("pega k de m sabotagens") e o que ficou cego.
"Controle: OK" não declara nada.

Registre o instrumento com `instrumento <caminho> "<nome>"`. Se ele mudar, os testes antigos
ficam "a revalidar".

## Critérios para aceitar uma solução

Responda um a um: válido / inválido / indeterminado.

1. **Sem escolha no meio.** Método e parâmetros aplicados de forma mecânica.
2. **Validade dupla:** o resultado faz sentido e o método foi aplicado com precisão.
3. **Não acaso:** P(acaso) calculada sobre o espaço realmente percorrido.
4. **Reprodução:** outra pessoa, só com o método, chega ao mesmo resultado.
5. **Tamanho:** resultado longo o bastante para não ser coincidência.
6. **Erros pequenos** e, se houver, com uma causa única.
7. **Sem rearranjo** depois de selecionar.

## Contra ajuste fino

- **Controle com a mesma liberdade:** aplique o mesmo procedimento a material sem mensagem. Se ele
  também "fala", a regra não tem conteúdo.
- **Variações:** perturbe cada parâmetro arbitrário. Se quase toda variação piora, os parâmetros
  foram ajustados ao dado.
- Concordância perfeita demais sugere ajuste iterativo.
- **Previsão sobre dado não usado:** a regra tirada de uma parte deve funcionar no resto.

## Discrepâncias

Liste toda discrepância entre candidato e evidência, inclusive ausências esperadas. Cada uma
precisa de explicação com evidência independente. Uma sem explicação → inconclusivo. Duas ou
mais → exclusão provável. "Poderia" e "é consistente com" não são evidência.

## Nível da proposição

| Nível | Proposição |
|---|---|
| Operação | Este procedimento produz este resultado |
| Fonte | Este é o valor ou documento verdadeiro |
| Atividade | Quem produziu o material quis esta leitura |
| Resolução | Isto responde ao objetivo do caso |

LR alto num nível não sobe para o de cima.

## Verificação (F6)

- Quem julga não escreveu o teste. O verificador recebe dados, critério e candidatos com 1–2
  chamarizes, sem saber qual é o suspeito.
- Reprodução por agente sem o histórico, só com a receita escrita.
- Discordância: base completa e agente novo. Nunca negociar o veredito.

## Resultado de terceiros

1. Procure retratação antes de adotar.
2. Que critério de aceitação o autor usou? Calcule o acaso com o número de tentativas dele.
3. Reproduzir um arquivo publicado prova que ele é coerente, não que é a solução.
4. Date a publicação.

## Checklist do achado (sim / não / discutível)

1. Proposições escritas antes do resultado, ainda as mesmas?
2. Nível declarado e o critério fala desse nível?
3. Previsão registrada no `teste`?
4. FPR e sensibilidade medidos; alarmes esperados muito abaixo de 1?
5. Controle com poder medido nesta execução?
6. Campeão comparado ao máximo sob ruído?
7. Discrepâncias explicadas com evidência independente?
8. Traços finos reproduzem em todas as versões?
9. Leitura registrada antes das referências?
10. Fontes indexadas e com origem?
11. Verificador cego concordou; reprodução bateu?
12. Conclusão nas escalas de `padroes.md`?
13. Critérios 1–7 e testes contra ajuste fino feitos?
