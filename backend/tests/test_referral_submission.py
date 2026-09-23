import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.models import Referral, User, WebhookLog
from tests.conftest import TEST_WEBHOOK_SECRET, create_telegram_init_data

PAYMENT_PROOF_URL = "https://drive.google.com/file/d/abc123/view"

ANSWERS = [
    {"question": "Full Name", "answer": "Person One"},
    {"question": "Email Address", "answer": "person1@example.com"},
    {"question": "Phone Number", "answer": "08010000001"},
    {"question": "Program", "answer": "Forex Trading"},
    {"question": "Class Preference", "answer": "Online"},
    {"question": "Payment Amount", "answer": "50000"},
    {"question": "Payment Method", "answer": "Bank Transfer"},
    {"question": "Payment Reference", "answer": "TRX-123"},
    {"question": "Payment Screenshot", "answer": PAYMENT_PROOF_URL},
    {"question": "How did you hear about us?", "answer": "A friend"},
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


async def _submit_form(client: AsyncClient, code: str, response_id: str, answers=None):
    response = await client.post(
        "/api/v1/webhooks/google-form",
        headers={"X-Webhook-Secret": TEST_WEBHOOK_SECRET},
        json={
            "response_id": response_id,
            "referral_code": code,
            "candidate_email": "person1@example.com",
            "candidate_telegram_handle": "@personone",
            "submitted_at": "2026-09-10T09:00:00Z",
            "answers": ANSWERS if answers is None else answers,
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    return response.json()


async def _admin_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = User(telegram_id=809001, username="submission_admin", is_admin=True)
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id), "telegram_id": admin.telegram_id})
    return {"Authorization": f"Bearer {token}"}


def _by_label(fields: list[dict]) -> dict[str, dict]:
    return {field["label"]: field for field in fields}


@pytest.mark.asyncio
async def test_google_form_answers_are_persisted_with_the_referral(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 800001, "persist_affiliate")
    await _submit_form(client, affiliate["referral_code"], "submission-persist")

    log = (
        await db_session.execute(
            select(WebhookLog).where(
                WebhookLog.google_form_response_id == "submission-persist",
                WebhookLog.status == "processed",
            )
        )
    ).scalars().first()
    assert log is not None
    assert "Payment Screenshot" in log.raw_payload
    assert PAYMENT_PROOF_URL in log.raw_payload

    referral = (
        await db_session.execute(
            select(Referral).where(
                Referral.google_form_response_id == "submission-persist"
            )
        )
    ).scalar_one()
    assert referral.referrer_id == affiliate["user"]["id"]
    assert referral.status == "verified"


@pytest.mark.asyncio
async def test_affiliate_sees_complete_submission_including_payment(
    client: AsyncClient,
):
    """The owning affiliate sees EVERY submitted Google Form answer."""
    affiliate = await _authenticate(client, 800010, "two_referrals")
    code = affiliate["referral_code"]
    headers = {"Authorization": f"Bearer {affiliate['access_token']}"}

    await _submit_form(client, code, "submission-one")
    await _submit_form(client, code, "submission-two")

    dashboard = await client.get("/api/v1/user/dashboard", headers=headers)
    assert dashboard.json()["total_verified_referrals"] == 2

    listing = (await client.get("/api/v1/referrals", headers=headers)).json()
    assert listing["total"] == 2
    assert listing["registered"] == 2
    assert {row["name"] for row in listing["referrals"]} == {"Person One"}
    assert {row["course"] for row in listing["referrals"]} == {"Forex Trading"}
    assert {row["email"] for row in listing["referrals"]} == {"person1@example.com"}
    assert all(row["registered_at"] is not None for row in listing["referrals"])

    for row in listing["referrals"]:
        detail = (
            await client.get(f"/api/v1/referrals/{row['id']}", headers=headers)
        ).json()
        assert detail["registered_at"] is not None
        assert detail["status"] == "verified"

        fields = _by_label(detail["form_fields"])
        # Registration information
        assert fields["Full Name"]["value"] == "Person One"
        assert fields["Email Address"]["value"] == "person1@example.com"
        assert fields["Phone Number"]["value"] == "08010000001"
        assert fields["Program"]["value"] == "Forex Trading"
        assert fields["Class Preference"]["value"] == "Online"
        # Payment information is NOT hidden from the affiliate.
        assert fields["Payment Amount"]["value"] == "50000"
        assert fields["Payment Amount"]["category"] == "payment"
        assert fields["Payment Method"]["value"] == "Bank Transfer"
        assert fields["Payment Reference"]["value"] == "TRX-123"
        proof = fields["Payment Screenshot"]
        assert proof["value"] == PAYMENT_PROOF_URL
        assert proof["category"] == "payment"
        assert proof["is_link"] is True
        # Any other submitted answer is preserved too.
        assert fields["How did you hear about us?"]["value"] == "A friend"

        # No internal envelope fields leak into the answer set.
        labels = set(fields)
        assert "response_id" not in labels
        assert "referral_code" not in labels
        assert "webhook_secret" not in labels


