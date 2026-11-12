# C10 Frontend Verification

## Scope And Gates

2026-11-09: explicit user apply approval, test mode only; ownership limited to
frontend/ and C10 artifacts. No backend changes or backend test execution while
C09 agent works concurrently. C05/C07 archived per roadmap and proposal.
Approved seams from this request: HTTP client, accessible DOM/navigation,
browser/service worker. Catalog HTTP and real backend/browser acceptance remain
delegated/pending; HTTP fixtures below are not integration acceptance.

## Baseline

Before manual edits, `npm.cmd test`, `npm.cmd run lint`, and
`npx.cmd --no-install tsc -b` could not run because node_modules was absent.
This is environment setup, not a RED test. `npm.cmd ci --ignore-scripts`
installed the existing lockfile (400 packages). Then, before edits:

| Command (frontend cwd) | Exit | Result |
| --- | --- | --- |
| npm.cmd test | 0 | Vitest 3.2.4, 3/3 client tests |
| npm.cmd run lint | 0 | 0 warnings/errors |
| npx.cmd --no-install tsc -b | 0 | clean |
| npm.cmd audit --json | 1 | 12 preexisting advisories: 3 low, 6 moderate, 1 high, 2 critical |

No failing baseline test was suppressed/fixed. Backend baseline deliberately
not executed here: separate backend ownership; task 1.3 remains partially pending.

## Dependency Review

Independent npm lockfile; npm 11.17.0. Persist ignore-scripts=true in frontend
before adding packages; clean installs retain that policy. Existing esbuild and
native optional packages run successfully without lifecycle scripts.
React 18/Vite 6 retained. Router 6.30.6 supports React >=16.8; Testing Library
16.3.0 supports React 18/19 and DOM 10; jsdom 26 supports Node 18+.
Only public npm packages from established maintainers, exact new versions,
no dependency lifecycle scripts approved. Browser binary installation is an
explicit separate test-tool command, not blanket npm lifecycle approval.

Audit is not a release sign-off: Vite dev server high findings and Vitest UI/
worker critical findings predate C10. Only local trusted test sources and
loopback servers; no Vitest UI or network-exposed dev server. Broad toolchain
remediation is deferred for review before release (review date 2026-11-16).
No production deployment is authorized.

## TDD Evidence

Each row will record actual executed RED/GREEN cycles, independent cases and
limitations. Setup failures do not count as RED. Tests mock only HTTP boundaries.

