import pytest
from sqlalchemy import select
from app.db.models import Referral, ReferralCode, User
from tests.conftest import create_telegram_init_data

@pytest.mark.asyncio
async def test_referrals_are_scoped_to_authenticated_affiliate(client, db_session):
    a = await client.post('/api/v1/auth/telegram', json={'init_data': create_telegram_init_data(user_dict={'id': 30303})})
    b = await client.post('/api/v1/auth/telegram', json={'init_data': create_telegram_init_data(user_dict={'id': 40404})})
    ta, tb = a.json()['access_token'], b.json()['access_token']
    users = (await db_session.execute(select(User).where(User.telegram_id.in_([30303,40404])))).scalars().all()
    ua, ub = sorted(users, key=lambda u: u.telegram_id)
    ca = (await db_session.execute(select(ReferralCode.id).where(ReferralCode.user_id == ua.id))).scalar_one(); cb = (await db_session.execute(select(ReferralCode.id).where(ReferralCode.user_id == ub.id))).scalar_one()
    db_session.add_all([Referral(referral_code_id=ca, referrer_id=ua.id, google_form_response_id='a-1', status='verified'), Referral(referral_code_id=cb, referrer_id=ub.id, google_form_response_id='b-1', status='verified')]); await db_session.commit()
    rows = (await client.get('/api/v1/referrals', headers={'Authorization': f'Bearer {ta}'})).json()['referrals']
    assert len(rows) == 1
    b_ref = (await db_session.execute(select(Referral).where(Referral.google_form_response_id == 'b-1'))).scalar_one()
    assert (await client.get(f'/api/v1/referrals/{b_ref.id}', headers={'Authorization': f'Bearer {ta}'})).status_code == 404
    assert (await client.get('/api/v1/referrals')).status_code == 401
