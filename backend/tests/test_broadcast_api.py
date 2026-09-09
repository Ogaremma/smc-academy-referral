import pytest
from sqlalchemy import select
from app.core.security import create_access_token
from app.db.models import User

@pytest.mark.asyncio
async def test_broadcast_endpoints_require_admin(client, db_session):
    user=User(telegram_id=1200,is_admin=False); db_session.add(user); await db_session.commit()
    token=create_access_token({'sub':str(user.id),'telegram_id':user.telegram_id})
    headers={'Authorization':f'Bearer {token}'}
    assert (await client.get('/api/v1/admin/broadcasts',headers=headers)).status_code==403
    assert (await client.post('/api/v1/admin/broadcasts',headers=headers,json={'message':'hello'})).status_code==403

@pytest.mark.asyncio
async def test_admin_broadcast_endpoint_owns_input_and_validates_message(client, db_session, monkeypatch):
    admin=User(telegram_id=1201,is_admin=True); db_session.add(admin); await db_session.commit()
    token=create_access_token({'sub':str(admin.id),'telegram_id':admin.telegram_id}); headers={'Authorization':f'Bearer {token}'}
    monkeypatch.setattr('app.api.admin.deliver_broadcast', lambda *args: None)
    response=await client.post('/api/v1/admin/broadcasts',headers=headers,json={'message':'hello','recipient_ids':[999], 'target_count':999})
    assert response.status_code==202
    assert (await client.get('/api/v1/admin/broadcasts',headers=headers)).status_code==200
    assert (await client.post('/api/v1/admin/broadcasts',headers=headers,json={'message':'   '})).status_code==422
