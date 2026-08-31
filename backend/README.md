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
- **`WebhookLog`**: Audit log recording raw payloads, status (`processed`, `duplicate`, `invalid_code`, `unauthorized`), error messages, and timestamps.

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
