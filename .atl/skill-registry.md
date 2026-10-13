# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

## Project Skills (`.agents/skills/` — única fuente, no duplicar en `~/.agents` ni en `.opencode/skills/`)

| Trigger | Skill | Path |
|---------|-------|------|
| React components, Next.js pages, data fetching, bundle optimization, performance improvements | vercel-react-best-practices | .agents/skills/vercel-react-best-practices/SKILL.md |
| Asked to "review my UI", "check accessibility", "audit design", "review UX", "check my site against best practices" | web-design-guidelines | .agents/skills/web-design-guidelines/SKILL.md |
| Building new UI or reshaping existing one; aesthetic direction, typography, non-templated visual design | frontend-design | .agents/skills/frontend-design/SKILL.md |
| Anything living in Postgres: tables, columns, types, schema, migrations, RLS, indexes, triggers, functions, pg_cron/pgmq, pgvector, pg_restore; slow queries, EXPLAIN, connections, locking, bloat | supabase-postgres-best-practices | .agents/skills/supabase-postgres-best-practices/SKILL.md |
| Designing or reviewing a PostgreSQL-specific schema: types, keys, constraints, indexes, partitioning | postgresql-table-design | .agents/skills/postgresql-table-design/SKILL.md |
| Building new FastAPI applications or setting up backend API projects | fastapi-templates | .agents/skills/fastapi-templates/SKILL.md |
| Building async APIs, concurrent systems, I/O-bound apps requiring non-blocking operations | async-python-patterns | .agents/skills/async-python-patterns/SKILL.md |
| Working with FastAPI APIs, Pydantic models, dependencies, SSE/streaming, serving frontend apps | fastapi | .agents/skills/fastapi/SKILL.md |
| Complex type logic, reusable type utilities, compile-time type safety in TypeScript | typescript-advanced-types | .agents/skills/typescript-advanced-types/SKILL.md |
| Working with Vite projects, vite.config.ts, Vite plugins, libraries/SSR apps | vite | .agents/skills/vite/SKILL.md |
| Auditing input handlers, user input, auth, sessions, storage, external integrations, login flows, OWASP Top Ten, dependency audits, supply-chain risk, PII/GDPR/CCPA | security-and-hardening | .agents/skills/security-and-hardening/SKILL.md |
| Creating/reviewing Dockerfiles and Compose services, installer harnesses, container security/networking/volumes ⚠️ Snyk High Risk flag at install — review generated Docker content before use | docker-patterns | .agents/skills/docker-patterns/SKILL.md |
| User wants test-first development, mentions "red-green-refactor", or wants integration tests | tdd | .agents/skills/tdd/SKILL.md |
| User says "diagnose"/"debug this", or reports something broken/throwing/failing/slow | diagnosing-bugs | .agents/skills/diagnosing-bugs/SKILL.md |
| User wants to review a branch, PR, work-in-progress changes, or asks to "review since X" | code-review | .agents/skills/code-review/SKILL.md |
| Automate browser interactions, test web pages, work with Playwright tests | playwright-cli | .agents/skills/playwright-cli/SKILL.md |
| Interacting with and testing local web apps using Playwright: verify frontend, debug UI, screenshots, browser logs | webapp-testing | .agents/skills/webapp-testing/SKILL.md |
| Implementing E2E tests, debugging flaky tests, establishing testing standards (Playwright/Cypress) | e2e-testing-patterns | .agents/skills/e2e-testing-patterns/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### vercel-react-best-practices
- Eliminate waterfalls: parallelize independent fetches with Promise.all, start promises early / await late, use Suspense boundaries to stream
- Import directly from modules, never barrel files; use next/dynamic for heavy components; defer analytics/logging until after hydration; preload on hover/focus
- Server: authenticate server actions like API routes; use React.cache() for per-request dedup; never hold mutable request state in module scope; minimize data passed to client components
- Client: use SWR for request dedup; version and minimize localStorage data; passive listeners for scroll
- Re-renders: derive state during render (not in effects), primitive effect deps, no inline component definitions, startTransition for non-urgent updates, useDeferredValue to keep inputs responsive
- Never memoize simple primitives; hoist static JSX; ternary over && for conditionals; group DOM/CSS changes via classes

### web-design-guidelines
- Before reviewing, fetch fresh guidelines via WebFetch: `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`
- Check target files against ALL fetched rules, not a subset
- Output findings in the terse `file:line` format specified by the guidelines
- If no file/pattern argument given, ask the user which files to review — do not guess

