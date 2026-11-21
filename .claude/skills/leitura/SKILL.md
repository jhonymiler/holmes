---
name: leitura
description: "Leitura de sentido: interpretar pistas, fontes e saídas de teste além da literalidade, em camadas (literal, figurada, alusão, função, subliminar, ausência), e ler o conjunto dos resultados para entender que história o caso conta e onde se está nela. Use ao ler uma pista ou fonte nova, ao registrar um resultado, quando o mapa pedir LEITURA DE CONJUNTO, depois de negativos repetidos, ao traduzir uma ideia em teste, ou quando o usuário perguntar 'o que isso significa?', 'em que parte estamos?', 'faz sentido?'. Gatilhos: significado, sentido, interpretar, metáfora, alusão, subliminar, narrativa, história, simbólico, literal demais, o que o autor quis dizer."
---

# Leitura de sentido

O material de um caso foi feito por alguém que comunica: um autor de enigma, quem redigiu um contrato,
quem montou uma planilha. Quase nunca a informação é só a literalidade das palavras ou dos bytes: ela
aponta para outras coisas, por imagem, alusão, duplo sentido e omissão. O erro mais caro do v1 foi ler
tudo como mecânica (palavra como senha, livro como lista de termos, saída como contagem) e só ver
sentido quando o usuário cobrava. O erro oposto também custa: achar mensagem onde há coincidência.
Nem todo material tem segundo sentido; a leitura literal e contextual é sempre a base.

## As camadas (literal e função sempre; as outras são lentes, quando o material e a questão justificarem)

| Camada | Pergunta |
|---|---|
| Literal | O que o texto ou a saída diz, palavra por palavra? Leia inteiro, não a linha que bateu. |
| Figurada | É metáfora, alegoria, imagem? O que ela representaria se não fosse literal? |
| Alusão | A que obra, cena, personagem, ideia ou acontecimento ela aponta? Ache a fonte e leia o trecho. |
| Função | O que ela faz no caso: instrui, identifica, marca etapa, dá nome, despista? |
| Subliminar | Jogo de palavras, homofonia, palavra escondida (acróstico, iniciais), duplo sentido, número que é índice, o que foi trocado em relação ao original citado (o diff costuma ser a mensagem). |
| Ausência | O que deveria estar ali e não está? O que o autor evitou dizer? |

Registre cada leitura que importar: `novo fato "<leitura>" --natureza interpretacao --origem agente`, ligada
à pista (`liga E.. sobre <pista>`). Se a leitura liga duas pistas, é `conexao` candidata; se nomeia um
conceito que aparece em várias, registre-o como entidade com aliases (`references/extracao.md`, passo D). Leitura sua é legítima: não a rebaixe por ser sua, nem a promova a fala
do autor.

## Ler a saída de um teste

1. Olhe a saída como texto e forma antes de contar: que palavra, que padrão, que número apareceu? Ecoa
   algo das fontes ou da LEITURA ATUAL?
2. Depois o número: nulo, controle, alcance.
3. `resultado <T> ... --sentido "<o que isto diz no contexto>"` (ou `"nenhum: <por quê>"`, ou deixe pendente
   para a leitura de conjunto). Sentido percebido é hipótese, não evidência: estime quão provável seria
   ver algo assim por acaso, contando as escolhas livres (`quantitativo.md`). Sem essa conta, não é acaso
   nem achado: é pista, registrada e confrontada com uma rival.

## Do conceito à operação

Pergunte o que referencia o quê, não qual é o verbo. Monte a correspondência antes de operar:
personagem ↔ peça, relação ↔ relação, acontecimento ↔ transformação.

1. Escreva o conceito (a hipótese) e o que o derrubaria (`--refuta-se`).
2. Liste formas de traduzi-lo em operação de famílias diferentes, não variações de uma (2 ou 3 costumam
   bastar; é heurística, não cota).
3. Escolha a que a fonte mais determina. Conte as escolhas livres: cada uma é um grau de liberdade.
4. Um 0 válido fecha aquela forma e baixa a confiança no conceito (`prob`). O conceito cai quando o critério
   de refutação é atingido; negativos que se acumulam não o deixam intacto.

## Leitura de conjunto (quando o mapa pede, ou depois de um túnel)

1. `ver` dos últimos resultados: leia os `sentido` juntos, não um por um.
2. Pergunte: somados, o que contam? Que leitura nenhum deles contradiz? O que surpreendeu?
3. Onde estamos na história do caso? O que ela prevê como próximo passo?
4. Liste leituras alternativas do todo, ao menos uma fora da lente usada até agora.
5. Se o quadro mudou: `holmes.py leitura "<até 800 caracteres>" --sustenta E.. --rival H.. --questao Q..
   --motivo "<o que mudou e por quê>"`. Se não mudou, diga por quê e deixe a leitura como está.

## Fechar o porquê

Quando algo resolve, registre por que a correspondência funcionou (a relação abstrata entre a pista e
a solução). É ela que guia o próximo passo; a receita que deu certo raramente se repete igual.

## Armadilhas

- **Literalidade:** testar a palavra da pista como senha ou byte em vez de perguntar o que ela significa.
- **Fonte tratada como string:** varrer um livro por palavra-chave e dá-lo como esgotado. Leia o trecho
  inteiro e resuma o conceito que ele explica.
- **Descartar sentido por p não calculado:** sem a conta, a coincidência fica como pista, não como ruído.
- **Conexão espúria:** duas pistas com tema parecido ("dualidade", "tempo") ligam quase tudo. Relação
  vale quando prevê algo que a rival (tema genérico, acaso, mesma fonte) não prevê.
- **Narrativa coerente demais:** cada elo a mais torna a história menos provável, não mais.
- **Lente única:** ler tudo pela mesma obra ou teoria. Uma das 3 leituras alternativas é de fora dela.
- **Tema sem ponte:** associação livre virando teste. A ponte entre fonte e operação tem de ser escrita.
- **Leitura promovida a achado:** sem verificação independente, leitura é pista ou hipótese.
- **Esquecer o papel do objeto:** um objeto do caso tem papel na história (quem ele é), não só valor.

## Parceiros

Para leitura de sentido, um segundo leitor ajuda: o agente `interprete` (leitura independente, sem ver a
sua) ou outro modelo via briefing. O que voltar entra grau C até conferido na fonte.