@pytest.mark.asyncio
async def test_admin_sees_the_same_complete_submission_and_payment_proof(
    client: AsyncClient, db_session: AsyncSession
):
    affiliate = await _authenticate(client, 800020, "admin_verification")
    await _submit_form(client, affiliate["referral_code"], "submission-admin")
    admin_headers = await _admin_headers(db_session)

    listing = (await client.get("/api/v1/admin/referrals", headers=admin_headers)).json()
    assert len(listing) == 1
    referral_id = listing[0]["id"]

    detail = (
        await client.get(f"/api/v1/admin/referrals/{referral_id}", headers=admin_headers)
    ).json()
    fields = _by_label(detail["form_fields"])
    assert fields["Full Name"]["value"] == "Person One"
    assert fields["Email Address"]["value"] == "person1@example.com"
    assert fields["Phone Number"]["value"] == "08010000001"
    assert fields["Program"]["value"] == "Forex Trading"
    assert fields["Class Preference"]["value"] == "Online"
    proof = fields["Payment Screenshot"]
    assert proof["value"] == PAYMENT_PROOF_URL
    assert proof["category"] == "payment"
    assert proof["is_link"] is True
    assert fields["Payment Reference"]["value"] == "TRX-123"
    assert detail["payment_proof_url"] == PAYMENT_PROOF_URL
    assert detail["referrer"]["username"] == "admin_verification"
    assert detail["status"] == "verified"


@pytest.mark.asyncio
async def test_referrals_remain_scoped_to_the_owning_affiliate(
    client: AsyncClient, db_session: AsyncSession
):
    owner = await _authenticate(client, 800030, "owner_affiliate")
    other = await _authenticate(client, 800031, "other_affiliate")
    await _submit_form(client, owner["referral_code"], "submission-owner")

    owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    listing = (await client.get("/api/v1/referrals", headers=owner_headers)).json()
    referral_id = listing["referrals"][0]["id"]

    assert (
        await client.get(f"/api/v1/referrals/{referral_id}", headers=other_headers)
    ).status_code == 404
    assert (await client.get("/api/v1/referrals")).status_code == 401
    assert (
        await client.get(f"/api/v1/admin/referrals/{referral_id}", headers=other_headers)
    ).status_code == 403


@pytest.mark.asyncio
async def test_legacy_submission_without_answers_still_exposes_identity(
    client: AsyncClient,
):
    affiliate = await _authenticate(client, 800040, "legacy_affiliate")
    await _submit_form(client, affiliate["referral_code"], "submission-legacy", answers=[])

    headers = {"Authorization": f"Bearer {affiliate['access_token']}"}
    listing = (await client.get("/api/v1/referrals", headers=headers)).json()
    detail = (
        await client.get(f"/api/v1/referrals/{listing['referrals'][0]['id']}", headers=headers)
    ).json()

    fields = _by_label(detail["form_fields"])
    assert fields["Email"]["value"] == "person1@example.com"
    assert fields["Telegram Username"]["value"] == "@personone"


@pytest.mark.asyncio
async def test_admin_referral_detail_requires_admin(client: AsyncClient):
    affiliate = await _authenticate(client, 800050, "not_admin")
    await _submit_form(client, affiliate["referral_code"], "submission-denied")
    headers = {"Authorization": f"Bearer {affiliate['access_token']}"}
    listing = (await client.get("/api/v1/referrals", headers=headers)).json()
    referral_id = listing["referrals"][0]["id"]

    assert (await client.get("/api/v1/admin/referrals", headers=headers)).status_code == 403
    assert (
        await client.get(f"/api/v1/admin/referrals/{referral_id}", headers=headers)
    ).status_code == 403


@pytest.mark.asyncio
async def test_admin_referral_detail_returns_404_for_unknown_referral(
    client: AsyncClient, db_session: AsyncSession
):
    admin_headers = await _admin_headers(db_session)
    response = await client.get("/api/v1/admin/referrals/999999", headers=admin_headers)
    assert response.status_code == 404