### frontend-design
- Design lead mindset: deliberate, opinionated palette/type/layout specific to the brief; take aesthetic risk; never ship generic AI-default looks (cream+terracotta serif, black+acid accent, SaaS card grids, ALL-CAPS eyebrow labels, `→` on links)
- Ground choices in the subject matter (industry, materials, vernacular); brief's explicit direction always wins
- Two passes: plan first (4–6 named hex colors, 1–2 typefaces with roles, layout concept with alignment, principles), self-review plan against brief for genericness, then build
- Typography: 1–2 families, line length <80 chars, never accent a single headline word or use all-caps labels
- Motion: one orchestrated moment max; motion must answer a user action; respect reduced motion; always responsive, keyboard-focus visible, accessible palette

### supabase-postgres-best-practices
- Load BEFORE any Postgres change, even a one-column change or single query
- Priority order: query performance and connection management (CRITICAL) → RLS/security → schema design → concurrency/locking
- Read the specific `references/<category>-*.md` rule file for the task at hand; each has incorrect-vs-correct SQL + EXPLAIN
- Connection pooling/scaling rules apply to any deployment, not just Supabase-hosted
- RLS policies always ship with tests verifying row visibility per tenant/role

### postgresql-table-design
- PK: `BIGINT GENERATED ALWAYS AS IDENTITY`; UUID only for distributed/opaque IDs (uuidv7/PG18+ or gen_random_uuid)
- Types: `TIMESTAMPTZ` for time, `NUMERIC(p,s)` for money (never `money`), `TEXT` for strings, `BOOLEAN NOT NULL`; never `timestamp` tz-naive, `char(n)`/`varchar(n)`, `serial`, `timetz`
- Normalize to 3NF first; denormalize only for measured, proven read wins
- Manually index every FK column (Postgres does NOT auto-index FKs); composite indexes obey leftmost-prefix; partial indexes for hot subsets; GIN for JSONB/arrays/FTS, GiST for ranges + exclusion constraints
- Anti-double-booking: `EXCLUDE USING gist (resource WITH =, period WITH &&)` — the DB enforces no-overlap, never app code alone
- UNIQUE allows multiple NULLs — use `UNIQUE NULLS NOT DISTINCT` (PG15+) when only one NULL allowed; CHECK passes on NULL so pair with NOT NULL; snake_case unquoted identifiers
- See `references/details.md` for JSONB indexing, partitioning DDL, workload patterns, zero-downtime evolution

### fastapi-templates
- Layout: `app/{api/v1/endpoints,core,models,schemas,services,repositories}` + `main.py`; business logic in services, data access in repositories, never in route handlers
- Async route handlers + async DB operations throughout; shared concerns (DB session, auth) via `Depends` injection
- Tests: pytest + httpx AsyncClient with `dependency_overrides[get_db]` against isolated test DB; per-test session fixtures
- Read `references/details.md` for implementation patterns when the SKILL.md summary is insufficient

### async-python-patterns
- Stay fully sync or fully async within a call path — never mix blocking I/O into async code
- Concurrent independent I/O with `asyncio.gather()`; long-lived concurrency via `asyncio.create_task()` with explicit lifecycle/cancellation handling
- Never block the event loop: CPU-bound work goes to `asyncio.to_thread()` or a process pool
- Always set timeouts (`asyncio.wait_for`); handle `CancelledError` for cleanup; use `async with` / `async for` for resource cleanup and async iteration
- Gather partial failures explicitly (return_exceptions or per-task try/except) — one failing task must not silently kill the batch
- Test async code with pytest-asyncio anyio-style async fixtures; never call async code from sync tests without a loop policy

### fastapi
- Run with `fastapi dev` / `fastapi run`; declare entrypoint in `pyproject.toml` `[tool.fastapi]`; prefer uv + Ruff + ty + HTTPX tooling
- Always use `Annotated[..., Depends(...)]` style for params and dependencies; create reusable type aliases for dependencies
- Never use `...` (Ellipsis) in path operations or Pydantic models; never use Pydantic `RootModel` — prefer plain return types, `response_model` only when public schema differs from internal return
- One HTTP operation per function; router-level prefix/tags/shared deps on `APIRouter`
- Async path ops only for I/O-bound work with async deps; sync `def` for CPU-bound — wrong choice blocks the loop or adds overhead
- SSE/streaming: `response_class=EventSourceResponse` + `yield`; see `references/streaming.md`; serve built frontend via `app.frontend()`/`router.frontend()`; native OpenTelemetry for traces/metrics/logs

