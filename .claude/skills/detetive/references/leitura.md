# F1 — Leitura

Obrigatória antes de abrir uma família nova de testes. Na retomada, confira a leitura anterior na
fonte; resumo de outro agente não basta.

## Ordem de exame

1. **O que já foi feito:** `ja "<termo>"`. Evita refazer.
2. **Fonte bruta.** Escreva a leitura própria, com confiança, antes dos itens 4 e 5.
3. **Metadados e vestígios da ferramenta** que produziu o material. Que marca ela deixaria?
4. **Interpretações anteriores**, suas e de terceiros. Cada mudança vira linha "mudei X porque vi Y".
5. **Soluções de terceiros e formato esperado**, por último. O que só foi visto depois delas pesa menos.

Resto do material: menos enviesante e mais objetivo primeiro; irrelevante fora.

## O que registrar por item

Leia unidades de sentido completas (parágrafo, seção, tabela inteira). Busca de palavra não é leitura.

- **Fonte e situação:** onde está, quem produziu, para quem, em que contexto. `novo fato --origem fonte`.
- **Mensagem:** o que o leitor é levado a entender, em palavras suas.
- **Referentes e função:** a que aponta? Identifica, instrui, marca uma etapa?
- **Outra leitura:** uma que muda o sentido ou o referente, não só o formato.
- **Discriminador:** que observação separaria as leituras? Sem nenhum, registre a lacuna (`novo fio`).
- **Ponte para a operação:** o que a fonte determina e o que você acrescentou. Conte as escolhas livres.

**Condição para testar:** ponte explícita entre fonte e operação, um teste que discrimine e
controle. Sem ponte, continue lendo: a associação de tema não substitui a ponte, mas é o começo de uma
leitura, que se registra como hipótese (skill `leitura`, camadas e leitura de conjunto).

Não presuma intenção em todo detalhe: pode ser acidente (H-artefato).

## Dois planos

Todo resultado (número, saída, padrão) se lê em dois planos no mesmo passo:

1. **Estatístico:** nulo, controle, alcance.
2. **Sentido:** o que o resultado diz no contexto da fonte. O texto do produtor costuma descrever
   como ler o próprio material.

Os planos conversam: sentido não se descarta só porque o p não foi calculado, e sentido percebido
não vira evidência sem a conta de quão provável ele seria por acaso, com as escolhas livres. Registre
os dois: `resultado ... --sentido`.

Registre as duas medidas: quão raro é sob acaso e quão plausível é sob a hipótese. P pequeno de
acaso não prova a hipótese; coincidência com sentido não é descartada só por isso. Classifique:
pista, hipótese de trabalho ou achado.

Estatística sozinha não separa sinal codificado de ruído. Negativo estatístico diz "sem estrutura
detectável", nunca "é ruído".

## Ferramentas de leitura

- **Segunda leitura independente** de todo dado extraído por ferramenta (OCR, parser, LLM).
- **Todas as versões:** outra cópia, outra resolução, outro método de extração. Traço fino só vale
  se aparece em todas.
- **Surpresas:** registre o que não casou com a expectativa (`novo fio`). Várias surpresas indicam
  que o entendimento está errado.
- **Inventário de consumo:** cada elemento da fonte e a etapa que o explica. Elemento sem uso
  indica solução incompleta ou chamariz.
- **Solução de terceiros:** qual a causa rival? que dado foi omitido? a evidência admite outra conclusão?
- **Refinar a pergunta:** o que contaria como resposta? Há premissa escondida na pergunta?
- **Recorte declarado:** em todo script, imprima o que foi tratado como dado e como foi segmentado.

## Após negativos repetidos

Volte aos referentes e às premissas antes de ampliar a mesma família. O negativo encerra o método
testado, não o significado da fonte.
