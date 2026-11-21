import { expect, test } from 'claude-code/testing'

const bash = (stdout: string) => ({ result: { stdout, stderr: '', interrupted: false } })

// no teste nada responde por baixo do plugin: env, fs e session são simulados aqui
function motor(on: any, gravados: string[]) {
  on('env.get', () => ({ value: undefined }))
  on('session.id', () => ({ value: 'sessao-teste' }))
  on('fs.write', (_: unknown, e: { path: string }) => { gravados.push(e.path); return { value: undefined } })
}

test('saída longa do Bash é podada e o inteiro vai para arquivo', async ($, on) => {
  const gravados: string[] = []
  motor(on, gravados)
  on('tool.call', { tool: 'Bash' }, () => bash('a'.repeat(3000) + 'MEIO' + 'z'.repeat(7000)))
  const r = await $.tool.call({ tool: 'Bash', command: 'cat grande.txt' })
  const out = (r.result as { stdout: string }).stdout
  expect(out.length < 4500).toBe(true)
  expect(out.includes('INTEIRO em /tmp/holmes-saidas/sessao-teste/')).toBe(true)
  expect(out.includes('MEIO')).toBe(false)
  expect(out.endsWith('z')).toBe(true)
  expect(gravados.length).toBe(1)
})

test('saída curta passa intacta', async ($, on) => {
  motor(on, [])
  on('tool.call', { tool: 'Bash' }, () => bash('ok\n'))
  const r = await $.tool.call({ tool: 'Bash', command: 'echo ok' })
  expect((r.result as { stdout: string }).stdout).toBe('ok\n')
})
