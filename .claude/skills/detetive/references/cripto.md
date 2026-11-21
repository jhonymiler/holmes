# Módulo opcional — casos com cifras

Use só quando o caso envolve texto cifrado, codificação ou dado escondido.

## Codificação ou cifra?

Codificação não esconde nada: base64, hex, binário, base58, URL-encoding, ASCII decimal, Morse.
Descasque todas as camadas antes de suspeitar de criptografia. Identifique o tipo de arquivo pelo
cabeçalho, não pela extensão.

## Diagnóstico de cifra clássica

- **Classe (100 letras, inglês):** vogais AEIOUY 33–47; DNRST 28–42; BCFGHLMPVW 17–31; JKQXZ 0–3.
  Tudo na faixa → transposição; fora → substituição.
- **IC** = Σ nᵢ(nᵢ−1)/(N(N−1)). Inglês ≈ 0,067; aleatório ≈ 0,0385. Não muda com substituição
  simples: serve para achar transposição ignorando a substituição.
- **Mono × poli:** distribuição com picos → um alfabeto; achatada → vários. Kasiski dá o período.
- **Palavra provável:** só se motivada por circunstância externa. Cada palavra tentada conta como tentativa.
- **Frequência não vê tudo:** acróstico, indexação e grade com nulos não deixam sinal estatístico.
- **Cifra de bloco** (tamanho múltiplo de 16, entropia alta): sem a chave não há criptanálise.
  Procure a chave no material.
- **Esteganografia:** bits menos significativos, canais de cor, metadados, dados após o fim do
  arquivo, espaços no fim de linha, versões diferentes da mesma imagem.
- **Kerckhoffs:** em enigma, o autor quer que o método seja achado. Procure a dica do método.

## Unicidade

U = H(K) / D. Inglês D ≈ 3,2 bits/letra; substituição simples U ≈ 28 letras. Abaixo de U, chaves
falsas dão texto plausível e nenhum scorer decide. Use o D do critério que o scorer mede, não o da
língua. H(K) inclui as escolhas do analista.

## Scorers

- Monogramas e IC: robustos, pouco seletivos, escores falsos em texto curto.
- n-gramas maiores e dicionário: seletivos, pouco robustos.
- Meça antes de confiar: sintéticos com chave conhecida, erro injetado, curva escore × erro no
  comprimento do alvo, taxa de falsos com chaves aleatórias.
- Nunca treine o scorer no material do caso.

## Critérios de aceitação típicos

| Critério | Falso positivo por candidato | Papel |
|---|---|---|
| Hash ou identificador igual ao alvo | desprezível | Confirmação; erro dominante é técnico |
| Checksum curto (4 bits) | 1/16 | Filtro |
| Checksum de 8 bits | 1/256 | Filtro |
| Padding PKCS#7 após AES-CBC | ≈ 1/255 | Filtro; em 10⁹ tentativas, milhões de falsos |
| Texto "plausível" | medir no comprimento do alvo | Filtro, nunca confirmação |

O critério final precisa de FPR × N muito abaixo de 1. Senão, encadeie um segundo estágio independente.

## Erros humanos

Senha montada à mão pode ter erro. Reparos enumeráveis: símbolo ilegível, caractere faltando,
caractere sobrando. Tolerar 1 erro multiplica o espaço por cerca de comprimento × alfabeto. Aceite
o erro só se um mecanismo único explica todos.

## Executar uma busca

- Controle com poder medido em cada execução (`validacao.md`).
- O critério precisa enxergar tudo que a hipótese pode produzir (texto legível e binário).
- Espaço declarado = código executado.
- Cópia local de função compartilhada é defeito. Registre o instrumento com `instrumento`.
- Checkpoint em busca longa; log sem buffer.
- Reprocessar saída antiga com critério mais seletivo é permitido; repetir a mesma busca, não.
- Erro de software é sistemático: rodar de novo não acha bug; segundo método acha.