| Task | Test / Seam | Baseline | RED | GREEN | Triangulation / Refactor |
| --- | --- | --- | --- | --- | --- |
| 3.1 | client.test.ts HTTP | 3 pass | 20:22:05 exit 1, 10 failures: missing body/PATCH/credentials, unsafe generic message | 20:22:28 exit 0, 13 pass | 409/402, 422 string/list, 2 non-JSON bodies, confirmar/cancelar, login/refresh; original 3 retained |
| 3.2/3.3 | session.test.ts HTTP/session | no session | 20:23:19 exit 1, 5 assertions fail against empty Session (earlier missing import not counted) | 20:23:55 exit 0, 5 pass | 401 anonymous vs 503 unavailable; parallel restore once; login+me, logout failure clears; no write retry on 401 |
| 3.2/4.1 | App.test.tsx accessible DOM | Home only | 20:24:41 exit 1, 11 failures missing login/register/guard/404 | 20:26:32 exit 0, 11 pass | 2 protected paths, 3 hostile returnTo, 401/429, registration no login/password, 2 unknown paths, staff denied; label description moved outside label after initial run |
| 4.2/5.1 | App.test.tsx DOM+HTTP | route placeholder | 20:27:28 exit 1, 8 failures missing treatment, catalog states, slots/reservation | 20:29:16 exit 0, 19 total pass | 2 treatments, empty/failure catalog, preserve selection without POST, 409 with/without alternatives, 201 vs lost response; fixed parameterized fixture wrappers (test harness error not RED) |
| 5.2/5.3 | App.test.tsx DOM+HTTP | no checkout/return screen | 20:30:15 exit 1, 7 failures missing consent/status | 20:32:03 exit 0, 7 targeted pass | optional/mandatory server amount, idempotency header, pending/revision/rejected/expired/approved with forged query; no write from return |
| 5.2/7.3 | payments.test.ts public URL boundary | fail-closed stub | 20:30:15 exit 1, 3 failures valid checkout/mock denied | 20:32:03 exit 0, 9 pass | 2 exact HTTPS hosts, hostile suffix/javascript/http/userinfo, production always rejected, mock development-only, feature gate |
| 6.1/6.2 | App.test.tsx DOM+HTTP | route placeholder | 20:32:44 exit 1, 5 failures missing list/actions/window | 20:33:30 exit 0, 31 DOM total pass | empty/populated, confirmar/cancelar PATCH, explicit cancel consent, actions=false vs late 422, no reprogramar |
| 4.3/7.1 | e2e/pwa.spec.ts Chromium preview | no icons, unstyled controls | 20:35 exit 1, 3 failures: manifest.icons undefined, slot height 24px at 360/1280 | 20:39 exit 0, 4 browser pass | PNG dimensions 192/512/maskable and mobile/desktop keyboard+touch; screenshots frontend/test-results/horarios-{360,1280}.png |
| 7.2 | e2e/pwa.spec.ts Chromium SW | default generateSW shell already safe for tested request | initial browser run 1 offline case already pass, NOT claimed RED | 20:39 exit 0 | direct /mis-reservas navigation offline vs JSON fetch network failure; CacheStorage only public assets; empty local/sessionStorage; reconnect login |

Commands used for cycles: `npm.cmd test -- src/shared/api/client.test.ts`,
`npm.cmd test -- src/features/auth/session.test.ts`,
`npm.cmd test -- src/App.test.tsx --reporter=dot` (and `-t` selectors as row names),
`npm.cmd test -- src/features/reserva/payments.test.ts --reporter=dot`,
`npm.cmd run build`, `npx.cmd --no-install playwright test`.
Times above are local tool output, all on 2026-11-09. 20:38 full regression:
58 tests across 4 files exit 0; build exit 0, 12 public precache entries.
No Docker images built. Browser HTTP interception uses fictitious fixtures,
not backend acceptance. PWA prompt implementation needs update-cycle browser
evidence in the follow-up cycles below; no prior RED for its initial rendering
is claimed (the subsequently tested defer/apply bug has its own actual RED).

## Follow-up Cycles And Review

| Task | Test / Layer | Baseline | Executed RED | Executed GREEN | Triangulation / Refactor |
| --- | --- | --- | --- | --- | --- |
| 7.3 | App.test.tsx logout from public checkout / DOM+HTTP | checkout survived logout | 20:42:15 exit 1, checkout region unexpectedly remained after logout | 20:42:41 exit 0, 10 targeted pass | key Schedule by user identity; private routes already unmount; 2-patient browser regression verifies account separation |
| 3.3/7.1 | e2e/pwa.spec.ts / Chromium multi-tab + real SW update | tabs not invalidated; defer hid all update controls | 20:43 exit 1, both tests failed: second tab still showed private row; deferred update button unavailable | 20:46 exit 0, 6 browser pass | BroadcastChannel invalidation without tokens; deferred update remains actionable; later expanded login/registro forms, defer keeps typed email, apply explicitly reloads |
| 5.1/5.4 | App.test.tsx expected booking status / DOM+HTTP | 200 falsely announced success | 20:45:17 exit 1, 200 failed; 204 already safe via exception, NOT claimed RED | 20:45:41 exit 0, 76 total pass | expectedStatus 201; 200/204 -> result unverified, consult own list, no automatic POST retry |
| 4.2/5.2 | App.test.tsx malformed HTTP payloads / DOM | accepted inconsistent policy; invalid date crashed rendering | 20:50:44 exit 1, 4 failures plus Invalid time value | 20:51:23 exit 0, 4 targeted pass | mandatory/null and disabled/fractional amounts; invalid vs naive dates; runtime guards at HTTP boundary, alternatives filtered through same Slot guard |
| 7.2 | e2e/pwa.spec.ts reconnection / Chromium | old slots became briefly actionable on reconnection | 20:53 exit 1, patient reads still 2 when old slot visible; anonymous case already green | 20:58 exit 0, 11 browser pass | invalidate slot result/selection/conflict/consent on online event before fresh read; anonymous+patient no POST queued on reconnect |
| 3.1/3.2/3.3/4.2/5.2/5.3/6.1/6.2 | supplementary regression cases / public HTTP+DOM | existing implemented behavior | Not claimed RED: independent triangulation tests passed without new behavior | 20:53 and 20:57 exit 0, 90 tests total | GET/PATCH abort, parallel expired GET single refresh, late restore ignored after logout; two AR midnight dates; two date filters/all vs selected chair; stale fetch ignores abort; register 409/422; checkout 503 lookup; stable key same payload/new key changed treatment; 20 polls over <60s and manual query, terminal polling stops; 120 vs 119 min server actions; own-list order/names/states |

