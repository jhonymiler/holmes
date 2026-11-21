import type { Register } from 'claude-code'

// Módulo do holmes: só a poda. Os hooks do holmes (abertura, pistas, guarda, pos, fim, pre-compact) ficam em
// .claude/settings.json, que carrega igual no CLI, no VS Code e no app; o mod é opcional e não os repete.
// Poda: saída de Bash acima de HOLMES_LIMITE_SAIDA (padrão 4000; 0 desliga) vai inteira para
// /tmp/holmes-saidas/<sessão>/ e entra no contexto só cabeça + cauda + o caminho. No v1 os resultados
// de ferramenta eram ~75% da janela e o raciocínio ~7%.

export const register: Register = on => {
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const r = await next(e)
    if (r.deny !== undefined) return r
    try {
      return await poda($, r)
    } catch {
      return r // a poda nunca estraga o resultado da ferramenta
    }
  }).catch(($, e, next) => next(e))
}

async function poda($: any, r: any) {
  const limite = Number((await $.env.get('HOLMES_LIMITE_SAIDA')) ?? '') || 4000
  if (!limite) return r
  const corta = async (txt: string, nome: string) => {
    const arquivo = `/tmp/holmes-saidas/${await $.session.id()}/${Date.now()}-${nome}.txt`
    await $.fs.write(arquivo, txt)
    const cabeca = Math.floor(limite * 0.7)
    return txt.slice(0, cabeca) + `\n\n… [holmes podou ${txt.length - limite} caracteres do meio ` +
      `(${txt.length} no total). INTEIRO em ${arquivo}: use grep/sed nele em vez de repetir o comando.] …\n\n` +
      txt.slice(-(limite - cabeca))
  }
  const res = r.result && typeof r.result === 'object' ? (r.result as Record<string, unknown>) : undefined
  if (res?.isImage) return r
  if (res && !r.isError) {
    const novo: Record<string, unknown> = { ...res }
    let podou = false
    for (const [campo, v] of Object.entries(res))
      if (typeof v === 'string' && v.length > limite) { novo[campo] = await corta(v, campo); podou = true }
    return podou ? { ...r, result: novo } : r
  }
  // caminho de erro: `result` vem como string; um hook só pode responder no formato do esquema do Bash
  if (typeof r.result === 'string' && r.result.length > limite)
    return { result: { stdout: await corta(r.result, 'erro'), stderr: '', interrupted: false } }
  return r
}
