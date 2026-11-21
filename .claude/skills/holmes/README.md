# holmes (mod opcional)

Poda saídas longas do Bash: acima de `HOLMES_LIMITE_SAIDA` (padrão 4000) o inteiro vai para
`/tmp/holmes-saidas/<sessão>/` e o contexto recebe só cabeça, cauda e o caminho.

Os hooks do holmes (mapa na abertura, pistas, diário, cobrança de registro) **não** estão aqui: ficam em
`.claude/settings.json` e funcionam com ou sem este mod, em qualquer cliente. Carrega sozinho de
`.claude/skills/holmes/` onde mods são permitidos; em `claude -p`, use `--plugin-dir .claude/skills/holmes`.
Testes: `claude plugin test .claude/skills/holmes`.