Review/refactor after green: extracted network helpers from visual components,
split SessionProvider from context hook, replaced effect-driven loading resets
with keyed server results to prevent stale filter data from being actionable.
No useMemo/useCallback, no React 19 APIs, no new backend auth flow. `useOnline`
uses useSyncExternalStore. Lint was initially 9 warnings; after refactor all 0
warnings/0 errors, without disabling lint rules. Regression remained green.

## Final Commands

After final lockfile, `npm.cmd ci --ignore-scripts` succeeded (455 packages),
then commands below succeeded on 2026-11-09. All npm commands cwd frontend/.

| Command | Exit | Evidence |
| --- | --- | --- |
| npm.cmd test -- --reporter=dot | 0 | 90 passed, 4 files; client 15, session 7, checkout URLs 9, DOM 59 |
| npm.cmd run lint | 0 | 0 warnings, 0 errors, 28 source/config/test files |
| npx.cmd --no-install tsc -b | 0 | clean (also included in build) |
| npm.cmd run build | 0 | Vite 6.3.6, 48 modules, generateSW, 12 public precache entries |
| npm.cmd run test:e2e | 0 | 11 Chromium tests passed, localhost preview automatically stopped |
| openspec.cmd validate c-10-pwa-reserva-publica --strict | 0 | Change is valid; command cwd project root |
| npm.cmd audit --json / clean ci audit | 1 / ci 0 | 14 findings: 3 low, 8 moderate, 1 high, 2 critical; NOT release signoff |

Browser coverage: PNG headers and dimensions 192/512/maskable; 360/1280px no
horizontal overflow, keyboard focus/Enter/Tab and touch target >=44px; offline
direct /mis-reservas and /pagos/retorno shell vs JSON fetch network failure;
CacheStorage URL inspection; multi-tab logout; defer/apply real updated SW on
login and registro without losing form on defer; two fictitious accounts;
anonymous/patient offline writes absent and reconnection fresh reads.
Screenshots were reviewed (mobile and browser assertions desktop) and contain
only public fictitious catalog/selection, not passwords or private rows.

Native audit: initial 12 findings predate C10. Router added 2 moderate findings;
patched 6.30.4 -> 6.30.6 within React 18-compatible line, without forced fix.
Remaining router broad-range advisories concern backslash redirects and SSR
error hydration. This app has no SSR/hydration input; navigation uses constants
or strict internal returnTo allowlist rejecting backslashes, plus URL tests.
No migration to router 7/Vite 8 or toolchain-wide audit fix in this change.
Preexisting Vite dev/launch-editor and Vitest UI/tinypool findings remain limited
to trusted local tool inputs; no UI server, no remote exposure, no release.
Review all remaining audit findings before pilot, target 2026-11-16.

