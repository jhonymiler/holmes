# F3/F5 — Avaliação quantitativa

Sem dado publicado, simule para o caso. Ordem de grandeza com base declarada basta. Sem base
nenhuma, diga que não há avaliação possível. Faça toda conta em código, não de cabeça.

## Razão de verossimilhança (LR)

LR = P(E | H) ÷ P(E | alternativa mais razoável). O LR multiplica **odds**, não probabilidade:
odds = p ÷ (1 − p); odds posterior = odds anterior × LR; p posterior = odds ÷ (1 + odds).
Ex.: p = 0,2 → odds 0,25; LR = 8 → odds 2 → p ≈ 0,67 (não 0,2 × 8).
- Proposições fixadas antes do resultado.
- LRs só multiplicam se as evidências são condicionalmente independentes. Três agentes repetindo a
  mesma leitura, ou duas pistas da mesma fonte, são uma evidência, não três.
- O LR nada diz sobre hipóteses fora do par; as duas podem ser falsas.
- Não transponha: "1 em 10⁹ de ser acaso" não é "1 em 10⁹ de estar errado". Numa busca de N
  candidatos, o prior de cada um é perto de 1/N.

### LR de uma coincidência
1. Escreva E exatamente como observado.
2. P(E | H): perto de 1 se H prevê E; baixa se só permite.
3. P(E | H-nada): simule com o mesmo procedimento que gerou E, incluindo todas as escolhas.
4. Traduza na escala verbal de `padroes.md`.

Exemplo: 8 dígitos hex batendo por acaso têm P = 2⁻³² por tentativa. Após 10⁶ tentativas, LR ≈
4 × 10³ (forte). Após 10⁹, LR ≈ 4 (fraco). Mesmo acerto, valor diferente.

## Taxa de erro do critério de aceitação

- **FPR** = P(aceita | errado). **Sensibilidade** = P(aceita | certo). Meça as duas em casos de
  resposta conhecida, parecidos com o caso real.
- Relate o limite superior de 95%: 0 erros em n → cerca de 3/n.
- **Alarmes falsos esperados = FPR × N.** Se ≥ 1, o critério é só filtro e precisa de segundo
  estágio independente.
- Não infira FPR de buscas reais ("nunca deu falso positivo"): lá a verdade é desconhecida.
- Sem sensibilidade medida, o negativo não encerra a receita.

## Graus de liberdade

- Some log₂ de cada escolha livre: ordem, início, formato, filtro, erros tolerados.
- **Orçamento de evidência:** bits do resultado menos log₂(tentativas, inclusive descartadas e de
  sessões anteriores). Margem ≤ 0 não é evidência.
- **Escolhas de coleta** (versão do texto, recorte, índice 0/1) também contam. Declaradas antes,
  são legítimas; escolhidas depois, são ajuste.
- **Jardim de bifurcações:** uma única análise já infla o falso positivo se os detalhes foram
  decididos olhando o dado. Fixe-os antes ou liste-os e corrija.

## Campeão de busca grande

Busca grande sempre acha um falso muito parecido. Compare o melhor escore com a distribuição do
máximo de N amostras sob ruído (ou p_global ≈ N·p). Candidato vindo do topo exige segunda
verificação antes de virar fato.

## Nulo e positivo

Nulo = embaralhamentos do próprio material. Positivo = sintéticos do tipo suposto, mesmo tamanho.
Achado = fora do nulo e dentro do positivo. Corrija pelo número de lugares em que olhou.

## Correlação

Exija a tabela 2×2 com as 4 contagens. Antes de afirmar relação entre A e B, considere: A→B, B→A,
C causa ambos, coincidência, o dado está errado.

## Calibração

Cada previsão (`--previsao`) leva probabilidade numérica. Ao registrar `resultado`, compare com a
previsão. Acompanhe o Brier (0 perfeito; 50/50 dá 0,25). Sem esse retorno, calibração é autoestima.

## Tempo

Tempo = espaço ÷ (taxa medida × paralelismo), com a taxa medida na máquina, no script e com as
opções reais. Se dá séculos, a hipótese está errada: volte à estrutura. Meça antes de otimizar.
