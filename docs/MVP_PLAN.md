# MVP Completion Plan

_Assessment date: 2026-09-15. Scope: everything needed to make Aeon's End Assistant
usable end-to-end as described in `README.md`._

---

## 1. Current state

There is no separate specification document in the repo (no issues, one closed PR),
so `README.md` is treated as the spec throughout this plan.

### What works today

| Area | Status |
|---|---|
| Data ingestion (`ingestion/seed.py`) | Working — scrapes gems/relics/spells/mages/nemeses from the wiki, caches to disk |
| Schema + migrations | Working — 3 Alembic revisions, all tables present |
| `GET/PUT /sets`, `/sets/saved` | Working |
| `GET /quickplay` | Working |
| `POST /expeditions` (create + initial draw) | Working |
| `GET /expeditions/{id}` (state) | Working |
| `POST /expeditions/{id}/resolve-battle` (win path) | Working |
| Frontend: Home, SetSelection, Quickplay, ExpeditionMode, ExpeditionResume, NewExpedition | Working |
| Backend test suite | 9 tests, all passing |
| CI (backend) / CD (EC2) | Working |

### Verified defects

Each item below was reproduced against a live Postgres + the real test fixtures,
not inferred from reading code.

**Frontend does not compile.** `npm run build` fails with 3 `TS6133` errors in
`ExpeditionView.tsx`; `npm run lint` reports 5 errors. CI only runs backend
pytest, so this has gone unnoticed. `frontend/Dockerfile` ships the Vite dev
server (`npm run dev`), so there is no production build path at all and nothing
ever exercises `tsc`.

**Expedition play loop is a stub.** `ExpeditionView.tsx` is the only page that
matters for the headline feature, and none of its buttons reach the API.
"Lock Supply", "Win" and "Loss" only call `setPhase(...)` on local state. The
post-win supply draw renders an empty `<h1>New Supply Cards:</h1>`, and the loss
randomizer picker is a literal `{/* temp */}` comment. `api.ts` has no
`resolveBattle`, `lockSupply` or `deleteExpedition` client at all. **An expedition
cannot be played past creation.**

**A lost battle soft-bricks the expedition.** `resolve_battle` sets
`result = 'loss'` on the current `ExpeditionBattle` row, leaves `current_battle`
unchanged, and creates no replacement row. Reproduced:

```
BATTLES AFTER LOSS: [{'battle_number': 1, 'result': 'loss', 'nemesis': {...}}]
PENDING BATTLES:    []
```

The frontend finds the current battle with `battles.find(b => b.result === null)`,
which now returns `undefined` — the nemesis disappears and the expedition can
never be resumed. A second loss on the same battle returns 200, silently
overwrites the same row (so the history shows one loss instead of two), but
*does* still grant the randomizer — barracks grew 9 → 10 → 11.

**`lock-supply` does not validate anything.** It never checks that the submitted
ids belong to this expedition or are currently in the barracks, and never checks
that exactly 9 cards remain. It also silently returns 200 with the expedition
unchanged when the barracks is already ≤ 9, so a caller cannot distinguish
"nothing to banish" from "banish applied". Nothing forces a supply lock before
the next `resolve-battle`.

**`DELETE /expeditions/{id}` returns `200 null` for ids that do not exist.**
No existence check, no `204`.

**The documented `big_pockets` variant is rejected.** `README.md` documents
`big_pockets`; `ExpeditionVariant.BIG_POCKETS` is `'big-pockets'`. Posting the
documented value returns `422`. The variant is also absent from the
`NewExpedition` dropdown, so it is unreachable from the UI despite being
implemented in `lock_supply`.

**Minor.** `GET /expeditions/active` raises 404 on an empty list and is never
called (the frontend filters `/expeditions` client-side).
`app/routers/cards.py` is a 0-byte file registered nowhere. `api.ts` never checks
`res.ok`, so error bodies become "data" and React Query renders no error state.
CORS hard-codes an EC2 IP. No tests exist for `/quickplay` or `/sets`, and none
for the frontend. `backend/ingestion/cache/` is gitignored, so a fresh clone
pays the full multi-minute rate-limited wiki scrape.

---

## 2. What "MVP" means here

The README already promises the scope. The MVP is done when a user can:

1. Pick their owned sets and have them persist.
2. Randomize a single game (already works).
3. Create an expedition, **play all of its battles through to completion**,
   winning and losing, with the barracks tracked correctly across battles.
