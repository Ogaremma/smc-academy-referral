# SMC Academy Referral — Telegram Mini App

A referral tracking system for SMC Academy, delivered as a **Telegram Mini App**.

## Architecture

```
Telegram Mini App (frontend)
        ↓
React + Vite frontend  (frontend/)
        ↓
FastAPI backend  (backend/)
        ↓
PostgreSQL (production) / SQLite (development)

──────────────────────────────────────────

Google Form (candidate registration)
        ↓
Google Apps Script  (google_apps_script/)
        ↓
POST /api/v1/webhooks/google-form
        ↓
Referral verified & recorded in database
        ↓
Dashboard shows: "X people registered via your link"
```

## Referral Flow

1. Referrer opens the Telegram Mini App and receives a personal referral link.
2. Referrer shares their link (e.g. `https://yourapi.com/r/SMC-7K2P9X`).
3. Candidate clicks the link and is redirected to the official SMC Academy Google Form, with the referral code **pre-filled** in the Referral field.
4. Candidate submits the form.
5. Google Apps Script detects the submission and sends a webhook to the FastAPI backend.
6. The backend validates the webhook secret, enforces idempotency, and records one verified referral.
7. The referrer's dashboard updates to show the new verified count.
8. Affiliates can review the submitted registration details for each referral, and administrators can open any referral to verify the full submission, including payment proof.

> **Important**: Only verified Google Form submissions are counted. There is no click tracking, leaderboard, or multi-level referral system.

## Project Structure

```
smcacademyreferral/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # Route handlers (auth, user, referral, webhooks)
│   │   ├── core/             # Security, JWT, exceptions
│   │   ├── db/               # SQLAlchemy models, session, base
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # Business logic (referral, user)
│   │   ├── config.py         # Pydantic Settings configuration
│   │   └── main.py           # FastAPI application entry point
│   ├── migrations/           # Alembic database migrations
│   ├── tests/                # Pytest test suite (12 tests)
│   ├── .env                  # Local secrets (NOT committed)
│   ├── .env.example          # Environment variable template
│   ├── alembic.ini           # Alembic configuration
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React + Vite + TypeScript + Tailwind CSS Mini App
│   ├── src/
│   │   ├── main.tsx          # React entry point
│   │   ├── App.tsx           # Root application component
│   │   └── index.css         # Global styles (Tailwind + glassmorphism)
│   ├── index.html            # HTML shell with Telegram WebApp SDK
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── google_apps_script/       # Google Apps Script webhook sender
    ├── Code.gs               # Triggered on form submission, calls webhook
    └── appsscript.json       # Apps Script manifest
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/telegram` | Authenticate via Telegram initData (HMAC-SHA256) |
| `GET`  | `/api/v1/user/me` | Get authenticated user profile & referral code |
| `GET`  | `/api/v1/user/dashboard` | Get verified referral count & activity |
| `GET`  | `/r/{code}` | Public redirect → Google Form with pre-filled referral code |
| `POST` | `/api/v1/webhooks/google-form` | Receive Google Form submission events |
| `GET`  | `/api/v1/referrals` | List this affiliate's referrals with submitted registration details |
| `GET`  | `/api/v1/referrals/{id}` | Referral detail for the owning affiliate (the complete submission, including payment information and proof) |
| `GET`  | `/api/v1/payout` | Read the affiliate's own payout details |
| `PUT`  | `/api/v1/payout` | Create or update the affiliate's own payout details |
| `GET`  | `/api/v1/admin/referrals` | List every referral across affiliates (admin) |
| `GET`  | `/api/v1/admin/referrals/{id}` | Full referral detail, including payment proof (admin) |
| `GET`  | `/api/v1/admin/affiliates/{id}/payout` | Affiliate payout details (admin) |
| `POST` | `/api/v1/webhooks/google-form/reconcile` | Idempotent backfill of historical form submissions (Apps Script) |
| `POST` | `/api/v1/webhooks/google-form/diagnostics` | Apps Script wiring check: secret, database, referral code, delivery counts |

## Visibility of submitted form data

The Google Form is the source of truth for a submission. The Apps Script sends
every non-empty answer (`answers: [{ question, answer }]`, including file
uploads as Google Drive links) and the backend stores the complete payload in
`webhook_logs.raw_payload`.

- **Affiliates** see the complete submission (registration information, payment
  information, payment proof, and every other answer) for referrals attributed
  to their own referral link. They never see another affiliate's referrals.
- **Admins** see the complete submission for every referral across all
  affiliates, plus the affiliate, referral code, and verification context.
- Internal transport metadata (webhook secret, tokens, database identifiers) is
  never exposed.

## Historical submission reconciliation

Registrations that arrived before the webhook carried the answers are recovered
with `POST /api/v1/webhooks/google-form/reconcile`. Before the first import, run
`verifyProductionSetup()` once from the Apps Script editor: it confirms
`BACKEND_WEBHOOK_URL` and `WEBHOOK_SECRET` against the live backend, reports how
many webhook deliveries have ever been recorded, resolves a referral code, and
prints every form question with its pre-fill entry id. Run
`installFormSubmitTrigger()` once as well: a live submission only reaches the
backend through an installable `onFormSubmit` trigger, because a simple trigger
cannot call `UrlFetchApp`. The Apps Script then exposes two entry points for the
history import:

1. `previewHistoricalSubmissions()` — dry run; reports what would change.
2. `backfillHistoricalSubmissions()` — applies the changes.

The reconciliation matches each response to an existing referral by
`response_id` (or, as a fallback, by the candidate's email/Telegram handle under
the same affiliate), enriches the referral with the answers it was missing, and
only creates a referral when the referral code on the submission resolves to a
known, active affiliate code. It never duplicates a referral, never overwrites
attribution, preserves the original submission timestamp, and reports anything
it could not match safely (for example a missing or unknown referral code)
instead of guessing.

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # Fill in BOT_TOKEN and WEBHOOK_SECRET
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Security

- Telegram `initData` validated with HMAC-SHA256 (`WebAppData` key derivation).
- JWT tokens for authenticated API calls.
- Webhook requests validated with a shared secret (constant-time compare).
- Webhook idempotency enforced by `google_form_response_id` uniqueness.
- Secrets are never committed — see `.env.example` for required variables.
