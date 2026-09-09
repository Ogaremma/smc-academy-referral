import asyncio
from datetime import datetime, timezone
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.config import settings
from app.db.models import Broadcast, BroadcastDelivery, User, ReferralCode, AuditLog

async def deliver_broadcast(broadcast_id: int, factory: async_sessionmaker):
    async with factory() as db:
        b = await db.get(Broadcast, broadcast_id); b.status='SENDING'; b.started_at=datetime.now(timezone.utc)
        users=(await db.execute(select(User).join(ReferralCode).where(User.is_active.is_(True),User.account_status=='ACTIVE',ReferralCode.is_active.is_(True)))).scalars().all()
        b.target_count=len(users); await db.commit(); success=failed=0; errors=[]
        async with httpx.AsyncClient(timeout=15) as client:
            for user in users:
                status='SENT'; err=None
                try:
                    response=await client.post(f'https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage',json={'chat_id':user.telegram_id,'text':b.message})
                    if response.status_code==429:
                        retry=response.json().get('parameters',{}).get('retry_after',1); await asyncio.sleep(min(int(retry),30)); response=await client.post(f'https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage',json={'chat_id':user.telegram_id,'text':b.message})
                    if response.status_code >= 400 or not response.json().get('ok'): status='FAILED'; err=f'Telegram error {response.status_code}'
                except Exception as exc: status='FAILED'; err=type(exc).__name__
                db.add(BroadcastDelivery(broadcast_id=b.id,user_id=user.id,status=status,error_message=err)); success += status=='SENT'; failed += status=='FAILED'; errors.append(err) if err else None
        b.success_count=success; b.failed_count=failed; b.status='COMPLETED' if failed==0 else ('PARTIAL' if success else 'FAILED'); b.error_summary='; '.join(errors[:5]) if errors else None; b.completed_at=datetime.now(timezone.utc)
        db.add(AuditLog(actor_user_id=b.actor_user_id,action='broadcast_sent',metadata_json=f'{{"broadcast_id": {b.id}, "target_count": {b.target_count}, "success_count": {success}, "failed_count": {failed}, "status": "{b.status}"}}'))
        await db.commit()
