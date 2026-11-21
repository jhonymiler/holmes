---
name: conferir-relatorio
description: "Confere na fonte primária o relatório de um subagente, de uma IA externa ou de outra sessão antes de registrá-lo no caso. Use quando um agente devolver resultado, quando o usuário pedir 'confere' ou 'verifica o que ele disse', ou antes de levar qualquer coisa de fora para o registro."
---

# Conferir relatório na fonte

Tudo que vem de fora (subagente, IA externa, outra sessão, terceiros) entra **grau C** até ser
conferido. Agente erra ids, linhas e citações com frequência.

## Passos

1. **Escreva seu julgamento antes de ler o relatório inteiro**, se o ponto for decisivo.
2. **Integridade do que ele editou.** Compare com a versão anterior (`diff`, `git diff`). Conte as
   linhas removidas. Remoção não pedida: mostre ao usuário antes de aceitar.
3. **Cada id citado:** `python3 -I holmes/holmes.py ver <id>`. O texto diz o que o relatório afirma?
4. **Cada citação de documento:** abra a fonte na linha indicada (`sed -n '<a>,<b>p' <arquivo>`).
   Cite o trecho, não a paráfrase do agente.
5. **Cada número ou resultado:** rode de novo o comando ou script que o produziu, ou confira o log.
   Diga se o resultado é **real** (dado do caso) ou **sintético** (dado de teste, simulação, exemplo).
6. **"Nunca testado" / "não está no registro":** `ja "<termo>"` e `busca "<termo>"` com sinônimos.
   Muitas vezes o termo entrou em outro papel. Diga qual.
7. **Fato de fora do repositório** (obra, evento, especificação): sem fonte lida, registre como relato
   externo (`novo fato --natureza relato --origem externo`: grau C, rascunho), nunca como fato vigente nem
   como premissa do caso. Vira premissa só se uma linha precisar assumi-lo, declarado (`novo premissa`).
8. **Grave só o conferido:**
   - conferido na fonte primária: `cita <pedaço> "<t>"`, ou `novo fato "<t>" --origem externo` seguido de `confere <E> "<onde conferiu>"`;
   - não conferido: `novo fato "<t>" --natureza relato --origem externo` (fica rascunho, grau C), ou não grave;
   - pista sem prova: `novo fio "<t>"`;
   - ligações: `liga <de> <tipo> <para>` **só depois** de ver o id impresso pelo `novo`.
9. **Corrija o documento** que o agente editou onde estava errado e diga ao usuário o que foi
   descartado e por quê.

## Saída para o usuário

Tabela curta: item | conferido? | onde | real ou sintético | registrado como (id).
Depois, em frase própria, o que **não** foi conferido e por quê.