## Contract Handoff And Gates

Exact routes/response fields and setup are in frontend/README.md. No global
/api prefix: only administrative config uses /api/config, not consumed here.
Catalog endpoint must provide active ordered resources and C09 policy fields,
with no PII. Runtime uses real API only, never falls back to fixtures.
POST /turnos sends only sillon_id/tratamiento_id/inicio/sena (not legacy aliases,
not money/fin). Idempotency-Key stays in memory for the same action/payload.
402 checkout and 503 CHECKOUT_NO_VERIFICADO use top-level bodies as designed
in C09, not exception.detail nesting. GET intento returns id and estado, not
checkout.status. Backend must preserve these planned shapes or coordinate a
contract revision before integration; no observed live differences are claimed.

Payment gating: VITE_ENABLE_TEST_PAYMENTS=false by default, production mode
always denied, mock only development, sandbox exact HTTPS MP AR allowlist.
Unlike an automatic redirect, 402 first shows amount/no-retention/manual-refund
warning and requires an explicit checkout link. Return never charges, only
queries own attempt. No paid-without-slot bypass or automatic refund added.

## Pending Tasks (17/25 Complete)

- 1.3: frontend baseline complete; backend pytest deliberately not run by frontend owner.
- 2.1/2.2: public catalog endpoint, active/inactive allowlist/RBAC checks and real C09 policy projection delegated to backend. No backend file edited.
- 7.2: frontend/SW online/offline and no-queue tests pass. Leave full task open for real API same-origin proxy vs SPA navigation checks, including PATCH/offline integrated acceptance; inherited no-cache behavior did not have a fabricated RED.
- 8.1: real API/browser cookies, 201/409/422, mobile/desktop integration after catalog is available.
- 8.2: verified C09 checkout/webhook, rejection and paid-without-slot with authorized sandbox/credentials. No sandbox or real payment executed, flag remains false.
- 8.3: frontend review/refactor/regression complete; backend regression and integrated matrix still owned elsewhere.
- 8.4: strict CLI validation complete; final live contract coordination/acceptance cannot be signed off before backend gates.

No archive, CHANGES/root/shared/C09/C11/C12 edits, commits, push, Docker images
or production deployment. Session/checkout/list data never persisted client-side;
source grep found storage names only in tests and no any/console/raw HTML sinks.

## Ejecucion E2E contra backend real (tarea 8.1)

Fecha: 2026-11-10. Entorno: Docker levantado (db:5432, redis:6379, api:8000, frontend:4173, todos saludables).
Endpoint GET /catalogo-publico implementado y disponible en http://localhost:8000/catalogo-publico (200, anonimo, sin PII, listas vacias: DB de desarrollo sin siembra de activos).
Se creo `frontend/e2e/real-backend.spec.ts` que llama al backend REAL con `page.request` (sin `page.route`, sin interception HTTP, sin mocks como unica evidencia) y se ejecuto con `npx playwright test e2e/real-backend.spec.ts`.

| Verificacion | Resultado contra backend real | Evidencia |
|---|---|---|
| anonimo lee catalogo publico (sin auth) | PASA | `GET /catalogo-publico` -> 200, `{sillones, tratamientos}` |
| registro de paciente | PASA | `POST /auth/registro` -> 201, rol `paciente` |
| login obligatorio (sin sesion) | PASA | `GET /auth/me` y `GET /mis-reservas` -> 401 |
| login + Mis reservas autenticado | PASA | `POST /auth/login` -> 200 + `access_token`; `GET /auth/me` 200; `GET /mis-reservas` 200 lista vacia |
| reserva sin sena | BLOQUEADO-ENTORNO | `POST /turnos` requiere tratamiento y sillón activos; DB dev sin siembra (catalogo vacio). No es regresion de codigo. |
| conflicto 409 | BLOQUEADO-ENTORNO | requiere reserva previa existente; no hay turnos en DB dev |
| cancelar 422 | BLOQUEADO-ENTORNO | requiere reserva dentro de ventana 2h; no hay turnos en DB dev |

