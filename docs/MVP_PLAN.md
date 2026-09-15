# MVP Completion Plan

_Assessment date: 2026-09-15._

**Spec sources:** ["Requirements and Definitions for Aeon's End Assistant App"](https://docs.google.com/document/d/1GO8vTYuYLKOZHR14PBj0ZXCfcqQKSnrwALrm_j7tw9E/edit)
(authoritative) and `README.md` (implementation notes). Where the two disagree,
the Drive document wins.

---

## 1. Requirement traceability

Every requirement checkbox from the spec document, against the code as it stands.

| Requirement | Status |
|---|---|
| User can select which sets they own | **Done** |
| User can choose a single game or an expedition | **Done** |
| User can start a new expedition or resume an in-progress one | **Done** |
| Before a battle, app displays the nemesis, and available mages and cards | **Partial** — displays correctly, but breaks permanently after any loss (§2.3) |
| Exactly 1 nemesis, 9 supply cards, 1–4 mages per battle | **Partial** — 9 cards enforced in the UI only; **mage selection does not exist**; quickplay's `num_mages` is unvalidated server-side |
| _Expedition:_ user can swap out cards in the barracks | **Partial** — checkboxes render, nothing is ever submitted |
| _Expedition:_ lock in choices, remaining player cards banished (unless Big Pockets) | **Not done** — endpoint exists but validates nothing and is never called |
| _Expedition:_ user inputs win or loss | **Not done** — endpoint exists, no UI wiring |
| _Expedition:_ on win, +1 gem/relic/spell, battle number advances, new nemesis | **Done** (backend) |
| _Expedition:_ on loss, user picks treasure/mage/card, then repeats the fight | **Partial** — backend draws correctly but leaves the expedition unresumable; the UI picker is a `{/* temp */}` stub |
| Completed expeditions no longer appear as in-progress | **Done** |
| User can abandon/delete an in-progress expedition | **Not done** — endpoint exists, returns `200` for unknown ids, no UI |

Out of scope per the spec: treasures, legacy content filtering, Outcasts mode.
Multi-user is a confirmed post-MVP concern.

---

## 2. Verified defects

Each reproduced against a live Postgres using the repo's own test fixtures.

### 2.1 The frontend does not compile

`npm run build` fails with 3 `TS6133` errors in `ExpeditionView.tsx`;
`npm run lint` reports 5 errors. CI runs only backend pytest, so nothing has
ever exercised `tsc`. `frontend/Dockerfile` runs `npm run dev`, so there is no
production build path either.

### 2.2 The expedition play loop is a stub

`ExpeditionView.tsx` is the only page that implements the headline feature, and
none of its buttons reach the API — "Lock Supply", "Win" and "Loss" call
`setPhase(...)` on local state only. The post-win draw renders an empty
`<h1>New Supply Cards:</h1>`; the loss randomizer picker is a comment placeholder.
`api.ts` has no `resolveBattle`, `lockSupply` or `deleteExpedition` client.
**An expedition cannot be played past creation.**

### 2.3 A lost battle makes the expedition unresumable

`resolve_battle` sets `result='loss'` on the current `ExpeditionBattle`, leaves
`current_battle` alone, and creates no replacement row:

```
BATTLES AFTER LOSS: [{'battle_number': 1, 'result': 'loss', 'nemesis': {...}}]
PENDING BATTLES:    []
```

The frontend locates the current battle with `battles.find(b => b.result === null)`,
which now returns `undefined`. The nemesis disappears and the expedition is dead.
A second loss returns 200, silently overwrites the same row (history shows one
loss, not two), but still grants the randomizer — barracks grew 9 → 10 → 11.

### 2.4 Per-battle mage selection is missing entirely

The spec requires choosing 1–4 mages per battle, with unused mages **returned to
the barracks** (unlike supply cards, mages are never banished). The UI lists all
expedition mages with no selection mechanism, and nothing is persisted.

### 2.5 `lock-supply` validates nothing

No check that submitted ids belong to this expedition or are currently in the
barracks. No check that exactly 9 remain. Silently returns 200 unchanged when the
barracks is already ≤ 9, so a caller cannot distinguish "nothing to banish" from
"banish applied". Nothing forces a lock before the next `resolve-battle`.

### 2.6 Smaller confirmed issues

- `DELETE /expeditions/{id}` returns `200 null` for ids that do not exist.
- README documents `big_pockets`; the enum is `big-pockets`, so the documented
  request returns `422`. The variant is also absent from the `NewExpedition`
  dropdown, so it is unreachable from the UI.
- `resolve_battle` types `loss_randomizer_type` as `Optional`, but a null falls
  into the `is not TREASURE` branch and then crashes on `.value`.
- `GET /expeditions/active` raises 404 on an empty list and is never called.
- `app/routers/cards.py` is a 0-byte file registered nowhere.
- `api.ts` never checks `res.ok`, so error bodies become "data" and React Query
  renders no error state.
- CORS hard-codes an EC2 IP address.
- No tests for `/quickplay` or `/sets`; none for the frontend.
- `backend/ingestion/cache/` is gitignored, so a fresh clone pays the full
  multi-minute rate-limited wiki scrape.

### 2.7 Rules confirmed correct — do not "fix" these

Checked against the spec document; the current behaviour is right:

- **Banishing is permanent** for the rest of the expedition. `draw_supply`
  excludes banished cards from all future draws. Correct.
- **Short expedition** skips battle 1 and draws the first nemesis from deck 2.
  `start_battle = 2` is correct.
- **Extended expedition** draws from deck 1 for battles 1–2, deck 2 for 3–4, and
  so on. `math.ceil(current_battle / 2)` is correct.
- **Big Pockets** banishes nothing. The early return in `lock_supply` is correct.
- **Treasures** are deliberately unhandled; `LossRandomizerType.TREASURE` as a
  no-op that still allows the retry is correct.

---

## 3. Decisions taken

| # | Decision |
|---|---|
| 1 | Banished cards are gone for the remainder of that expedition. Confirmed — current behaviour stands. |
| 2 | Expedition length is configurable: base 4 or 5. Extended is **always exactly double** the base, giving 8 or 10. A 9-battle extended is not supported. |
| 3 | Short expeditions start at battle 2. Confirmed — current behaviour stands. |
| 4 | Multi-user is post-MVP. The single global `UserSet` row set stays. |
| 5 | **Big Pockets becomes a separate boolean**, orthogonal to the others. `variant` narrows to `standard \| short \| extended`. Short + Big Pockets becomes a legal combination, matching the spec's framing of it as a banishing rule. |
| 6 | **Selected mages are persisted per battle**, so resuming mid-battle restores the choice and battle history shows who fought. |

---

## 4. Plan

Five phases, each leaving the repo in a working state.

### Phase 0 — Make the build honest (~0.5 day)

Nothing else is trustworthy while `tsc` fails and CI doesn't notice.

- Fix the 3 unused-binding errors in `ExpeditionView.tsx`. Do not delete the
  bindings — they are the unfinished wiring Phase 2 consumes.
- Fix the two `react-hooks/set-state-in-effect` lint errors in `SetSelection.tsx`
  and `ExpeditionView.tsx`. Both derive state from a query result; replace with a
  `useMemo` default plus a reset keyed on the battle id rather than on the whole
  `data` object. As written, `ExpeditionView`'s effect re-runs on every refetch
  and would wipe the user's selection mid-interaction once mutations exist.
- Add a `frontend` CI job: `npm ci`, `npm run lint`, `npm run build`.
- Add a multi-stage production target to `frontend/Dockerfile`, keeping the
  dev-server command for local compose.

**Done when:** build and lint exit 0, and CI enforces both.

### Phase 1 — Schema and state machine (~2–3 days)

One Alembic revision covering all of the following.

**1a. Configurable length.** Replace `MAX_EXP_LEN = 4` with an
`Expedition.base_length` column (validated 4 or 5). Effective length is
`base_length * 2` for extended, `base_length` otherwise; short runs battles
2..length. Completion fires when the winning battle number equals the effective
length.

Note that `base_length = 5` requires nemeses with `expedition_battle = 5`
(Beyond the Breach). `POST /expeditions` should verify the selected sets can
supply every tier the chosen length needs, and 400 with a useful message if not —
otherwise the expedition dies at the final battle.

**1b. Split Big Pockets out.** `Expedition.big_pockets: bool`; narrow the
`ExpeditionVariant` enum to `standard | short | extended`. Rename the enum value
spelling to snake_case while touching it, and update the README.

**1c. Model battle attempts.** One `ExpeditionBattle` row per *attempt*. On a
loss, set `result='loss'` on the current row and insert a new row with the same
`battle_number` and `nemesis_id` and `result=NULL`. This preserves loss history
and, importantly, preserves the invariant the frontend already relies on — the
pending battle is the one with a null result.

Follow-on edits:
- `resolve_battle` selects the battle by `battle_number == current_battle`, which
  is ambiguous once attempts repeat. Key it on `result == None` instead.
- Add an `attempt` field to `BattleDetail` so the UI can show "Battle 2, attempt 3".
- Confirm by test that a re-fought nemesis is not re-drawn at a later tier.

**1d. Persist selected mages.** New `expedition_battle_mages` join table keyed on
the attempt row. New `POST /expeditions/{id}/select-mages` (or fold it into
`lock-supply` as a single "lock in choices" call, which matches the spec's
wording — prefer this). Validate 1–4 mages, all drawn from the expedition's
barracks.

**1e. Validate `lock-supply`.** Rename to reflect that it locks the whole battle
setup (supply + mages):
- 400 if any submitted card id is not currently a barracks card of this expedition.
- 400 if the resulting barracks size is not exactly 9, skipping the check when
  `big_pockets` is set.
- 400 if the mage count is outside 1–4.
- Return the resulting state, not the bare expedition.

**1f. Guard `resolve-battle`.**
- 400 when the expedition is already `complete`.
- 400 when the battle setup was never locked.
- 400 when `won_battle` is false and `loss_randomizer_type` is missing.

**1g. Small corrections.** `DELETE` → 404 on missing, 204 on success. Validate
quickplay's `num_mages` to 1–4 server-side. Delete `app/routers/cards.py`. Either
wire `GET /expeditions/active` into the frontend or delete it; if kept, return
`[]` rather than 404.

**Done when:** a scripted run — win, loss, retry, win, through to completion —
leaves a coherent, resumable state at every step, for each variant and both lengths.

### Phase 2 — Wire the play loop (~3 days)

This is the MVP. Everything above exists to make it possible.

**2a. `api.ts`:** add `resolveBattle`, `lockBattleSetup`, `deleteExpedition`. Add
a shared `handle(res)` that throws on `!res.ok` using FastAPI's `detail` field,
and route every existing call through it. Without this, all the new 400s from
Phase 1 render as blank screens.

**2b. `ExpeditionView.tsx`** — the battle loop, driven by server state rather
than a local `useState` a refetch can desynchronise:

| Phase | Behaviour |
|---|---|
| `selecting` | Pick exactly 9 supply cards from the barracks **and 1–4 mages**. Card selection is skipped when `big_pockets` is set or the barracks is already at 9; mage selection always applies. |
| Lock in | `POST` the unselected card ids and the selected mage ids, invalidate, advance to `locked`. |
| `locked` | Show the locked 9-card supply, the chosen mages, and the nemesis. Win / Loss buttons. |
| Win | `POST { won_battle: true }`, diff the barracks before/after to name the 3 new randomizers, then → `selecting` for the next battle, or → `complete`. |
| Loss | Show the randomizer picker (gem / relic / spell / mage / treasure), `POST` the choice, name what was added, then → **`selecting`** for the retry. |
| `complete` | Finished state with the full battle history. |

The loss path returning to `selecting` rather than `locked` is load-bearing: the
spec says a retry repeats the start-of-fight rules, so the player re-picks supply
and mages and banishes again. After a loss the barracks holds 10 cards (9 + the
new randomizer), so one more gets banished on the retry.

**2c. Supporting UI:** render banished cards and battle history (`battles` is
already in the response and currently unused); add delete-expedition to
`ExpeditionResume` with a confirmation; add the Big Pockets toggle and the length
selector to `NewExpedition`; show battle number and variant per row on
`ExpeditionResume`.

**Done when:** a full expedition — including at least one loss and retry — can be
played start to finish in the browser, closed, and resumed.

### Phase 3 — Robustness and configuration (~1 day)

- Loading and error states on every page; today a failed fetch renders nothing.
- `VITE_API_URL` env var, falling back to the current `http://${hostname}:8000`.
- CORS origins from an env var instead of a hard-coded EC2 IP.
- Surface the backend's existing "not enough cards in selected sets" errors
  rather than failing silently.

### Phase 4 — Test and documentation debt (~1–1.5 days)

- Tests for `/quickplay` (respects saved sets, honours and validates `num_mages`,
  404 with no saved sets) and `/sets` (save/replace round-trip).
- New expedition tests: a loss leaves a pending battle; two losses record two
  attempts; lock rejects foreign ids, wrong card counts and bad mage counts;
  `resolve-battle` rejects an unlocked setup; delete 404s on unknown ids; each
  variant and both lengths run to completion; Short + Big Pockets combined.
- Sync `README.md`: variant spelling, the new `big_pockets` and `base_length`
  fields, the lock endpoint's request body (currently undocumented — a bare
  `list[int]`), and the delete status code.
