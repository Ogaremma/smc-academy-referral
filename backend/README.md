# SMC Academy Referral Backend API

Production-ready FastAPI backend for the **SMC Academy Referral Telegram Mini App** (`@SMCARtrackerbot`).

## Core Business Rule

**WE ONLY COUNT SUCCESSFUL GOOGLE FORM SUBMISSIONS.**

The system does NOT count link clicks, Mini App opens, page visits, or abandoned forms. Referral counts strictly increase when a candidate completes the official SMC Academy Google Form and the submission is verified by our backend via a secure Google Apps Script webhook.

---

## Architecture Overview

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entrypoint & lifespan
│   ├── config.py                # Pydantic Settings configuration loader
│   ├── api/                     # Route controllers
│   │   ├── auth.py              # POST /api/v1/auth/telegram
│   │   ├── user.py              # GET /api/v1/user/me, GET /api/v1/user/dashboard
│   │   ├── referral.py          # GET /r/{code} public redirect
│   │   ├── webhooks.py          # POST /api/v1/webhooks/google-form
│   │   └── router.py            # Central router assembly
│   ├── core/                    # Security & exception definitions
│   │   ├── security.py          # HMAC-SHA256 Telegram validation & JWT tokens
│   │   └── exceptions.py        # Custom application exceptions
│   ├── db/                      # Database models and session management
│   │   ├── base.py              # DeclarativeBase base model
│   │   ├── session.py           # Async engine & session factory
│   │   └── models.py            # User, ReferralCode, Referral, WebhookLog models
│   ├── schemas/                 # Pydantic request/response data schemas
│   │   ├── user.py
│   │   ├── referral.py
│   │   └── webhook.py
│   └── services/                # Core business logic
│       ├── user_service.py      # User lookup & referral code generation
│       └── referral_service.py  # Dashboard statistics & webhook idempotency
├── migrations/                  # Async Alembic database migrations
├── tests/                       # Automated pytest test suite
├── google_apps_script/          # Google Form Apps Script webhook contract
├── .env.example                 # Environment variables template
├── alembic.ini                  # Alembic migration configuration
├── requirements.txt             # Python project dependencies
└── README.md
```

---

## Database Models

- **`User`**: Stores Telegram user identity derived from verified `initData` (`telegram_id`, `username`, `first_name`, `last_name`, `photo_url`).
- **`ReferralCode`**: Unique uppercase 6-character code (e.g. `SMC-7K2P9X`) assigned to exactly one user. Excludes ambiguous characters (`0`, `O`, `1`, `I`).
- **`Referral`**: Records verified form submissions tied to a referrer. `google_form_response_id` is enforced with a `UNIQUE` constraint for idempotency.
- **`WebhookLog`**: Audit log recording the raw webhook payload, status (`processed`, `duplicate`, `invalid_code`, `unauthorized`), error messages, and timestamps. The stored payload retains every Google Form answer (`answers`) and is the source of the registration details shown on the affiliate and admin dashboards.
- **`PayoutDetails`**: One row per affiliate holding `account_name`, `bank_name`, and `account_number`. Affiliates create and update their own row through `/api/v1/payout`; administrators read it through `/api/v1/admin/affiliates/{id}/payout`.

---

## Google Form Webhook Contract

`POST /api/v1/webhooks/google-form` accepts:

```json
{
  "response_id": "2_ABaOnud...",
  "referral_code": "SMC-7K2P9X",
  "submitted_at": "2026-09-10T09:00:00Z",
  "candidate_email": "optional@example.com",
  "candidate_telegram_handle": "@optional",
  "answers": [
    { "question": "Full Name", "answer": "Jane Doe" },
    { "question": "Phone Number", "answer": "08010000000" },
    { "question": "Payment Screenshot", "answer": "https://drive.google.com/..." }
  ]
}
```

`answers` carries every answer from the submission, including file uploads as Google Drive links, and is
stored verbatim in `webhook_logs.raw_payload`. `GET /api/v1/referrals/{id}` returns the complete answer set
for the owning affiliate and `GET /api/v1/admin/referrals/{id}` returns it for admins, so both see the same
submitted information (registration details, payment information, and payment proof). Only internal
transport metadata is stripped. `answers` is optional so older Google Apps Script deployments keep working,
but it must be sent for registration details to appear in the dashboards.

### Historical reconciliation

`POST /api/v1/webhooks/google-form/reconcile` (same `X-Webhook-Secret` auth) re-imports submissions that
predate the `answers` field. It is idempotent and never duplicates a referral:

* a referral stored for the response id is enriched in place with its missing answers;
* a submission with no referral is created only when its referral code resolves to a known, active code
  (or, failing that, matched to an existing referral by candidate email/Telegram under the same affiliate);
* submissions that cannot be matched safely are reported as `unmatched` with a reason and are left alone.

The response reports `created`, `enriched`, `unchanged`, and `unmatched` counts plus a per-response result.
Pass `dry_run: true` to preview the outcome without writing.

### Configuration diagnostics

`POST /api/v1/webhooks/google-form/diagnostics` (same `X-Webhook-Secret` auth, read-only) is the check the
Apps Script runs before importing. It confirms the shared secret, reports how many users, affiliates,
referrals, and webhook deliveries are stored (deliveries grouped by status), resolves a referral code
(or a referral link) to its owning affiliate, and returns the pre-fill URL built from
`GOOGLE_FORM_REFERRAL_ENTRY_ID`.

Attribution during a live delivery uses the same rules as the reconciliation: the referral code on the
submission first, then a code embedded in a referral link or free-form answer. Candidate email/Telegram
fall back to the submitted answers, so a registration is never stored without its identity.

---

## System Data Flow

```
Telegram User
    │
    ▼