Limitacion de entorno documentada: la DB de desarrollo (`turnos`) tiene 0 filas en `tratamiento`/`sillon`/`usuario`/`turno` (verificado via MCP postgres, solo SELECT). El MCP es de solo lectura y no hay script de siembra, por lo que no se pueden crear tratamientos/sillones/reservas para ejercitar los flujos de reserva, 409 y 422. La infraestructura de E2E contra backend real funciona (autenticacion, catalogo publico, mis-reservas verificadas); los flujos de reserva requieren siembra de datos previa.

Adicional: navegacion pagina (localhost:4173 -> localhost:8000) limitada por CORS (`FRONTEND_URL=http://localhost:5173` en backend/.env no incluye 4173); las llamadas directas `page.request` evitan CORS y confirman el contrato del backend. Los tests de browser de `pwa.spec.ts` no pueden lanzar en este equipo (no hay binarios de Playwright Chromium instalados en ms-playwright): problema de entorno preexistente, no regresion.

## Tarea 8.2 bloqueada (checkout sandbox MP)

Estado: BLOQUEADO. Requiere credenciales autorizadas de Mercado Pago sandbox (MP_ACCESS_TOKEN, MP_MODE=sandbox) que NO estan disponibles en este entorno. `backend/.env` tiene `MP_MODE=disabled` y `MP_ACCESS_TOKEN=` vacio. No se documento integracion con placeholder; no se aprobo checkout/retorno/estado con credenciales sandbox. Segun C-09, la aceptacion integrada de pago queda pendiente hasta que C-09 sea aprobado, implementado y el contrato verificado/archivado. No hay evidencia de flujo MP real ni mock aprobado como integracion.

## Skills And Documentation

Loaded full skills: openspec-apply-change, frontend-design,
vercel-react-best-practices, typescript-advanced-types, vite, webapp-testing,
tdd, security-and-hardening. Read project AGENTS, relevant KB, roadmap and C09
design/payment delta specs. No skill registry files used.
Context7: React Router 6.30.3 docs for declarative routing/search params;
vite-plugin-pwa for generateSW/prompt/virtual register; React Testing Library for
Vitest DOM/cleanup/async interactions. No React 19/Vite 8 recipes applied.

## High-Finding Correction Pass

2026-11-09 local / 2026-11-10 UTC. Explicit user authorization to fix frontend
session/security bugs only. This section supersedes earlier safety conclusions
about loopback-only mitigation, header idempotency, and refresh-only locking;
earlier command evidence remains historical, not an assertion of current safety.
C09 has no real Docker/Postgres/Redis services, confirmed by separate owner.
No backend edits, tests, bootstrapping or integrated acceptance in this pass.

### Baseline Before Edits

At 21:39:07 local: `npm.cmd test -- --reporter=dot` exit0, 90 tests/4 files;
`npm.cmd run test:e2e` exit0, 11 browser tests; lint exit0 (0 warnings/errors);
`npx.cmd --no-install tsc -b` exit0. No baseline failure fixed or suppressed.
`npm.cmd audit --json` exit1:14 findings (3low,8moderate,1high,2critical).
All commands use frontend cwd unless OpenSpec (project root).

### Executed TDD Cycles

