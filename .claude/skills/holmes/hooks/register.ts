import type { Register } from 'claude-code'

// holmes module: trimming only. The holmes hooks (start, prompt, guard, post, stop, pre-compact) live in
// .claude/settings.json, which loads the same in the CLI, in VS Code and in the app; the mod is optional and does
// not repeat them. Trimming: Bash output above HOLMES_OUTPUT_LIMIT (the old HOLMES_LIMITE_SAIDA is read when it
// is unset or empty; 4000 when the value is not a nonzero number) goes in full to /tmp/holmes-outputs/<session>/ and only head + tail + the path
// enter the context. In v1, tool results were ~75% of the window and the reasoning ~7%.

export const register: Register = on => {
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const r = await next(e)
    if (r.deny !== undefined) return r
    try {
      return await trim($, r)
    } catch {
      return r // trimming never spoils the tool's result
    }
  }).catch(($, e, next) => next(e))
}

async function trim($: any, r: any) {
  const raw = String((await $.env.get('HOLMES_OUTPUT_LIMIT')) || (await $.env.get('HOLMES_LIMITE_SAIDA')) || '')
  const limit = raw === '' || isNaN(Number(raw)) ? 4000 : Number(raw) // an explicit 0 turns trimming off
  if (!limit) return r
  const cut = async (txt: string, name: string) => {
    const file = `/tmp/holmes-outputs/${await $.session.id()}/${Date.now()}-${name}.txt`
    await $.fs.write(file, txt)
    const head = Math.floor(limit * 0.7)
    return txt.slice(0, head) + `\n\n… [holmes trimmed ${txt.length - limit} characters from the middle ` +
      `(${txt.length} in total). IN FULL at ${file}: use grep/sed on it instead of repeating the command.] …\n\n` +
      txt.slice(-(limit - head))
  }
  const res = r.result && typeof r.result === 'object' ? (r.result as Record<string, unknown>) : undefined
  if (res?.isImage) return r
  if (res && !r.isError) {
    const updated: Record<string, unknown> = { ...res }
    let trimmed = false
    for (const [field, v] of Object.entries(res))
      if (typeof v === 'string' && v.length > limit) { updated[field] = await cut(v, field); trimmed = true }
    return trimmed ? { ...r, result: updated } : r
  }
  // error path: `result` comes as a string; a hook can only answer in the Bash schema's format
  if (typeof r.result === 'string' && r.result.length > limit)
    return { result: { stdout: await cut(r.result, 'error'), stderr: '', interrupted: false } }
  return r
}
