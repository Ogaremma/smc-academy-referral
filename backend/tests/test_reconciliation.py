"""Historical Google Form reconciliation tests.

These cover the real-world scenario: registrations that arrived before the
webhook carried the full Google Form answers must be recovered from the form /
sheet source data without duplicating or resetting any existing referral.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models import Referral
from app.db.models import User
from tests.conftest import TEST_WEBHOOK_SECRET, create_telegram_init_data

RECONCILE_URL = "/api/v1/webhooks/google-form/reconcile"
PROOF_URL = "https://drive.google.com/file/d/historic123/view"

ANSWERS = [
    {"question": "Full Name", "answer": "Historic Person"},
    {"question": "Phone Number", "answer": "08122223333"},
    {"question": "Program", "answer": "Product Design"},
    {"question": "Class Preference", "answer": "Offline"},
    {"question": "Payment Reference", "answer": "HIST-777"},
    {"question": "Payment Screenshot", "answer": PROOF_URL},
]


async def _authenticate(client: AsyncClient, telegram_id: int, username: str):
    response = await client.post(
        "/api/v1/auth/telegram",
        json={
            "init_data": create_telegram_init_data(
                user_dict={"id": telegram_id, "username": username}
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def _headers(affiliate: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {affiliate['access_token']}"}


def _submission(**overrides) -> dict:
    payload = {
        "response_id": "legacy-response-1",
        "referral_code": "SMC-UNSET",
        "candidate_email": "historic@example.com",
        "candidate_telegram_handle": "@historic",
        "submitted_at": "2026-08-01T10:00:00Z",
        "answers": ANSWERS,
    }
    payload.update(overrides)
    return payload


async def _legacy_submission(client: AsyncClient, code: str, response_id: str):
    """Recreate a pre-fix submission: attribution envelope, no answers."""
    response = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json={
            "response_id": response_id,
            "referral_code": code,
            "candidate_email": "historic@example.com",
            "candidate_telegram_handle": "@historic",
            "submitted_at": "2026-08-01T10:00:00Z",
        },
    )
    assert response.status_code == 200
    return response.json()


async def _reconcile(client: AsyncClient, responses: list[dict], dry_run: bool = False):
    response = await client.post(
        RECONCILE_URL,
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json={"dry_run": dry_run, "responses": responses},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _referral_count(db_session: AsyncSession, referrer_id: int) -> int:
    rows = (
        await db_session.execute(
            select(Referral).where(Referral.referrer_id == referrer_id)
        )
    ).scalars().all()
    return len(rows)


@pytest.mark.asyncio
async def test_legacy_referral_is_enriched_without_duplication(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 820001, "historic_affiliate")
    await _legacy_submission(client, affiliate["referral_code"], "legacy-response-1")

    before = (await client.get("/api/v1/referrals", headers=_headers(affiliate))).json()
    assert before["total"] == 1
    detail_before = (
        await client.get(f"/api/v1/referrals/{before['referrals'][0]['id']}", headers=_headers(affiliate))
    ).json()
    assert all(field["label"] != "Full Name" for field in detail_before["form_fields"])

    report = await _reconcile(
        client, [_submission(referral_code=affiliate["referral_code"])]
    )
    assert report["enriched"] == 1
    assert report["created"] == 0

    # No second referral row, and the original attribution is untouched.
    assert await _referral_count(db_session, affiliate["user"]["id"]) == 1
    after = (await client.get("/api/v1/referrals", headers=_headers(affiliate))).json()
    assert after["total"] == 1
    assert after["referrals"][0]["id"] == before["referrals"][0]["id"]

    detail = (
        await client.get(f"/api/v1/referrals/{after['referrals'][0]['id']}", headers=_headers(affiliate))
    ).json()
    fields = {field["label"]: field for field in detail["form_fields"]}
    assert fields["Full Name"]["value"] == "Historic Person"
    assert fields["Program"]["value"] == "Product Design"
    assert fields["Payment Screenshot"]["value"] == PROOF_URL
    # Original submission timestamp is preserved.
    assert detail["registered_at"].startswith("2026-08-01")


@pytest.mark.asyncio
async def test_reconciliation_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    affiliate = await _authenticate(client, 820002, "idempotent_affiliate")
    await _legacy_submission(client, affiliate["referral_code"], "legacy-response-1")
    payload = [_submission(referral_code=affiliate["referral_code"])]

    first = await _reconcile(client, payload)
    second = await _reconcile(client, payload)

    assert first["enriched"] == 1
    assert second["unchanged"] == 1
    assert second["created"] == 0
    assert await _referral_count(db_session, affiliate["user"]["id"]) == 1


@pytest.mark.asyncio
async def test_missing_referral_is_created_from_the_sheet_submission(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 820003, "create_affiliate")

    report = await _reconcile(
        client, [_submission(referral_code=affiliate["referral_code"])]
    )
    assert report["created"] == 1
    assert report["results"][0]["referral_id"] is not None

    dashboard = (
        await client.get("/api/v1/user/dashboard", headers=_headers(affiliate))
    ).json()
    assert dashboard["total_verified_referrals"] == 1

    listing = (await client.get("/api/v1/referrals", headers=_headers(affiliate))).json()
    assert listing["total"] == 1
    detail = (
        await client.get(f"/api/v1/referrals/{listing['referrals'][0]['id']}", headers=_headers(affiliate))
    ).json()
    fields = {field["label"]: field["value"] for field in detail["form_fields"]}
    assert fields["Full Name"] == "Historic Person"
    assert fields["Payment Reference"] == "HIST-777"
    assert detail["registered_at"].startswith("2026-08-01")

    # A second run must not create a duplicate.
    again = await _reconcile(
        client, [_submission(referral_code=affiliate["referral_code"])]
    )
    assert again["created"] == 0
    assert await _referral_count(db_session, affiliate["user"]["id"]) == 1


@pytest.mark.asyncio
async def test_dry_run_reports_without_writing(client: AsyncClient, db_session: AsyncSession):
    affiliate = await _authenticate(client, 820004, "dryrun_affiliate")
    payload = [_submission(referral_code=affiliate["referral_code"])]

    preview = await _reconcile(client, payload, dry_run=True)
    assert preview["dry_run"] is True
    assert preview["created"] == 1
    assert await _referral_count(db_session, affiliate["user"]["id"]) == 0

    applied = await _reconcile(client, payload)
    assert applied["created"] == 1
    assert await _referral_count(db_session, affiliate["user"]["id"]) == 1


@pytest.mark.asyncio
async def test_unmatched_submissions_are_reported_and_not_created(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 820005, "unmatched_affiliate")

    report = await _reconcile(
        client,
        [
            _submission(response_id="no-code", referral_code=""),
            _submission(response_id="unknown-code", referral_code="SMC-NOPE99"),
        ],
    )
    assert report["unmatched"] == 2
    assert report["created"] == 0
    reasons = {item["response_id"]: item["reason"] for item in report["results"]}
    assert "No referral code" in reasons["no-code"]
    assert "does not exist" in reasons["unknown-code"]
    assert await _referral_count(db_session, affiliate["user"]["id"]) == 0


@pytest.mark.asyncio
async def test_reconciliation_matches_by_identity_without_duplicating(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 820006, "identity_affiliate")
    await _legacy_submission(client, affiliate["referral_code"], "legacy-response-9")

    # Same candidate (email + Telegram) but a different response id.
    report = await _reconcile(
        client,
        [
            _submission(
                response_id="legacy-response-different",
                referral_code=affiliate["referral_code"],
            )
        ],
    )
    assert report["enriched"] == 1
    assert report["created"] == 0
    assert await _referral_count(db_session, affiliate["user"]["id"]) == 1


@pytest.mark.asyncio
async def test_reconciliation_requires_webhook_secret(client: AsyncClient):
    response = await client.post(
        RECONCILE_URL,
        json={"responses": [_submission(referral_code="SMC-ANY")]},
    )
    assert response.status_code == 401


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(telegram_id=829001, username="reconcile_admin", is_admin=True)
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id), "telegram_id": admin.telegram_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_submission_health_reports_and_clears_missing_answers(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 820007, "health_affiliate")
    await _legacy_submission(client, affiliate["referral_code"], "legacy-response-1")
    admin_headers = await _admin_headers(db_session)

    before = (
        await client.get("/api/v1/admin/referrals/submission-health", headers=admin_headers)
    ).json()
    assert before["referrals_missing_answers"] == 1
    assert before["missing"][0]["response_id"] == "legacy-response-1"
    assert before["missing"][0]["affiliate"]["username"] == "health_affiliate"

    await _reconcile(client, [_submission(referral_code=affiliate["referral_code"])])

    after = (
        await client.get("/api/v1/admin/referrals/submission-health", headers=admin_headers)
    ).json()
    assert after["referrals_missing_answers"] == 0
    assert after["missing"] == []


@pytest.mark.asyncio
async def test_submission_health_requires_admin(client: AsyncClient):
    affiliate = await _authenticate(client, 820008, "health_denied")
    response = await client.get(
        "/api/v1/admin/referrals/submission-health", headers=_headers(affiliate)
    )
    assert response.status_code == 403