### typescript-advanced-types
- Generics with constraints (`T extends ...`) for reusable type-safe APIs; multiple type params compose via intersections
- Conditional types for type-level branching; distribute thoughtfully over unions; `infer` to extract inner types
- Mapped types (`in keyof`, `as` remapping, `+`/`-` modifiers) for transformations; template literal types for string-domain safety (routes, event names, API keys)
- Prefer built-in utility types (Partial, Pick, Omit, ReturnType, Awaited, NonNullable) over hand-rolled equivalents
- Narrow with discriminated unions + exhaustive `never` checks; validate at runtime boundaries (zod/valibot) — types erase at runtime
- Test complex types with compile-time assertions (`expectTypeOf`/`AssertTrue`); avoid deep recursion — keep instantiation depth small for compiler performance

### vite
- Vite 8 uses Rolldown bundler + Oxc transformer (not Rollup/esbuild) — check `references/rolldown-migration.md` when touching build config
- Always ESM, never CommonJS; prefer `vite.config.ts` with `defineConfig`; env via `loadEnv`, client vars through `import.meta.env`
- Assets: `import.meta.glob` for bulk imports, `?raw`/`?url` suffix queries; path alias `@` → `/src`
- Dev proxy API calls: `server.proxy: { '/api': 'http://localhost:8080' }`; official plugins: `@vitejs/plugin-react` (or `-swc`), `@vitejs/plugin-legacy` for old browsers
- Library/SSR builds need explicit mode config — see `references/build-and-ssr.md`; multi-environment (Vite 6+) via Environment API reference

### security-and-hardening
- Threat-model first: map trust boundaries (HTTP, forms, uploads, webhooks, queues, LLM output — trust follows who WROTE the value), name assets, run STRIDE, write abuse cases as first tests
- Always: validate all external input at the boundary (schema → 422, downstream uses parsed value only); parameterize every query; framework auto-escaping for output; HTTPS; bcrypt≥12/scrypt/argon2; httpOnly+secure+sameSite cookies; security headers (CSP from `default-src 'self'`); native lockfile audit before every release
- Never: commit secrets (rotate immediately if leaked, then purge history); log sensitive data; trust client-side validation; `eval()`/`innerHTML` with user data; auth tokens in localStorage; stack traces to users; CORS `*` with credentials
- Auth: check authorization per request on the resource (IDOR/A01), not just authentication; rate-limit auth endpoints (~10/15min) with a shared store when multi-instance; strip sensitive fields before responding
- SSRF: allowlist scheme+host for user-influenced URLs, resolve ALL DNS records, reject private/reserved ranges, forbid redirects
- Ask human first for: new/changed auth flows, new PII/payment storage, new external integrations, CORS changes, uploads, rate-limit changes, elevated permissions
- Privacy: classify fields, collect only for stated purpose, set retention TTL + real deletion path (backups/caches/indexes included), consent-gated third-party sharing; LLM output is untrusted input — validate + encode, never into SQL/shell/DOM/eval

### docker-patterns
- ⚠️ WARNING (Snyk High Risk flagged at install): treat generated Docker/installer content as untrusted — review Dockerfiles, install scripts, and Compose files line-by-line before building or running
- Compose: `depends_on` with `service_healthy` conditions; named volumes for pgdata/redisdata; bind-mount source + anonymous volume for deps for hot reload; healthchecks on DB services (pg_isready)
- Multi-stage Dockerfiles: deps → dev (hot reload) → build → production (minimal, non-root `USER appuser`, HEALTHCHECK, `NODE_ENV=production`); separate dev/prod targets, never ship dev tooling to prod
- Secrets via environment, never baked into images; `.env.example` committed with placeholders, real `.env*` gitignored
- Use override files for local vs prod differences; pin base image versions (e.g. `postgres:16-alpine`, `node:22-alpine`)