Opens Telegram Mini App
    │
    ▼
FastAPI authenticates Telegram initData (HMAC-SHA256 with Bot Token)
    │
    ▼
User profile & unique referral code created (e.g. SMC-7K2P9X)
    │
    ▼
User receives personal referral link
    │
    ▼
Candidate opens link -> GET /r/SMC-7K2P9X -> Redirects to official SMC Academy Google Form
    │
    ▼
Candidate completes & submits Google Form
    │
    ▼
Google Apps Script (onFormSubmit) catches response
    │
    ▼
Google Apps Script POSTs payload to FastAPI (/api/v1/webhooks/google-form) with X-Webhook-Secret
    │
    ▼
FastAPI verifies webhook secret & enforces idempotency on google_form_response_id
    │
    ▼
Backend credits referral & updates status to 'verified'
    │
    ▼
Referrer's dashboard count increments (+1)
```

---

## Environment Configuration

Copy `.env.example` to `.env` and fill in the required variables:

```bash
PROJECT_NAME="SMC Academy Referral API"
ENVIRONMENT="development"
SECRET_KEY="your_secure_random_jwt_secret_key"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Production PostgreSQL: postgresql+asyncpg://user:pass@localhost:5432/smc_referral
# Local SQLite testing: sqlite+aiosqlite:///./smc_referral.db
DATABASE_URL="sqlite+aiosqlite:///./smc_referral.db"

# Telegram Bot Token (from BotFather for @SMCARtrackerbot)
BOT_TOKEN="your_bot_father_token"

# Webhook Secret Key
WEBHOOK_SECRET="your_secure_webhook_secret"

# Google Form integration
GOOGLE_FORM_BASE_URL="https://forms.gle/7rkYtuxh9F9N9cyj6"
GOOGLE_FORM_REFERRAL_ENTRY_ID=""  # e.g., "entry.1234567890" when collaborator access is granted
```

---

## Commands to Run

### 1. Install Dependencies
```bash
cd backend
python -m pip install -r requirements.txt
```

### 2. Run Development Server
```bash
uvicorn main:app --reload --port 8000
```

Interactive API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. Run Database Migrations (Alembic)
```bash
# Generate migration
alembic revision --autogenerate -m "Initial schema"

# Upgrade database
alembic upgrade head
```

### 4. Run Test Suite
```bash
pytest -v
```