| Finding / Tasks | Public Seam / Test | RED Executed (local time, exit1) | GREEN Executed (exit0) | Triangulation / Review |
| --- | --- | --- | --- | --- |
| H1 /3.3 | session.test.ts HTTP/session | 21:41:18,4 failures: delayed GET401 restored before/after logout; restore during closing; stale200 returned | 21:41:47,11 session tests | Both orderings deferred, no refresh/retry; closing flag and generation captured before dispatch; clear again on logout completion. First harness reused Response body: corrected before the counted RED. |
| H2 /3.3 | session.test.ts HTTP mutation order | 21:42:52,4 failures: login/logout reached HTTP before delayed refresh completed | 21:43:34,15 session tests | Same Session vs two instances; shared lock and same-realm queue; modeled cookie variable at response boundary, not real cookie proof. Raw /auth/me has no recursive recovery under lock. |
| H1 /3.3 | session.test.ts stale write401 | 21:45:48,2 failures: post/patch A cleared B identity | 21:49:59,17 session tests | Generation guard on success/error of both write methods, no automatic retry. |
| H3 /5.1,5.4 | App.test.tsx HTTP+DOM | 21:47:27,2 failures: generic500/503 lacked unverified state and allowed retry | 21:48:44,2 targeted tests | Replaced old test encouraging repeated503. Account-scoped memory survives SPA navigation, filters/choice/writes locked; no storage of private request. |
| H3 /5.1,5.4 | App.test.tsx reconciliation/malformed201 | 21:49:14,4 failures: reconciliation control did not query; malformed201 falsely success | 21:49:59,4 targeted tests | Found own matching reservation vs empty list; only positive server match unlocks, empty/error remains blocked. Two malformed bodies; success status alone insufficient. |
| H4 /4.2 | App.test.tsx UTC/local boundary | 21:50:36,2 failures: slot button omitted full date | 21:51:11,2 targeted tests | UTC00:00 -> previous AR day21:00, UTC03:00 -> chosen AR day00:00. Outside day stays visible/disabled, URL-preselected submit guarded too. Backend day semantics NOT fixed. |
| H5 /1.4,8.3 | tooling-security.test.ts dependency public API | 21:52:45,4 failures: inherited filename selected benign wrong module and inherited execArgv reached worker in both pools | 21:55:04,4 targeted tests | Patched Tinypool2.1.2; worker_threads + child_process, isolated child processes, no shell/untrusted code/real exploit. Harness initially inherited --input-type into threads even after patch; switched eval wrapper to isolate intended pollution. |
| H2 /3.3 | session.test.ts browser unsupported/restore failure | 21:57:38,4 failures: browser without locks mutated cookie; restore401/503 let old successful GET through | 21:58:34,these4 cases green (one NEW logout case red) | Browser fails closed without Web Locks; Node-only local queue is not multi-tab fallback. Failed restore increments generation before anonymous/unavailable state. |
| H2 /3.3 | session.test.ts lock acquisition failure on logout | 21:58:34,1 new failure: closing message missing when lock rejected | 21:59:12,full116 tests/5files | Catch outside lock covers acquisition AND HTTP failure, clears memory/informs unverified server closure; paired with existing503 logout case. |

Commands for rows: `npm.cmd test -- src/features/auth/session.test.ts --reporter=dot`,
`npm.cmd test -- src/App.test.tsx --reporter=dot -t "ambiguo bloquea"`,
same command with `-t "reconciliacion explicita|201 malformado"`, `-t "franja UTC"`,
`npm.cmd test -- src/tooling-security.test.ts --reporter=dot`.
No inherited/regression-only case is claimed as a fresh RED. Additional native
Web Lock browser tests are regression evidence after unit RED/GREEN, not fake
pre-fix browser failures.

### Behavior And Limits

- All cookie mutations serialize under `turnos-auth-cookie` across tabs that share the UI origin; login/logout included. No access/refresh tokens broadcast or persisted. Browser without Web Locks cannot mutate auth cookie and shows safe unavailability. This is an explicit security support requirement, not an implicit best-effort mutex.
- Old GET responses (401 or success), old POST/PATCH401 and pending identity results cannot recover/clear/deliver data into a different generation. Logout suppresses refresh until finalized. Generation-keyed flights avoid reusing an old-generation refresh promise.
- Uncertain reserve response blocks further POST, filters, slot choice and updates, including after navigation to/from Mis reservas. Explicit reconciliation only reads authenticated own reservations, matching treatment/chair/instant; empty list/error does not prove no commit and does not unlock. A known attempt routes to server status lookup. The header is NOT proof of server idempotency.
- The lock is in-memory and cleared on logout/reload by privacy design; it cannot be a durable duplicate-prevention control across reloads/sessions. Contact clinic for unresolved outcome, do not use reload as retry. Durable server reconciliation/idempotency is an integration gate, not invented by frontend.
- Full AR timestamp shown in every slot. Slot outside selected local date stays visible but disabled; no silent filtering, day shifting, synthetic availability or backend fix. Date contract remains BLOCKED and task4.2 reopened.
- Native Web Lock tests hold the same lock from another Chromium page, show login/logout pending with zero HTTP mutations, release and observe one request. HTTP intercepted with fictitious responses; no actual refresh cookie/backend identity guarantee is claimed.