### tdd
- Red before green: failing test first, then minimal code to pass — no speculative features
- Test behavior through public interfaces (seams), never internals/private methods/side channels; expected values from independent source of truth (spec, literal, worked example) — never recomputed the way the code does
- Agree on seams with the user BEFORE writing tests ("What's the public interface, which seams?"); no test at an unconfirmed seam
- One vertical slice per cycle (one seam → one test → one minimal implementation); never horizontal (all tests first, then all code)
- Refactoring belongs to review (code-review skill), not the red→green loop; consult CONTEXT.md/ADRs for domain vocabulary

### diagnosing-bugs
- Phase 1 is the skill: build a TIGHT red-capable feedback loop first (failing test → curl script → CLI fixture → headless browser → trace replay → throwaway harness → fuzz → bisect → differential); no hypothesizing before the loop exists; tighten for speed/signal/determinism (pin time, seed RNG, isolate FS)
- Redact every secret as `<REDACTED>` in shown commands/outputs; keep credentials in env vars
- Reproduce the USER's exact symptom, then minimize to the smallest still-red scenario (every remaining element load-bearing)
- Generate 3–5 ranked falsifiable hypotheses ("If X, then changing Y removes it"), show user before testing; change one variable per probe; debugger > targeted tagged logs (`[DEBUG-xxxx]`); perf bugs need measurement + bisection, not logs
- Regression test before fix only at a correct seam (else flag missing seam as the finding); cleanup mandatory: repro green, `[DEBUG-*]` removed, throwaways deleted, winning hypothesis in commit message

### code-review
- Two-axis review of `git diff <fixed-point>...HEAD` (three-dot): Standards (repo conventions + Fowler smell baseline) and Spec (originating issue/spec) run as PARALLEL sub-agents, reported side by side, never merged/reranked
- Pin fixed point first: `git rev-parse` must resolve, diff non-empty; capture `git log <fixed-point>..HEAD --oneline`
- Spec source order: issue refs in commits → user-provided path → docs/specs/.scratch matching branch → ask user (skip Spec axis if none)
- Standards = repo docs (CODING_STANDARDS.md etc.) + 12-smell baseline (Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest); repo standard always overrides baseline; smells are judgement calls, never hard violations; skip what tooling enforces
- End with per-axis finding counts + worst issue per axis

### playwright-cli
- `playwright-cli open [url]` → `snapshot`/`find` for refs → `click eN` / `fill eN "text" --submit` / `type` / `press` / `hover` / `select` / `drag` / `upload` / `check` → `close`; interact via snapshot refs, not coordinates
- `find "text"` / `find --regex "/pattern/i"` to locate nodes; `--filename=` when too many matches; `eval "js" [ref]` for attributes/DOM reads
- `screenshot` rarely needed (snapshot is primary); `resize 1920 1080` for viewport; `dialog-accept`/`dialog-dismiss` for modals; `go-back`/`go-forward`/`reload` for navigation
- Scoped shell: only `playwright-cli:*` and `npx playwright:*` commands

### webapp-testing
- Write native Python Playwright scripts with `sync_playwright()`; headless Chromium; always `browser.close()`
- Scripts in `scripts/` are black boxes: run `--help` first, never read source unless customization is proven necessary
- Dynamic apps: `with_server.py` manages server lifecycle (single or multi-server backend+frontend); scripts contain only Playwright logic
- Reconnaissance-then-action: goto → `wait_for_load_state('networkidle')` (CRITICAL before DOM inspect) → screenshot/locators → identify selectors → act; never inspect DOM before networkidle
- Prefer `text=`/`role=`/ID selectors; `wait_for_selector()` over fixed sleeps; see `examples/` for element discovery, static `file://` HTML, console logging patterns

### e2e-testing-patterns
- Pyramid: many unit, more integration, few E2E — E2E only for critical user journeys (login, checkout, booking), complex interactions, cross-browser, real API integration; never unit logic, API contracts, or edge cases
- Test user behavior (click, type, see), not implementation; independent + deterministic tests; Page Objects for page logic; `test.step` for reporting
- Selectors: `data-testid`/`getByRole`/`getByLabel` — never CSS classes, nth-child, or DOM structure
- Flakes: proper auto-waits, never fixed timeouts; mock external APIs; parallelize; create+destroy test data per test
- Debug: `--headed`, `--debug`, trace viewer + screenshots/video, `page.pause()` inspector

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| *(none yet)* | — | Project CLAUDE.md/AGENTS.md not generated yet (later phase); conventions section intentionally empty |

## Warnings

- **docker-patterns**: flagged Snyk High Risk at install time. Review all generated Docker/installer content before building or running.
