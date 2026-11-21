# O time

Definições em `.claude/agents/*.md`.

## Orçamento

- Especialistas em Sonnet ou Haiku, esforço medium no máximo. Escopo bem definido compensa modelo menor.
- Todo subagente carrega `CLAUDE.md` e `.claude/rules/` inteiros: mantenha-os curtos.
- Subagente não lança subagente.

## Quem faz o quê

| Agente | Modelo | Fase | Entrega | Não faz |
|---|---|---|---|---|
| `arquivista` | haiku | F0 | Coleta isolada, hashes, fontes indexadas | Interpretar |
| `pesquisador` | sonnet | F1, F2 | Fontes externas lidas, trechos com localizador e grau | Concluir sobre o caso |
| `analista` | sonnet | F1–F3 | Leitura, hipóteses, pré-avaliação | Código de busca |
| `engenheiro` | sonnet | F4 | Script com controle, execução registrada | Julgar o próprio resultado |
| `revisor` | sonnet | F4 | Revisão do código e da cobertura | Editar o código revisado |
| `verificador` | sonnet | F6 | Verificação cega e reprodução | Ler o registro ou saber o suspeito |
| `ceticismo` | sonnet | F5, F7 | Ataque a negativo e a conexão antes de virar definitivo | Registrar |
| `interprete` | opus | F1, leitura de conjunto | Leituras alternativas, conceitos que ligam pistas, conexões candidatas | Rodar teste; confirmar relação |

Integrador é o coordenador: só ele confronta as entregas com o mapa, decide o que registrar e reescreve a
leitura. Intérprete e cético só valem a chamada em julgamento decisivo, não a cada observação.

Revisão cruzada: `revisor` revisa `engenheiro`; `verificador` julga candidatos; o coordenador confere
na fonte todo relatório antes de registrar; o usuário revisa o coordenador.

## Quando delegar

- **Delegar:** frentes independentes de tamanho real (lançadas juntas); leitura maior que um
  contexto; independência deliberada (revisor, verificador, ceticismo); trabalho barato e conferível.
- **Não delegar:** o que cabe em poucas chamadas; cadeia dependente que cabe num contexto;
  verificar o próprio trabalho.

## Briefing (o subagente não herda a conversa)

Inclua sempre:
1. O caso e o pedido de rodar `python3 -I holmes/holmes.py mapa` antes de agir.
2. O modo de trabalho (LEITURA, CIRURGIA ou VARREDURA) e o custo máximo.
3. Os ids de entrada (`ver <id>`) e a saída esperada.
4. O que já está encerrado. Antes de dizer "novo" ou "já coberto": `ja "<termo>"`, citando ids.
5. Negativo refuta só a receita testada; declarar o que ficou de fora.
6. Não declarar bloqueio por falta de fonte externa; propor o próximo passo.
7. Devolver as relações que achou como candidatas (de, para, relação, por quê, rival, discriminador), para o
   coordenador avaliar e gravar com `conexao`; nunca como `liga` direta.
8. Formato de entrega: resultado, real ou sintético, o que conferiu na fonte, o que não conferiu.

Para `verificador`: nunca o veredito nem a hipótese favorita.
Para `ceticismo`: a alegação, o script, o log e o registro, sem defesa dela.

## Depois

- Não refaça o trabalho do agente. Confira o relatório na fonte (skill `conferir-relatorio`).
- Resultado de agente ou IA externa entra `--origem agente|externo --grau C` até conferido.
- Fato de fora do repositório que o agente afirme entra como relato externo (grau C, rascunho), não como
  premissa do caso, até haver fonte lida.

## Sigilo e segurança

- Segredo encontrado (credencial, chave, dado pessoal): grave em arquivo local do caso e avise só
  o usuário. Nunca publique nem envie a terceiros.
- Arquivo baixado não é confiável: pasta própria e vazia, Python com `-I`, scripts fora dela.
- Respeite os limites de CPU e memória da máquina declarados no `CLAUDE.md`.
