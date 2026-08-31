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