4. Leave, come back, and resume that expedition.
5. Delete an expedition.

Item 3 is the whole gap. Treasures stay out of scope (README), and legacy
filtering / Outcasts stay out of scope (README).

---

## 3. Plan

Five phases, ordered so each one leaves the repo in a working state. Phases 1
and 2 are the MVP-critical work; 0 is a prerequisite; 3 and 4 are what make it
shippable rather than demoable.

### Phase 0 — Make the build honest (prerequisite, ~half a day)

Nothing else is trustworthy while `tsc` fails and CI doesn't notice.

- Fix the 3 unused-binding errors in `ExpeditionView.tsx`. Do not delete
  `lossRandomizerType` / `selectedPlayerCards` / `notSelectedPlayerCards` — they
  are the unfinished wiring that Phase 2 consumes. Fixing them properly means
  finishing the component, so the minimum here is to get a clean build and let
  Phase 2 use the bindings.
- Fix the two `react-hooks/set-state-in-effect` lint errors in `SetSelection.tsx`
  and `ExpeditionView.tsx`. Both are the "derive state from a query result"
  pattern; replace with a `useMemo` default plus an explicit reset keyed on the
  expedition/battle id rather than on the whole `data` object. The
  `ExpeditionView` effect currently re-runs on every refetch and would wipe the
  user's card selection mid-interaction once mutations exist.
- Add a `frontend` job to `.github/workflows/ci.yml`: `npm ci`, `npm run lint`,
  `npm run build`.
- Add a multi-stage production target to `frontend/Dockerfile` (build with node,
  serve the static bundle), keeping the dev-server command for local compose.

**Done when:** `npm run build` and `npm run lint` both exit 0, and CI enforces it.

### Phase 1 — Correct the expedition state machine (backend, ~1–2 days)

**1a. Model battle attempts so a loss leaves a pending battle.**
Recommended shape: one `ExpeditionBattle` row per *attempt*. On a loss, set
`result = 'loss'` on the current row and immediately insert a new row with the
same `battle_number` and the same `nemesis_id` and `result = NULL`. This
preserves the loss history and — importantly — preserves the invariant the
frontend already relies on, that the pending battle is the one with a null
result.

The alternative (a single row per battle number with an `attempts` counter and a
result that stays null until won) is a smaller migration but throws away history;
prefer the per-attempt rows.

Required follow-on edits:
- `resolve_battle` currently selects the battle by `battle_number == current_battle`,
  which becomes ambiguous with multiple attempt rows. Key it on
  `ExpeditionBattle.result == None` instead.
- Add an `attempt` (or ordering) field to `BattleDetail` so the frontend can
  render "Battle 2, attempt 3".
- `fought_nemesis_ids` dedupe on the win path still works unchanged, but confirm
  with a test that a re-fought nemesis is not re-drawn later.
- New Alembic revision.

**1b. Validate `lock-supply`.**
- 400 if any submitted id is not currently a barracks card of this expedition.
- 400 if the resulting barracks size is not exactly 9 (skip the check entirely
  for `big-pockets`, which by design banishes nothing).
- Return the resulting state rather than the bare expedition, so the client does
  not need a follow-up `GET`.

**1c. Guard `resolve-battle`.**
- 400 when the expedition is already `complete`.
- 400 when the barracks exceeds 9 and the variant is not `big-pockets`
  (i.e. the supply was never locked).
- 400 when `won_battle` is false and `loss_randomizer_type` is missing — it is
  currently `Optional`, and a null falls into the `is not TREASURE` branch and
  then crashes on `.value`.

**1d. Small corrections.**
- `DELETE /expeditions/{id}`: 404 on missing, 204 on success.
- Decide the `big_pockets` vs `big-pockets` spelling (recommend changing the enum
  to `big_pockets` to match the README and every other snake_case value in the
  API) and update whichever side loses.
- Delete `app/routers/cards.py`.
- Either wire `GET /expeditions/active` into the frontend or delete it; if kept,
  return `[]` instead of 404 on empty.

**Done when:** a scripted win/loss/win/loss/win/win/win/win run through the API
leaves a coherent, resumable state at every step.

### Phase 2 — Wire the expedition play loop (frontend, ~2–3 days)

This is the MVP. Everything above exists to make this possible.

**2a. `api.ts`:**
- Add `resolveBattle(id, { won_battle, loss_randomizer_type })`,
  `lockSupply(id, banishedIds)`, `deleteExpedition(id)`.
