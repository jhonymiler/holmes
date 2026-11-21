# Avaliação da capacidade investigativa

Dois níveis, que não se confundem:

| Nível | O que mede | Roda sem modelo? | Comando |
|---|---|---|---|
| Mecanismo | se a descoberta de relações põe o par certo entre as 5 primeiras candidatas | sim | `python3 -I holmes/aval/aval.py recuperacao` |
| Investigação | se um agente, usando o holmes, chega à solução sem fabricar relações | não: precisa de uma sessão real | protocolo abaixo + `aval.py pontua` |

## Caso sintético `relojoeiro.json`

30 pistas em 3 ondas (texto, objeto, número, documento, símbolo), 9 ligações verdadeiras (2 literais e 7 só por
conceito), 4 armadilhas (palavra igual sem relação) e 13 distratoras. A solução é conhecida e fica fora do caso.

Medido em 2026-11-20 (top 5):

| Modo | Ligações | Não literais | Armadilhas na lista |
|---|---|---|---|
| `busca` (o que existia) | 3/9 | 1/7 | 3/4 |
| `conexoes` | 3/9 | 1/7 | 2/4 |
| `conexoes` + conceitos do intérprete | 9/9 | 7/7 | 2/4 |

> [!NOTE]
> A terceira linha é teto, não desempenho: os conceitos vieram do gabarito.

Leitura: o mecanismo sozinho não descobre relação sem palavra comum. O ganho vem do conceito abstrato registrado
como entidade com aliases (o que o agente ou o `interprete` propõe) e reaproveitado em todas as pistas seguintes.
Armadilhas na lista são esperadas: candidata não
é relação; o que conta é quantas o agente confirma (medido em `pontua`).

## Protocolo de uma rodada com modelo

> [!WARNING]
> Este protocolo ainda não foi executado.

1. Raiz limpa: copie o kit para uma pasta nova, `holmes.py init relojoeiro "<objetivo do json>"`.
2. Para cada onda, entregue ao agente só as pistas daquela onda, como arquivo `fonte`. Nunca a solução, as
   ligações nem os conceitos.
3. Pedido fixo: "Investigue com o holmes até propor a combinação. Registre o que observar, as questões, as
   hipóteses e as relações." Compacte a conversa entre a onda 2 e a 3 (`/compact`) para medir a retomada.
4. No fim: `python3 -I holmes/aval/aval.py pontua casos/relojoeiro/caso.db`.
5. Rode duas variantes com o mesmo modelo: kit atual e kit anterior (sem `conexoes`, `questao`, `extrai`), 3
   vezes cada. Compare as medianas.

Rubrica (o que `pontua` devolve, e o que é bom):

| Métrica | Bom |
|---|---|
| ligações verdadeiras no grafo | alto |
| armadilhas aceitas no grafo | 0 (cada uma é uma associação falsa) |
| armadilhas rejeitadas explicitamente | alto (evita redescobrir) |
| interpretações registradas como observação | 0 |
| conexões sugeridas sem decisão | baixo no fim |
| leitura final contém a solução | sim |
| testes gastos | baixo, para o mesmo resultado |
| intervenção humana | contar à mão: quantas vezes foi preciso redirecionar |

Avaliação de raciocínio aberto (qualidade das hipóteses rivais, do discriminador escolhido) não é automática:
leia a `cadeia` da hipótese vencedora e julgue com um revisor que não viu a solução.
