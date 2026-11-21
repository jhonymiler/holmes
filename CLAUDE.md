# Projeto de investigação (holmes 2.0)

## Onde está cada coisa
- `holmes/holmes.py` — CLI do registro. Um banco por caso em `casos/<caso>/caso.db`. Rode sempre com
  `python3 -I holmes/holmes.py <cmd>` a partir da raiz.
- `casos/<caso>/` — `CASO.md` (o que é o caso, ≤ 2 KB, à mão), `MAPA.md` (gerado, não editar),
  `fontes/` (originais, só leitura), `scripts/`, `saidas/` (logs), `notas/` (prosa livre, fora do índice).
- `holmes/corpus.py` — o material (chats, documentos, livros) em `corpus/corpus.db`. Busque nele
  (`busca`, `janela`) em vez de abrir arquivos grandes; cite trechos com `holmes.py cita <pedaço>`.
- `.claude/rules/constituicao.md` — regras de toda sessão. `.claude/skills/detetive/` — o método.
  `.claude/skills/leitura/` — leitura de sentido. Hooks: `.claude/settings.json`. Modelo de dados: `MODELO.md`.
- `.holmes/` — estado local: caso ativo e diário do raciocínio por sessão (gerado pelos hooks).

## Como começar
1. A abertura da sessão já injeta o `mapa` do caso ativo. Leia-o; não leia documentos inteiros.
2. Trocar de caso: `holmes.py usa <caso>`. Caso novo: `holmes.py init <caso> "<objetivo>"`.
3. Antes de testar: `holmes.py ja "<termos>"`. Detalhe: `ver <id>`; no que se apoia: `cadeia <id>`; o que fazer e por quê: `proximo`.
4. Pista, fonte e saída se leem pelo sentido, não só pela letra (skill `leitura`). A `LEITURA ATUAL` do mapa é
   a história que o caso parece contar; reescreva-a com `holmes.py leitura` quando o mapa pedir.

## Ambiente desta máquina
## Regras do projeto
- Arquivo baixado é não confiável: Python com `-I`, nunca executar o que veio de fora.
