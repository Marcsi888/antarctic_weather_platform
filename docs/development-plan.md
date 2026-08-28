# Development Plan

## 1. Objective

This document is the working plan for the GS Inima Environment technical
challenge: a full-stack application that retrieves historical meteorological
observations from AEMET OpenData for two Antarctic research stations
(Gabriel de Castilla and Juan Carlos I), persists them locally, aggregates
them over time, and exposes them through an API and a web interface. The
stated business framing is evaluating a hypothetical wind-farm project in
Antarctica, so wind speed, temperature, and pressure are the measurements of
interest.

The quality bar is not "does it run," but whether every decision in the
system (station identifiers, timezone handling, aggregation semantics,
cache design, error handling) can be defended in a follow-up technical
interview. The plan below exists to keep that standard visible throughout
the week rather than only at submission time.

## 2. Delivery Targets

- Official submission target: **28 August 2026**
- Internal implementation-complete target: **26 August 2026**

The two-day gap is deliberate, not padding. Historical-data integrations
tend to reveal their real problems late: a station identifier that turns
out wrong, a DST edge case that only shows up when a test interval happens
to cross a transition, a response field that AEMET populates inconsistently
across stations. Reserving 27–28 August for QA, documentation, screenshots,
and repository cleanup means those discoveries don't compete with
first-draft implementation work under time pressure. If implementation
finishes before 26 August, the extra time moves forward into validation and
polish rather than sitting idle, though it does not justify inventing more scope.

## 3. Engineering Priorities

In order, and only overridden if a concrete technical finding demands it:

1. Correctness of the required endpoint and its documented inputs/outputs
2. Idiomatic, deliberate Python (typing, structure, boundaries)
3. Resilient AEMET integration (timeouts, validation, mapped errors)
4. Timezone and DST correctness
5. Backend tests covering real behavior, not just happy paths
6. SQLite persistence and cache design that is explainable, not merely functional
7. React + TypeScript frontend quality
8. Frontend critical-path tests
9. Documentation (README, architecture, disclosures)
10. CI proportional to the project's size
11. Architecture diagrams
12. Technical report and optional translation, and cosmetic polish

This ordering exists so that if the week compresses, the cut falls on
polish, not on the things a reviewer would actually probe.

## 4. Development Phases

**Phase 0: Requirements and architecture.** Read the challenge
specification closely, resolve ambiguities I can resolve from documentation,
flag the ones I can't, and agree on a minimal layered architecture and
repository layout before any code exists.

**Phase 1: Python project foundation.** Project scaffolding: dependency
management, FastAPI app skeleton, settings/config module reading from
environment variables, logging configuration, exception hierarchy. No
AEMET or domain logic yet.

**Phase 2: AEMET integration.** Before writing the client: confirm the
endpoint contract against real documentation and, if credentials are
available, an actual response: station identifiers, the two-step
response pattern (AEMET's `datos`/`metadatos` indirection is expected but
must be confirmed, not assumed), field types, and error behavior. Then
build a typed client with explicit timeouts, response validation, and a
transport-DTO-to-domain-model mapping boundary.

**Phase 3: Timezone and aggregation domain logic.** Implement the
instant/local-representation/UTC/offset/DST transformation pipeline as an
isolated module, independent of the API layer, so it can be unit tested
against known DST transition dates. Implement hourly/daily/monthly
aggregation using the documented mean-based approach, isolated behind a
function boundary that documents the assumption.

**Phase 4: SQLite persistence and caching.** Schema design, uniqueness
constraints derived from observation identity, and interval-coverage logic
for cache hit/miss/partial-coverage. This phase depends on Phase 2 (data
shape) and Phase 3 (canonical timestamp representation) being settled.

**Phase 5: Backend API completion and tests.** Wire the service layer to
routes, finish request validation (station, interval, measurement
selection), and write the backend test suite: unit tests for domain logic,
integration tests for the endpoint with the AEMET client mocked.

**Phase 6: React/TypeScript frontend.** Vite + React + TypeScript scaffold,
typed API client, query form (station, interval, aggregation, measurements),
results table, and a lightweight chart.

**Phase 7: Frontend tests and integration.** Vitest + React Testing
Library coverage for form validation, loading/success/error/empty states,
and one interaction test involving aggregation or measurement filtering.
Manual end-to-end check against the running backend.

**Phase 8: CI and Docker.** GitHub Actions workflows for backend
(lint/type-check/test) and frontend (lint/type-check/test/build). Docker
Compose so `docker compose up --build` runs the full stack locally.

**Phase 9: Documentation and C4 architecture.** README, lightweight C4
System Context and Container diagrams reflecting what was actually built.

**Phase 10: English technical report.** LaTeX report focused on the
reasoning behind key decisions, written after the system is stable so it
describes the real implementation rather than the intended one.

**Phase 11: Final QA and optional Spanish report.** Fresh-clone
evaluator-experience test, final review against the checklist in §10, and
only then an optional Spanish translation of the report.

## 5. Day-by-Day Plan

Assuming work starts **22 August 2026** (today) and targets implementation
completion by **26 August 2026**:

| Date | Focus | Depends on |
|---|---|---|
| 22 Aug | Phase 0: requirements, ambiguities, architecture, repo structure. Phase 1: project foundation (config, logging, exception hierarchy, FastAPI skeleton). | - |
| 23 Aug | Phase 2: AEMET client, spec verification first, then implementation with tests against mocked responses. | Phase 1 |
| 24 Aug | Phase 3: timezone/DST module and aggregation module, each with focused unit tests. Phase 4 begins: SQLite schema and cache-coverage logic. | Phase 2 |
| 25 Aug | Phase 4 finishes: persistence + cache integrated. Phase 5: API routes wired end-to-end, backend test suite filled out (validation, cache hit/miss, upstream failure modes). | Phase 3, 4 |
| 26 Aug | Phase 6: React/TypeScript frontend (form, table, chart). Phase 7: frontend tests. Backend implementation-complete checkpoint. | Phase 5 |
| 27 Aug | Phase 8: CI workflows and Docker Compose. Phase 9: README and C4 diagrams. Fresh-clone smoke test. | Phase 6, 7, 8 |
| 28 Aug | Phase 10: English technical report. Final QA pass against §10 checklist. Repository cleanup. Submission. Spanish translation only if time remains and does not threaten the English deliverable. | Phase 9 |

The frontend is compressed into a single day (26 Aug) because its scope is
bounded (one form, one table, one chart, typed throughout) and because
backend correctness is the higher-priority item if something upstream (the
AEMET client, timezone handling) takes longer than expected on 23–24 Aug.
If Phase 2 or 3 slips, the frontend day is the first thing I'd compress
further, not backend testing.

## 6. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AEMET API behavior (station IDs, response shape, multi-step flow) doesn't match assumptions | High | High | Verify against real documentation and, if possible, a live call before writing the production client. Treat every unverified detail as a flagged assumption, not a fact, until confirmed. |
| Timezone/DST handling has a subtle bug (ambiguous or nonexistent local times, wrong aggregation boundary) | Medium | High | Isolate the transformation pipeline in one module; write tests anchored to known Europe/Madrid DST transition dates; never mix naive and aware datetimes. |
| Cache interval-coverage logic becomes more complex than the challenge warrants | Medium | Medium | Keep the coverage algorithm to the simplest version that is still correct and explainable (interval difference against stored coverage), and document explicitly why a more general interval-tree approach isn't needed at this scale. |
| Upstream data quality issues (missing fields, gaps in the ~10-minute granularity, inconsistent station naming) | Medium | Medium | Validate at the transport-to-domain boundary; decide and document explicit handling for missing values before aggregation touches them. |
| Frontend/backend contract drift (typed API client vs. actual Pydantic response models) | Low | Medium | Keep response models as the single source of truth; write the TypeScript types from the actual API responses, not from memory. |
| Time pressure compresses lower-priority items | Medium | Medium | The priority ordering in §3 exists precisely so that if this happens, the cut is predictable and defensible (report polish and Spanish translation go first, not tests or timezone correctness). |

## 7. Optional Differentiators

Explicitly separated from required scope so neither of us mistakes one for
the other mid-implementation:

- Chart/visualization polish beyond a functional line or bar chart
- C4 documentation beyond System Context + Container (a Component diagram
  only if it materially helps)
- Deeper analytical explanations in the report (complexity analysis,
  interval/set reasoning) beyond what's needed to justify the design
- English LaTeX technical report itself is a differentiator relative to a
  bare README, though a strong README is required regardless
- Optional Spanish translation of the report
- Evaluator-experience niceties (README badges, richer Docker healthchecks)

None of these are implemented before the required scope in §3 is solid.

## 8. Commit Strategy

Commits will follow Conventional Commits and correspond to genuine
engineering milestones (a working configuration layer, a tested AEMET
client, a complete aggregation module), not to calendar days or arbitrary
checkpoints. No commit will be split or merged purely to make the history
look a particular way, and no commit will claim work happened on a day it
didn't. At each milestone I'll propose the exact files to stage and a
commit message, and wait for approval before committing. Nothing here
authorizes autonomous commits.

## 9. Definition of Done

- The required AEMET endpoint integration works against verified station
  identifiers and date ranges
- Timezone conversion is correct and tested across at least one DST
  transition in each direction
- Aggregation (hourly/daily/monthly) uses local calendar boundaries, not
  raw UTC grouping, and its mean-based semantics are documented
- SQLite persistence avoids redundant AEMET requests for previously
  fetched intervals
- Backend test suite passes and meaningfully covers validation,
  aggregation, timezone/DST, cache behavior, and upstream failure modes
- Frontend is functional end-to-end against the real backend and its
  critical-path tests pass
- CI is green on the default branch
- `docker compose up --build` starts the full stack from a fresh clone
- README is complete per the outline agreed for this project
- Architecture diagrams reflect the actual implementation
- No secrets are committed; `.env` is ignored, `.env.example` is safe
- `git status` is clean at each milestone boundary
- Fresh-clone setup has been tested by following only the README

## 10. Final Review Checklist (27–28 August)

- [ ] Fresh clone, follow README exactly, note any friction
- [ ] `docker compose up --build` works with no manual fixes
- [ ] All backend and frontend tests pass locally and in CI
- [ ] No `any` in TypeScript without a documented reason
- [ ] No hardcoded credentials or station-identifier guesses left unverified
- [ ] Every non-obvious decision has a corresponding note in the README,
      architecture doc, or report
- [ ] Screenshots in the README reflect the current frontend
- [ ] AI usage disclosure is present and accurate
- [ ] Git history reads as coherent engineering progress
- [ ] I can explain every file's purpose without re-reading it first
