import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.db.base import Base
from app.db.models import User, ReferralCode, Broadcast, BroadcastDelivery, AuditLog
from app.services.broadcast_service import deliver_broadcast

class Resp:
    def __init__(self, code=200, body=None): self.status_code=code; self.body=body or {'ok': True}
    def json(self): return self.body
class Client:
    responses=[]
    def __init__(self,*a,**k): pass
    async def __aenter__(self): return self
    async def __aexit__(self,*a): pass
    async def post(self,*a,**k):
        value=self.responses.pop(0)
        if isinstance(value, Exception): raise value
        return value

async def make_db(tmp_path):
    engine=create_async_engine(f"sqlite+aiosqlite:///{(tmp_path/'broadcast.db').as_posix()}")
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)

@pytest.mark.asyncio
async def test_delivery_partial_failure_and_eligibility(tmp_path, monkeypatch):
    engine, factory=await make_db(tmp_path)
    async with factory() as db:
        actor=User(telegram_id=999,is_admin=True); db.add(actor)
        for i in range(3):
            u=User(telegram_id=700+i); db.add(u); await db.flush(); db.add(ReferralCode(user_id=u.id,code=f'C{i}',is_active=True))
        db.add(User(telegram_id=800,account_status='REVOKED'))
        db.add(User(telegram_id=-900,is_active=False,account_status='DELETED'))
        db.add(User(telegram_id=801))
        await db.commit(); b=Broadcast(actor_user_id=actor.id,message='hello'); db.add(b); await db.commit(); await db.refresh(b)
        Client.responses=[Resp(),Resp(400,{'ok':False}),RuntimeError('network')]; monkeypatch.setattr('app.services.broadcast_service.httpx.AsyncClient',Client)
        await deliver_broadcast(b.id,factory)
        await db.refresh(b); row=b; assert (row.target_count,row.success_count,row.failed_count,row.status)==(3,1,2,'PARTIAL')
        assert len((await db.execute(select(BroadcastDelivery))).scalars().all())==3
        audit=(await db.execute(select(AuditLog).where(AuditLog.action=='broadcast_sent'))).scalar_one(); assert 'network' not in (audit.metadata_json or '')
    await engine.dispose()

@pytest.mark.asyncio
async def test_delivery_429_retry(tmp_path, monkeypatch):
    engine,factory=await make_db(tmp_path)
    async with factory() as db:
        actor=User(telegram_id=1000,is_admin=True); u=User(telegram_id=1001); db.add_all([actor,u]); await db.flush(); db.add(ReferralCode(user_id=u.id,code='R',is_active=True)); b=Broadcast(actor_user_id=actor.id,message='x'); db.add(b); await db.commit(); await db.refresh(b)
        Client.responses=[Resp(429,{'ok':False,'parameters':{'retry_after':0}}),Resp()]; monkeypatch.setattr('app.services.broadcast_service.httpx.AsyncClient',Client); await deliver_broadcast(b.id,factory); await db.refresh(b); assert b.success_count==1 and b.failed_count==0
    await engine.dispose()

@pytest.mark.asyncio
async def test_delivery_429_retry_failure_is_recorded(tmp_path, monkeypatch):
    engine,factory=await make_db(tmp_path)
    async with factory() as db:
        actor=User(telegram_id=1100,is_admin=True); u=User(telegram_id=1101); db.add_all([actor,u]); await db.flush(); db.add(ReferralCode(user_id=u.id,code='RF',is_active=True)); b=Broadcast(actor_user_id=actor.id,message='x'); db.add(b); await db.commit(); await db.refresh(b)
        Client.responses=[Resp(429,{'ok':False,'parameters':{'retry_after':0}}),Resp(400,{'ok':False,'description':'secret response'})]
        monkeypatch.setattr('app.services.broadcast_service.httpx.AsyncClient',Client)
        await deliver_broadcast(b.id,factory); await db.refresh(b)
        assert b.success_count==0 and b.failed_count==1 and b.status=='FAILED'
        delivery=(await db.execute(select(BroadcastDelivery))).scalar_one(); assert delivery.status=='FAILED'; assert 'secret response' not in (delivery.error_message or '')
    await engine.dispose()
