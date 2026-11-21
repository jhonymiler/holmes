# F0 — Coleta, custódia e fontes abertas

## Princípios

- **Colete antes de analisar.** Página, post e arquivo hospedado somem. Capture primeiro.
- Do mais volátil ao menos volátil: página viva, snapshot, material de terceiros.
- Analise uma cópia. Abrir e salvar num editor, converter encoding ou recomprimir altera o material.
- Arquivo baixado não é confiável: pasta própria e vazia, Python com `-I`, scripts fora dela.
- Registre horários em UTC. Data de modificação informada pelo servidor é relato, não medida.

## Registro por item

Indexe com `fonte <caminho> --titulo "<t>"`. No resumo ou num fato ligado, guarde:

| Campo | Por quê |
|---|---|
| URL ou origem exata + método (curl, navegador, snapshot) | Reprodução |
| UTC | Ordem dos eventos |
| Cabeçalhos relevantes (data, tamanho, ETag) | "É o mesmo arquivo que outros viram?" |
| sha256 como recebido | Lacre |
| HTML-fonte + captura, se for página | O mínimo para reconstruir |
| Procedência: original / montado por nós / terceiros | Saber o que é primário |
| Cópias independentes com hashes comparados | Autenticidade por outro canal |
| Derivados: hash do pai, operação, ferramenta | Toda transformação registrada |

## Arquivos da web

- Snapshot de arquivo é composto: imagens e scripts podem ter datas diferentes da página. "Estava
  na página no dia X" exige a data de cada recurso.
- Arquive em dois serviços e baixe os originais.
- Diga "primeira cópia encontrada", nunca "primeira cópia", com o alcance da busca.

## Verificar a fonte

- Proveniência: quem publicou primeiro, quando, a partir de quê.
- Histórico, independência, especificidade, contemporaneidade.
- Conteúdo: identificadores únicos, dado verificável, consistência interna, corroboração externa.
- **Relato circular:** dez posts citando o mesmo print são um print.
- Anacronismo: formato, software ou referência que não existia na data alegada.
- Evidência que resolve tudo e chegou na hora certa é suspeita.
- Canal assinado: se a fonte tem assinatura ou domínio oficial, classifique cada item por estar ou
  não assinado.

## Graduar

Grau no registro: `--grau A|B|C` (A = conferido na fonte primária; B = fonte confiável não
conferida; C = relato, agente ou externo não conferido). Para análise fina, use Admiralty
(`padroes.md`).

- Avalie a informação antes de olhar quem a produziu.
- A nota da fonte vem só do histórico. Sem histórico não é "ruim", é "sem base".
- Gradue também ferramentas: script com bug conhecido vale menos que instrumento validado de ponta a ponta.

## Citação

Toda afirmação-chave aponta a fonte mais original com identificador recuperável (caminho + sha256,
ou URL + data de acesso + snapshot). Post citado é arquivado no momento da citação.

## Disciplina

Registre a busca que não achou nada, com os termos e onde procurou: é resultado negativo com alcance.
Não use conta pessoal em fonte aberta.
