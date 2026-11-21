# F2 — Hipóteses

## Gerar

- Rivais de verdade, não cota. Considere, quando forem plausíveis: **H-nada** (acaso, erro de
  transcrição), **H-mundano** (índice 0/1, encoding, fuso, unidade, off-by-one), **H-adversária**
  (engano), **H-erro** (o produtor errou) e, para "detalhe intencional", **H-artefato** (acidente).
  Hipótese inventada para fechar número é ruído na matriz.
- Questão ainda sem explicação plausível fica aberta como `questao` (lacuna), sem hipótese forçada.
- Inclua hipóteses de terceiros e de sessões anteriores, com crédito.
- Gere antes de mergulhar no detalhe. Gerar e avaliar são passos separados.
- Registre o teste que cada hipótese sugere, não só o da favorita.
- Registro: `novo hipotese "<t>" --pai <frente>`; rivais ligadas com `liga <a> contradiz <b>`.

## Prior pela visão de fora

Antes dos detalhes: "de N tentativas deste tipo, quantas acertaram?" Esse é o prior. Com muitas
linhas refutadas, o prior de "a próxima acerta" é baixo.

## Premissas

Para cada premissa que a linha exige:
- relevância 0–2 (2 = a linha cai sem ela) × suporte 0–2. Prioridade: relevância alta, suporte baixo.
- "O que veríamos se fosse verdade, e por que não vemos?"
- Imagine que uma fonte perfeita disse que está errada. Construa o cenário.
- P(A e B) = P(A) × P(B | A). Só vira produto simples se as premissas forem independentes; premissas
  que vêm da mesma fonte ou do mesmo raciocínio costumam andar juntas. Cinco independentes a 80% dão 33%.
- Revise as premissas no início e antes de concluir.

Premissas de identidade ("é o mesmo arquivo"), tempo e completude ("é o log inteiro") quebram mais.

## ACH — como registro, não como oráculo

ACH (análise de hipóteses concorrentes) não melhora a acurácia sozinha; serve para achar evidência
que distingue e deixar o raciocínio auditável.

1. Linhas = evidências, premissas e ausências. Colunas = hipóteses.
2. Preencha por linha: "se H fosse verdadeira, qual a chance de ver isto?" — C (consistente),
   I (inconsistente), N (neutro), ? (não sei).
3. Linha C em todas as colunas não distingue: sai do ranking, mas fica registrada.
4. Coluna extra: quão fácil seria forjar o item?
5. Leia por coluna. Ranqueie por inconsistências. Só sai a refutada, com I documentado.
6. Se discorda da matriz, falta uma linha. Acrescente; não anule em silêncio.
7. Converta em probabilidades. Somam 1 (com "outra") só se as hipóteses forem mutuamente exclusivas;
   leituras que podem ser verdade juntas (função narrativa e operacional) têm probabilidades próprias.
8. Julgamento decisivo: 2 ou 3 agentes independentes estimam sem se ver; use a média.
9. Sensibilidade: se o I decisivo estiver errado, a conclusão muda? Confira-o por outra via.
10. Escreva antes o que, se aparecer, muda a conclusão.

## Engano

Suspeite quando: a análise depende de um único item; a informação-chave chegou na hora certa;
aceitá-la obriga a mudar uma premissa central; quem produziu o material vê o que você faz.

- Motivo, canais, risco e custo do engano.
- Já houve engano antes desta fonte?
- A fonte é manipulável? Acesso direto ou de segunda mão?
- A cadeia inteira foi checada, inclusive transcrições? Há confirmação por canal que o produtor
  não controla?

Engano fica como hipótese viva, nunca como explicação de bolso.

## Inferência forte e premortem

- Todo teste responde: que hipótese ele exclui? Teoria que explica qualquer resultado não explica nenhum.
- Resultado novo → 2 ou 3 explicações → controle que as separa.
- **Premortem:** antes de rodar, escreva "terminou sem achado, ou o achado era falso. Por quê?"
  As respostas viram testes de sanidade.
- Consenso antigo pede advogado do diabo (agente `ceticismo`). Depois, confira a taxa-base.
- Remendo ad hoc multiplica probabilidades: cada um torna a hipótese menos provável.

## Antes de coletar mais

Classifique o que espera obter: mais detalhe do mesmo (só aumenta confiança), variável nova
(raramente muda), valor novo de variável crítica ou modelo novo (os únicos que mudam a acurácia).

## Em aberto

Duas hipóteses com inconsistências comparáveis: "em aberto, e eis o teste que decidiria", com
probabilidades. Escolher a menos feia é o erro confiante mais comum.