- Add a shared `handle(res)` helper that throws on `!res.ok` using the FastAPI
  `detail` field, and route every existing call through it. Without this, all the
  new 400s from Phase 1 render as blank screens.

**2b. `ExpeditionView.tsx` — replace local-only phases with real mutations:**

| Phase | Behaviour |
|---|---|
| `selecting` | Barracks checkboxes, exactly 9 selectable. Shown only when barracks > 9 and variant ≠ `big-pockets`; otherwise skip straight to `locked`. |
| Lock Supply | `POST /lock-supply` with the **un**selected ids, invalidate the expedition query, advance to `locked`. |
| `locked` | Show the 9-card supply, the mages, and the current nemesis. Win / Loss buttons. |
| Win | `POST /resolve-battle { won_battle: true }`, then diff barracks before/after to show the 3 newly drawn randomizers by name, then return to `selecting` for the next battle — or to `complete`. |
| Loss | Show the randomizer picker (gem / relic / spell / mage / treasure), `POST /resolve-battle` with the choice, show what was added, return to `locked` for the retry against the same nemesis. |
| `complete` | Expedition-finished state with the full battle history. |

Use `useMutation` + `queryClient.invalidateQueries` throughout; derive `phase`
from server state where possible rather than from a `useState` that a refetch can
desynchronise.

**2c. Supporting UI:**
- Render banished cards and battle history (`battles` is already in the response
  and currently unused).
- Delete-expedition control on `ExpeditionResume`, with a confirmation.
- Add `big-pockets` to the `NewExpedition` variant dropdown.
- `ExpeditionResume` should show battle number / variant per expedition, not just
  a name.

**Done when:** a full standard expedition — including at least one loss and
retry — can be played start to finish in the browser, closed, and resumed.

### Phase 3 — Robustness and configuration (~1 day)

- Loading and error states on every page; today a failed fetch renders nothing.
- Move the API base URL to `VITE_API_URL` with the current
  `http://${hostname}:8000` as the fallback.
- Move CORS origins to an env var instead of the hard-coded EC2 IP.
- Empty-state handling when a user's sets are too small to draw from (the backend
  already 400s with a useful `detail`; surface it).

### Phase 4 — Test and documentation debt (~1 day)

- Tests for `/quickplay` (respects saved sets, honours `num_mages`, 404 with no
  saved sets) and `/sets` (save/replace round-trip).
- New expedition tests: loss leaves a pending battle, two losses record two
  attempts, `lock-supply` rejects foreign ids and wrong counts, `resolve-battle`
  rejects an unlocked supply, delete returns 404 for unknown ids, and each of the
  four variants runs to completion.
- Sync `README.md`: the variant spelling, the `lock-supply` request body
  (currently undocumented — it is a bare `list[int]`), and the delete status code.
- Consider committing `backend/ingestion/cache/` (remove it from `.gitignore`) so
  a fresh clone can seed without the multi-minute rate-limited scrape. This is
  the single biggest quality-of-life win for new setups and for CI integration
  tests.

---

## 4. Sequencing and estimate

```
Phase 0  ──►  Phase 1  ──►  Phase 2  ──►  Phase 3  ──►  Phase 4
(build)      (backend)     (frontend)    (polish)      (tests/docs)
 ~0.5d         ~1-2d          ~2-3d        ~1d           ~1d
```

Roughly **5–8 working days** to a genuine MVP. Phases 0–2 alone (~4–6 days) get
to "the advertised feature set actually works"; 3 and 4 are what make it
maintainable.

Phase 1 and Phase 2 can overlap once 1a lands, since 1a fixes the contract that
2b depends on. Nothing in Phase 2 should start before 1a — building the UI
against the broken loss flow would mean building it twice.

## 5. Open questions for the author

1. **Banishing is permanent** in the current code — banished cards are excluded
   from all future draws by `draw_supply`. Confirm that matches the intended
   rules, since it is the load-bearing assumption of the barracks model.
2. **Expedition length** is hard-coded as `MAX_EXP_LEN = 4`. A `TODO` in
   `test_expeditions.py` notes that Beyond the Breach makes this 5. In or out of
   MVP?
3. **Short variant** starts at battle 2 and still ends at battle 4, giving 3
   battles. Confirm that is the intended shape.
4. **Single-user model.** `UserSet` has no user column and `/sets/saved` replaces
   the global row set. Fine for MVP; worth confirming multi-user is genuinely a
   post-MVP concern.
