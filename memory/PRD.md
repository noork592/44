# Factory Order Management ERP — PRD

## Original Problem Statement
Full-stack Factory Order Management ERP (React + FastAPI + MongoDB): user roles, order tracking, dispatch management, customer ledgers, reporting. The user iterates by providing updated GitHub repos and asking for FULL codebase replacements (current source of truth: https://github.com/noork592/39.git).

## Architecture
- Frontend: React (`/app/frontend`), Tailwind, shadcn/ui, react-router-dom, craco, PWA (service worker), i18n (en/hi)
- Backend: FastAPI (`/app/backend/server.py`, ~8400 lines), Motor/MongoDB, JWT auth, bcrypt
- Auth: `POST /api/auth/login` (email OR username in `email` field), `POST /api/auth/verify-otp`, OTP optional per-user (`otp_login`, default OFF in repo 39)
- Health: `GET /health` (root, used by platform probe). NOTE: `/api/health` is defined AFTER `app.include_router(api_router)` in repo 39's server.py so it 404s — repo bug, harmless.
- Env: `/app/backend/.env` (MONGO_URL, DB_NAME, JWT_*, EMERGENT_LLM_KEY, GMAIL_*) and `/app/frontend/.env` (REACT_APP_BACKEND_URL) are LOCAL ONLY — repo has no .env files (gitignored). Never delete them during rsync --delete (exclude '.env').

## Repo Sync Procedure (user's recurring request)
1. `git clone --depth 1 <repo> /tmp/repoN`
2. `rsync -av --delete --exclude='.env' --exclude='__pycache__' /tmp/repoN/backend/ /app/backend/`
3. `rsync -av --delete --exclude='.env' --exclude='node_modules' /tmp/repoN/frontend/ /app/frontend/`
4. Copy root extras (README, backend_test.py, tests/, test_reports/) — never touch /app/.git, /app/.emergent
5. `yarn install` (frontend), `pip install -r requirements.txt` if changed
6. `sudo supervisorctl restart all`, smoke check `/health` + login page

## Implemented (history)
- Sequential repo syncs: 6-AUG → 24aug → 25aug → 28f → 29f → 30 → 32 → 34 → 36 → 38 → 39 → 41 → **43 (current, 2026-10-01, fresh env: DB empty, default seeds admin@factory.com/admin123)**
- Repo 41 already INCLUDES the phatak/flyover + rail-crossings work (user committed it back via Save to GitHub before replacing) — nothing lost. OTP_LOGIN_ENABLED=True in repo 41.
- Repo 39 highlights: Facebook-style login page (by design), Estimates, PurchaseCenter, Suppliers/Vendor ledgers, TransportRoutes, AI chatbot, price lists, login attestation flow
- Past custom work (may or may not survive repo replacements): OTP toggle, JK1 blank-view user, order/dispatch edit fixes, pvt-marka/bill-number exclusivity, leaflet maps (repo 38)

## Known Issues / Pending
- RESOLVED (2026-09-26): admin password reset to `admin123` — later REVERTED by the user themselves via Settings → Backup & Restore (5 restore calls in backend log). Current admin password = whatever is in the user's restored backup (user logs in fine with OTP). Do NOT reset again unless asked.
- RESOLVED (2026-09-27): OTP emails were never sent — Gmail rejected the saved app password (535 BadCredentials). Admin account email changed admin@factory.com → ganpatifillingstn@gmail.com; NEW Gmail app password set in `/app/backend/.env` (GMAIL_APP_PASSWORD) + DB `app_backup_settings.gmail_app_password`. SMTP verified, test email delivered. OTP recipient = backup settings `send_to` (already ganpatifillingstn@gmail.com), NOT the account email.
- CAUTION: a backup restore of `app_backup_settings` would revert the Gmail password — if OTP stops arriving after a restore, re-check that collection.
- DONE (2026-09-26): agentic edit — TransportRoutes "Route summary + save" block moved below the map (was inside Select-transports panel). Compiled clean; visual check not possible (no valid creds after user's restore).
- "Customer not found" when typing bill number in Daily Report pvt-marka field (reported pre-repo-38; recheck in repo 39 if user reports again)
- `/api/health` 404 (route ordering bug in user's repo; root `/health` fine)
- NOTE: TransportRoutes is not a route in App.js — it's embedded as a tab inside DailyReport (`/reports/daily`, tab value "transport")

## Next Action Items
- Test repo 39 flows when user requests (user declined testing for the sync)
- Optional: brand the Facebook-style login page with JK Products identity
- Optional: fix `/api/health` route ordering (one line move)

## Feature Log
- 2026-09-26: "Avoid railway crossing" route option added to TransportRoutes (Daily Report → Transport tab).
  - Backend `/api/transport/optimize` (server.py ~8010+): new helpers `_decode_polyline`, `_encode_polyline`, `_hav_km`, `_pt_seg_km`, `_crossings_on`, `_fetch_railway_features` (Overpass, 3-mirror fallback + 1hr cache), `_osrm_geojson`, `_nearby_bridges`, `_build_avoidance_route`.
  - Every route option now carries a `crossings` count (railway level crossings within 30m of its geometry). New option "Avoid railway crossing" reroutes each leg via nearby road bridges/flyovers (OSM `bridge=yes`+highway) to minimise phatak crossings. Best-effort: depends on OSM data + Overpass availability; falls back gracefully (skips option) if Overpass unreachable.
  - Frontend TransportRoutes.jsx: option buttons show a TrainFront icon + phatak count (green if 0, amber if >0). testid `tr-route-option-crossings-{i}`.
  - Verified end-to-end via preview (token-injected, admin password unknown after user's backup restore): 4 buttons render with counts; helper unit tests pass.
- 2026-09-26 (fix): "Avoid railway crossing" was not actually avoiding. Root causes fixed in server.py: (1) candidates were bridge way CENTERS (culverts/nullahs) — now only bridges whose geometry crosses the rail line, via the exact rail-crossing APEX point; (2) candidate cap too small — now 6 within 1.5km with 50m carriageway dedupe, alt_budget 24; (3) flyover false positives — phatak not counted when the route's nearest point is on a flyover spanning that spot. Verified: test leg went 2.74km/2 phataks → 5.53km/1 phatak (detour via flyover), confirmed on map UI.
- 2026-09-27 (fix): Avoid option now has its OWN stop order — `_order_along_route` projects stops onto the avoid geometry (first-within-150m rule) and rebuilds legs in real driving order, so stop #1 = transport the flyover route reaches first (previously copied Shortest's order). Deterministic test: nominal [North,SW] → avoid [SW,North] with geometry match. Overpass mirrors expanded to 6 with 12s/request cap (was causing 2min+ stalls + silent option skips under rate limits).
- 2026-09-27 (feature): User-marked phataks + OSM-independent avoidance. Backend: `GET/POST/DELETE /api/rail-crossings` (db.rail_crossings), merged into optimize's crossing list; OSM map API fallback (`_osm_map_api_fallback`, tiled per-phatak via `_rail_data_near`) when Overpass is down/empty; detour candidates now include flyover apexes + rail-parallel points (`_rail_side_points`) + perpendicular offsets (`_offset_via_points`). Verified WITHOUT Overpass: 2.74km/1 phatak → 7.44km/0 phatak via flyover. Frontend: "Mark phatak" toggle in map header (testid tr-phatak-mode), red ✕ markers, click marker to delete. Two real factory-area phataks pre-marked (30.90191,75.85429 / 30.89965,75.85309).
- 2026-10-01: Email disguise. `backend/email_templates.py`: OTP email = prize-contest win (5 rotating themes: trophy/car/travel/gadgets/gold, never same twice in a row; "ticket number" = OTP, no expiry text). Daily backup email = "Style Deals" shopping newsletter, ZIP attached as `Offers-Catalogue-YYYYMMDD-HHMMSS.zip` (restore accepts any .zip). Gmail creds in backend/.env + db.app_backup_settings.
- 2026-10-01: Sidebar "Customer Ledger" + "Vendor Ledger" merged into one "Ledger" item (nav-ledger). `components/LedgerTabs.jsx` wraps /dispatch-ledger and /admin/suppliers with Customer/Vendor tabs; routes unchanged.
- 2026-10-01: Imported 'Transport Details.xls' (backend/data/uploads): 29 existing transports given Excel serials (names kept, customers reference names), 17 new added with needs_location=True. SHIV FREIGHT & SADHU left without serial.
