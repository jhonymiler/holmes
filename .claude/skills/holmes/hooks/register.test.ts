import { expect, test } from 'claude-code/testing'

const bash = (stdout: string) => ({ result: { stdout, stderr: '', interrupted: false } })

// in the test nothing answers beneath the plugin: env, fs and session are simulated here
function engine(on: any, written: string[]) {
  on('env.get', () => ({ value: undefined }))
  on('session.id', () => ({ value: 'test-session' }))
  on('fs.write', (_: unknown, e: { path: string }) => { written.push(e.path); return { value: undefined } })
}

test('long Bash output is trimmed and the whole goes to a file', async ($, on) => {
  const written: string[] = []
  engine(on, written)
  on('tool.call', { tool: 'Bash' }, () => bash('a'.repeat(3000) + 'MIDDLE' + 'z'.repeat(7000)))
  const r = await $.tool.call({ tool: 'Bash', command: 'cat big.txt' })
  const out = (r.result as { stdout: string }).stdout
  expect(out.length < 4500).toBe(true)
  expect(out.includes('IN FULL at /tmp/holmes-outputs/test-session/')).toBe(true)
  expect(out.includes('MIDDLE')).toBe(false)
  expect(out.endsWith('z')).toBe(true)
  expect(written.length).toBe(1)
})

test('short output passes intact', async ($, on) => {
  engine(on, [])
  on('tool.call', { tool: 'Bash' }, () => bash('ok\n'))
  const r = await $.tool.call({ tool: 'Bash', command: 'echo ok' })
  expect((r.result as { stdout: string }).stdout).toBe('ok\n')
})