- Commit `backend/ingestion/cache/` (drop it from `.gitignore`) so a fresh clone
  can seed without the rate-limited scrape. Biggest quality-of-life win for new
  setups and for any future CI integration test.

---

## 5. Sequencing

```
Phase 0  ──►  Phase 1  ──►  Phase 2  ──►  Phase 3  ──►  Phase 4
(build)      (schema +      (frontend     (polish)      (tests/docs)
              state)         play loop)
 ~0.5d         ~2-3d           ~3d          ~1d          ~1-1.5d
```

Roughly **7–9 working days**. Phases 0–2 (~5.5–6.5 days) get to "the specified
feature set actually works"; 3 and 4 make it maintainable.

Phase 2 must not start before 1c and 1d land — building the UI against the broken
loss flow, or against a battle model with no mage selection, means building it twice.

---

## 6. Deferred, with rationale

- **Treasures.** Explicitly out of scope. Two spec details are therefore no-ops
  the app may want to *mention* in the UI rather than implement: Short deals
  level-1 treasures at the start, and Extended deals treasures only after
  even-numbered battles. A one-line note on the battle screen would be enough.
- **Standalone vs Expansion boxes.** The spec defines the distinction but no
  requirement enforces it, and `Set` has no type column. Worth noting the failure
  mode: a user selecting only expansion boxes gets a set of cards they cannot
  actually play with. Post-MVP, but cheap to add later as a `Set.is_standalone`
  flag plus a warning on the set-selection screen.
- **Legacy content filtering** and **Outcasts mode.** Out of scope per both the
  spec and the README.
- **Multi-user.** Confirmed post-MVP. Worth flagging that the current single
  global `UserSet` row set means the AWS deployment shares one user's saved sets
  across every visitor — fine for a personal tool, but it is the first thing that
  will need to change once it is genuinely public.
