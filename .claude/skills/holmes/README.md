# holmes (optional mod)

Trims long Bash outputs: above `HOLMES_LIMITE_SAIDA` (default 4000) the full output goes to
`/tmp/holmes-saidas/<session>/` and the context receives only the head, the tail and the path.

The holmes hooks (map at session start, clues, diary, reminders to record) are **not** here: they live in
`.claude/settings.json` and work with or without this mod, in any client. It loads by itself from
`.claude/skills/holmes/` where mods are allowed; in `claude -p`, use `--plugin-dir .claude/skills/holmes`.
Tests: `claude plugin test .claude/skills/holmes`.
