"""Attribution, count and visibility guarantees for real registrations.

Every person who registered through an affiliate referral link must be credited
to that affiliate, with the complete Google Form submission (identity, course,
payment information and payment proof) visible to the affiliate and to admins,
without ever duplicating a referral.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models import Referral, User, WebhookLog
from tests.conftest import TEST_WEBHOOK_SECRET, create_telegram_init_data

PROOF_URL = "https://drive.google.com/file/d/oduduwa-proof/view"

ANSWERS = [
    {"question": "Full Name", "answer": "Ade Bello"},
    {"question": "Email Address", "answer": "ade@example.com"},
    {"question": "Telegram Username", "answer": "@adebello"},
    {"question": "Phone Number", "answer": "08033334444"},
    {"question": "Course", "answer": "Cybersecurity"},
    {"question": "Class Preference", "answer": "Online"},
    {"question": "Payment Amount", "answer": "50000"},
    {"question": "Payment Method", "answer": "Bank Transfer"},
    {"question": "Payment Reference", "answer": "SMC-PAY-9001"},
    {"question": "Payment Screenshot", "answer": PROOF_URL},
]


async def _authenticate(client: AsyncClient, telegram_id: int, username: str) -> dict:
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


def _headers(session: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(telegram_id=930001, username="attribution_admin", is_admin=True)
    db_session.add(admin)
    await db_session.commit()
    return {
        "Authorization": f"Bearer {create_access_token({'sub': str(admin.id), 'telegram_id': admin.telegram_id})}"
    }


async def _post_webhook(client: AsyncClient, payload: dict):
    response = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _reconcile(client: AsyncClient, submissions: list[dict], dry_run: bool = False):
    response = await client.post(
        "/api/v1/webhooks/google-form/reconcile",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json={"dry_run": dry_run, "responses": submissions},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _rows(db_session: AsyncSession, referrer_id: int) -> list[Referral]:
    return (
        await db_session.execute(
            select(Referral).where(Referral.referrer_id == referrer_id)
        )
    ).scalars().all()


@pytest.mark.asyncio
async def test_webhook_credits_affiliate_from_a_referral_link_answer(
    client: AsyncClient, db_session: AsyncSession
):
    """The referral code embedded in the shared link still credits the affiliate."""
    affiliate = await _authenticate(client, 910001, "oduduwa_link")
    link = f"https://smc-academy-referral.onrender.com/r/{affiliate['referral_code']}"

    result = await _post_webhook(
        client,
        {
            "response_id": "link-answer-1",
            "referral_code": "",
            "submitted_at": "2026-09-22T18:30:00Z",
            "answers": ANSWERS + [{"question": "How did you hear about us?", "answer": link}],
        },
    )

    assert result["success"] is True
    rows = await _rows(db_session, affiliate["user"]["id"])
    assert len(rows) == 1
    assert rows[0].candidate_email == "ade@example.com"
    assert rows[0].candidate_telegram_handle == "@adebello"
    assert rows[0].registered_at.isoformat().startswith("2026-09-22")


@pytest.mark.asyncio
async def test_webhook_normalizes_a_referral_link_in_the_code_field(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 910002, "oduduwa_code_field")
    link = f"https://smc-academy-referral.onrender.com/r/{affiliate['referral_code']}"

    result = await _post_webhook(
        client,
        {
            "response_id": "code-field-link-1",
            "referral_code": link,
            "submitted_at": "2026-09-22T19:00:00Z",
            "answers": ANSWERS,
        },
    )

    assert result["success"] is True
    assert len(await _rows(db_session, affiliate["user"]["id"])) == 1


@pytest.mark.asyncio
async def test_webhook_submission_without_any_code_is_rejected_and_logged(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 910003, "unattributable")

    result = await _post_webhook(
        client,
        {
            "response_id": "no-code-anywhere",
            "referral_code": "",
            "submitted_at": "2026-09-22T20:00:00Z",
            "answers": ANSWERS,
        },
    )

    assert result["success"] is False
    assert len(await _rows(db_session, affiliate["user"]["id"])) == 0
    log = (
        await db_session.execute(
            select(WebhookLog).where(
                WebhookLog.google_form_response_id == "no-code-anywhere"
            )
        )
    ).scalars().first()
    assert log is not None and log.status == "invalid_code"


@pytest.mark.asyncio
async def test_webhook_keeps_oversize_answers_instead_of_dropping_the_registration(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 910004, "long_answers")
    long_answer = "P" * 9000

    result = await _post_webhook(
        client,
        {
            "response_id": "oversize-answer",
            "referral_code": affiliate["referral_code"],
            "submitted_at": "2026-09-22T20:30:00Z",
            "answers": ANSWERS + [{"question": "Anything else?", "answer": long_answer}],
        },
    )

    assert result["success"] is True
    assert len(await _rows(db_session, affiliate["user"]["id"])) == 1


@pytest.mark.asyncio
async def test_reconciliation_creates_the_referral_from_a_referral_link_answer(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 910005, "oduduwa_historic")
    link = f"https://smc-academy-referral.onrender.com/r/{affiliate['referral_code']}"

    report = await _reconcile(
        client,
        [
            {
                "response_id": "historic-link-answer",
                "referral_code": "",
                "submitted_at": "2026-09-22T21:15:00Z",
                "answers": ANSWERS + [{"question": "Referral", "answer": link}],
            }
        ],
    )

    assert report["created"] == 1
    rows = await _rows(db_session, affiliate["user"]["id"])
    assert len(rows) == 1
    assert rows[0].google_form_response_id == "historic-link-answer"
    assert rows[0].registered_at.isoformat().startswith("2026-09-22")


@pytest.mark.asyncio
async def test_reconciliation_never_moves_an_existing_referral_to_another_affiliate(
    client: AsyncClient, db_session: AsyncSession
):
    owner = await _authenticate(client, 910006, "original_owner")
    other = await _authenticate(client, 910007, "other_affiliate")

    await _post_webhook(
        client,
        {
            "response_id": "attributed-once",
            "referral_code": owner["referral_code"],
            "candidate_email": "ade@example.com",
            "submitted_at": "2026-09-22T12:00:00Z",
        },
    )

    report = await _reconcile(
        client,
        [
            {
                "response_id": "attributed-once",
                "referral_code": other["referral_code"],
                "submitted_at": "2026-09-23T09:00:00Z",
                "answers": ANSWERS,
            }
        ],
    )

    assert report["enriched"] == 1
    assert report["created"] == 0
    owner_rows = await _rows(db_session, owner["user"]["id"])
    assert len(owner_rows) == 1
    assert owner_rows[0].google_form_response_id == "attributed-once"
    # The original submission timestamp is kept, not replaced by the re-import.
    assert owner_rows[0].registered_at.isoformat().startswith("2026-09-22")
    assert await _rows(db_session, other["user"]["id"]) == []


@pytest.mark.asyncio
async def test_duplicate_response_ids_cannot_create_duplicate_referrals(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 910008, "duplicate_guard")
    submission = {
        "response_id": "duplicate-response",
        "referral_code": affiliate["referral_code"],
        "submitted_at": "2026-09-22T22:00:00Z",
        "answers": ANSWERS,
    }

    first = await _reconcile(client, [submission])
    second = await _reconcile(client, [submission])
    both_at_once = await _reconcile(client, [submission, submission])

    assert first["created"] == 1
    assert second["created"] == 0
    assert both_at_once["created"] == 0
    assert len(await _rows(db_session, affiliate["user"]["id"])) == 1


@pytest.mark.asyncio
async def test_referral_counts_match_the_actual_referral_rows(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 910009, "counting_affiliate")
    admin_headers = await _admin_headers(db_session)

    for index in range(2):
        await _post_webhook(
            client,
            {
                "response_id": f"counted-{index}",
                "referral_code": affiliate["referral_code"],
                "submitted_at": "2026-09-22T23:00:00Z",
                "answers": ANSWERS,
            },
        )

    rows = await _rows(db_session, affiliate["user"]["id"])
    assert len(rows) == 2

    dashboard = (await client.get("/api/v1/user/dashboard", headers=_headers(affiliate))).json()
    assert dashboard["total_verified_referrals"] == len(rows)

    listing = (await client.get("/api/v1/referrals", headers=_headers(affiliate))).json()
    assert listing["total"] == len(rows)

    affiliates = (await client.get("/api/v1/admin/affiliates", headers=admin_headers)).json()
    listed = next(row for row in affiliates if row["id"] == affiliate["user"]["id"])
    assert listed["referral_count"] == len(rows)

    detail = (
        await client.get(
            f"/api/v1/admin/affiliates/{affiliate['user']['id']}", headers=admin_headers
        )
    ).json()
    assert detail["referral_count"] == len(rows)


@pytest.mark.asyncio
async def test_affiliate_and_admin_see_the_complete_submission(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 910010, "visibility_affiliate")
    admin_headers = await _admin_headers(db_session)

    await _post_webhook(
        client,
        {
            "response_id": "visibility-1",
            "referral_code": affiliate["referral_code"],
            "submitted_at": "2026-09-22T23:30:00Z",
            "answers": ANSWERS,
        },
    )

    listing = (await client.get("/api/v1/referrals", headers=_headers(affiliate))).json()
    referral_id = listing["referrals"][0]["id"]

    for url, headers in (
        (f"/api/v1/referrals/{referral_id}", _headers(affiliate)),
        (f"/api/v1/admin/referrals/{referral_id}", admin_headers),
    ):
        payload = (await client.get(url, headers=headers)).json()
        fields = {field["label"]: field for field in payload["form_fields"]}
        assert fields["Full Name"]["value"] == "Ade Bello"
        assert fields["Course"]["value"] == "Cybersecurity"
        assert fields["Class Preference"]["value"] == "Online"
        assert fields["Payment Amount"]["value"] == "50000"
        assert fields["Payment Method"]["value"] == "Bank Transfer"
        assert fields["Payment Reference"]["value"] == "SMC-PAY-9001"
        assert fields["Payment Screenshot"]["value"] == PROOF_URL
        assert fields["Payment Screenshot"]["is_link"] is True

    admin_detail = (
        await client.get(f"/api/v1/admin/referrals/{referral_id}", headers=admin_headers)
    ).json()
    assert admin_detail["referrer"]["username"] == "visibility_affiliate"
    assert admin_detail["referral_code"] == affiliate["referral_code"]
    assert admin_detail["payment_proof_url"] == PROOF_URL
