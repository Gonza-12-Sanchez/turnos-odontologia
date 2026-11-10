import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, it } from 'vitest'

const configured = fileURLToPath(new URL('../security-fixtures/configured.mjs', import.meta.url))
const inherited = fileURLToPath(new URL('../security-fixtures/inherited.mjs', import.meta.url))

it.each(['worker_threads', 'child_process'])('Tinypool %s ignora filename heredado en run()', runtime => {
  const script = `
    const {default: Tinypool} = await import('tinypool');
    const pool = new Tinypool({filename:${JSON.stringify(configured)}, runtime:${JSON.stringify(runtime)}, minThreads:1, maxThreads:1, execArgv:[]});
    Object.prototype.filename = ${JSON.stringify(inherited)};
    try { console.log(await pool.run(null, {})); }
    finally { delete Object.prototype.filename; await pool.destroy(); }
  `
  const output = execFileSync(process.execPath, ['-e', `(async () => {${script}})().catch(error => {console.error(error); process.exitCode = 1})`], { encoding: 'utf8', timeout: 15_000 })
  expect(output.trim()).toBe('configured-worker')
})
it.each(['worker_threads', 'child_process'])('Tinypool %s no hereda execArgv para crear workers', runtime => {
  const script = `
    const {default: Tinypool} = await import('tinypool');
    process.execArgv = [];
    Object.prototype.execArgv = ['--not-a-real-security-regression-option'];
    let pool;
    try {
      pool = new Tinypool({filename:${JSON.stringify(configured)}, runtime:${JSON.stringify(runtime)}, minThreads:1, maxThreads:1});
      console.log(await pool.run(null));
    } catch (error) { console.log('inherited-options-reached-worker: ' + error.message); }
    finally { delete Object.prototype.execArgv; if(pool) await pool.destroy(); }
  `
  const output = execFileSync(process.execPath, ['-e', `(async () => {${script}})().catch(error => {console.error(error); process.exitCode = 1})`], { encoding: 'utf8', timeout: 15_000 })
  expect(output.trim()).toBe('configured-worker')
})