### All Findings Triaged

| Audit Finding (14 baseline packages) | Action / Concrete Exposure Control |
| --- | --- |
| vite HIGH (Windows launch-editor and other6.x advisories) |6.3.6 ->6.4.6, above affected <=6.4.3; inside existing^6.x-compatible range, no Vite major. Final audit no Vite advisory. Not deferred via loopback. |
| tinypool CRITICAL | Scoped `vitest.tinypool=2.1.2` override removes both prototype pollution advisories. Reviewed official2.0 release (only breaking: dropNode18; availableParallelism replaces exec),2.1 additive serialization,2.1.2 security fix. Project already Node20+; engines explicit. Named/default Tinypool constructor/run/destroy/workerId APIs used by Vitest checked.4 benign gadget cases and suite verify both runtimes. |
| vitest CRITICAL |3.2.4 ->3.2.7 patches UI arbitrary file execution (<3.2.6). Remains MODERATE via mocker, not critical. No Vitest4/5 migration. |
| fast-uri MODERATE |3.1.8 ->3.1.9 in transitive permitted range; removed from audit. |
| serialize-javascript LOW |7.1.2 ->7.1.4 in transitive permitted range; removed from audit. |
| @vitest/mocker + vitest residual MODERATE | Fix requires major (audit suggests Vitest5). Not auto-upgraded. `test.api=false`, `vitest run` only, no UI/browser-mock/API listener in commands; tests/config trusted local files, no remote test modules. Do not enable API/UI without separate review. |
| react-router + react-router-dom MODERATE | Latest pinned6.30.6; fix requires7.18+, not automatic major. No SSR/error hydration. All navigation constants or strict internal returnTo allowlist rejecting backslashes, including new backslash regression cases. No provider URLs fed to router; checkout uses its own strict URL guard. |
| glob + minimatch + workbox-build + vite-plugin-pwa MODERATE | Fix requires major graph changes/downgrade suggested by audit; no force/downgrade. Only static source-controlled patterns in Vite Workbox config and trusted repository files; no user-provided glob strings, no remote input in build. These packages are build-time, not API/PWA runtime processing untrusted patterns. |
| deepmerge + @rollup/plugin-node-resolve LOW | Latest deepmerge4.3.1 has no patched4.x release. Controlled static plugin config, no external JSON or __proto__ options merged from users. Review before release rather than replace graph arbitrarily. |

Final audit exit1:10 findings,2low/8moderate/0high/0critical. Review residuals
before pilot (target2026-11-16); not release acceptance. `npm.cmd audit signatures`
exit0:453 registry signatures verified,146 attestations. npm scripts remain
disabled. No `npm audit fix --force`, no new runtime library or Node global install.
Actual execution Node24.19.0/npm11.17; package engines/release notes support
Node20+, but a separate Node20 execution matrix was NOT run here.

Context7 read `/vitejs/vite/v6.4.5` for6.x configureServer/security API and
`/vitest-dev/vitest/v3_2_4` for pool/API configuration; npm registry confirms
6.4.6/3.2.7 metadata. Official Tinypool release notes:
https://github.com/tinylibs/tinypool/releases/tag/v2.0.0,
https://github.com/tinylibs/tinypool/releases/tag/v2.1.0,
https://github.com/tinylibs/tinypool/releases/tag/v2.1.2.

