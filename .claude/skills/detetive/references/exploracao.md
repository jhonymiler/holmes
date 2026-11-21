# Caso parado — exploração

Quando ninguém vai entregar a resposta, esperar pista externa ou repetir variações da última
receita é a forma mais cara de não achar nada.

## Princípio

Os portões protegem afirmações, não tentativas. Tentar é barato; declarar cobertura, linha
encerrada ou achado é que exige F3, controle e revisão.

## Dois regimes

| | Exploração | Cobertura |
|---|---|---|
| Modo | LEITURA ou CIRURGIA | CIRURGIA ou VARREDURA |
| Pode | Testar palpite; hipótese de 1%; inverter premissa central; ler por ângulo novo | O que a F3 declarar |
| Custo | ≤ 10 min de máquina ou 1 h de leitura por tentativa | O que a F3 estimar |
| Registro | `teste ... --exploratorio` + `resultado`, alcance real ("1 tentativa, 10 candidatos") | `teste` completo + revisão |
| Vale como | Pista. Nunca cobertura | Cobertura |
| Promoção | Ideia que encolhe o espaço ou prevê dado novo sobe para F3 | — |

Na dúvida, explore. Negativo de exploração não encerra nada.

## Regras

- Ausência de manifestação de quem produziu o material só pesa contra uma hipótese que previa essa
  manifestação; sem essa previsão, não pesa.
- Não declare bloqueio por falta de fonte externa. Proponha o próximo passo com o que existe.
- Negativo exploratório não fecha nada. Negativo válido fecha a receita no alcance e baixa a confiança no
  tema, sem matá-lo. Diga o que ficou de fora (`--fora`).
- Mantenha pontas soltas visíveis (`novo fio`) e ligadas (`liga`), mesmo sem evidência. Revisite os
  fios do `mapa` antes de escolher o próximo teste.
- Resolveu uma parte: registre por que a resposta funcionou e use isso como guia das pendentes.
- Mostre o raciocínio: o que chamou atenção, que conexões, por que promissoras.

## Estímulos de criatividade (caso parado; heurísticas, não cotas)

1. **Sair do cânone:** gere hipóteses que não venham do registro, de terceiros nem de sessão
   anterior. Liste as premissas herdadas e inverta uma por vez.
2. **Trocar a lente:** trate o material como outra coisa (texto como dado, dado como texto, a dica
   como ruído, o enunciado como errado). Uma tentativa barata por lente antes de descartar.
3. **Cruzar eixos:** combine fatos medidos de frentes diferentes. O espaço promissor costuma estar
   nos cruzamentos tratados como independentes.
4. **Procurar a pergunta:** após receitas falhas em série, pergunte que pergunta está sendo respondida sem
   perceber, antes de ampliar o espaço.
5. **Aceitar o palpite:** teste primeiro, justifique depois. Não descarte por "já tentaram" sem ler
   exatamente o que foi tentado (`ja`).

## Limites que não mudam

- Segurança: Python com `-I` em material baixado; nada sensível sai da máquina.
- Exploração não muda estado de linha encerrada nem apaga registro.
- Acerto aparente passa por controle e `verificador` cego antes de virar achado.

## Anti-paralisia

Se a resposta a "o que testar agora?" for "nada, falta F3" ou "nada, falta a fonte X", está errada.
Escolha a ideia mais barata e diferente das já feitas e rode como exploração. Ou ligue fios soltos,
releia a fonte primária, pesquise referência externa. Pare só por custo real, não por cerimônia.