### Final Correction Verification

Clean `npm.cmd ci --ignore-scripts` exit0:453 packages, lockfile accepted.
Full correction regression at21:59 exit0:116 tests/5files, lint0warnings/0errors,
tsc/build Vite6.4.6 correct,13 Chromium tests passed at22:00. Two additional
existing-route backslash cases were added afterward and final commands rerun.
See latest command outputs/final response for updated count.

No independent subagent tool is exposed in this environment. Manual session-only
review checked generation capture before each await, closing invalidation,
queued operation checks, single-flight identity, lock acquisition failures and
absence of recursive recoverable GET inside locks. This is NOT labeled an
independent-agent review or real-cookie test.

Current conservative progress16/25 after reopening4.2. C09 real-services blocker,
catalog backend, date semantics, real cookies/auth/reservation/SW proxy and
payments integration remain pending. No backend/shared-root/C09/C11/C12 edits,
commits, pushes, final images or production actions.

Latest final results after clean install and all edits (22:06-22:07 local):

| Command | Exit | Result |
| --- | --- | --- |
| npm.cmd test -- --reporter=dot |0|118/118 in5files: DOM68,session22,client15,checkout9,tooling4 |
| npm.cmd run lint |0|0warnings/0errors in31files; no lint suppressions |
| npx.cmd --no-install tsc -b |0|Clean explicit typecheck |
| npm.cmd run build |0|Vite6.4.6,48modules,12public precache entries |
| npm.cmd run test:e2e |0|13/13 Chromium, including both native cross-tab mutation locks |
| openspec.cmd validate c-10-pwa-reserva-publica --strict |0|Valid |
| openspec.cmd list --json |0|C10 remains in-progress16/25 |
| npm.cmd audit --json |1|10 total:8moderate,2low,0high,0critical (not a clean audit/release) |
| npm.cmd audit signatures |0|453 signatures verified,146 attestations |

Skills loaded for corrections: openspec-apply-change, security-and-hardening,
tdd, vercel-react-best-practices, vite, webapp-testing. No new design system,
feature scope, backend auth change or security bypass introduced.

## Fresh Frontend Handoff Verification

2026-11-10, 00:30-00:34 -03:00. Delegated execution for staging preparation,
from `frontend/`, using existing Node 24.19.0/npm 11.17.0 and browser binaries.
No dependency/browser installation, source/test/config/lockfile edits, backend
execution, infrastructure services or migrations. No listener detected on4173
before the runner started its own preview. Existing application processes were
not stopped or restarted.

| Command | Exit | Fresh Result |
| --- | --- | --- |
| npm.cmd test -- --reporter=dot | 0 | 118/118 tests in5files |
| npm.cmd run lint | 0 | 0warnings/0errors in31files |
| npx.cmd --no-install tsc -b | 0 | Explicit typecheck passed |
| npm.cmd run build | 0 | Vite6.4.6,48modules,12public precache entries |
| npm.cmd run test:e2e | 0 | 13/13 Chromium tests |

This is regression of existing frontend behavior, not a new RED/GREEN cycle or
backend/integrated acceptance. HTTP interception uses fictitious data; real
cookies, PostgreSQL/Redis and MP remain unverified. Generated dist, caches,
reports and screenshots are excluded from staging. npm audit/signatures and
OpenSpec validation were not rerun in this pass; earlier evidence remains
historical. C09 stays2/26 and C10 stays16/25 with all integration gates open.
Commit remains pending during staging preparation; no push, PR, archive, final
image build, production action or C11/C12 work.

## Regresión local del retorno de pago

Se corrigieron las tres URL de retorno para incluir `intento_id` y se ajustó la autorización de la consulta del intento para verificar el ID de paciente asociado al usuario autenticado. La prueba de integración reproduce el checkout simulado, confirma el estado pendiente para el titular y recibe 404 para otro paciente. Tarea 8.2 sigue pendiente de ejecutar el sandbox con credenciales autorizadas.
