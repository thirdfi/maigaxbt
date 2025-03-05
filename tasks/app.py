from __future__ import annotations

import asyncio
from datetime import timedelta

from aiogram import Bot
from asgiref.sync import async_to_sync
from celery import Celery, shared_task
from celery.schedules import crontab

from api.config.celery import tg_bot_token
from django.utils.timezone import now

from api.config import celery as config
from api.helpers.helper import get_crypto_prices
from api.user.models import Bet

app = Celery("main")
app.config_from_object(config)
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'verify-bets-every-1-hour': {
        'task': 'tasks.app.verify_bets',
        'schedule': crontab(minute='*/57'),  # Run every 1 hour
    },
}




@shared_task
def verify_bets():
    """Verify bets whose verification time has passed."""
    bets = Bet.objects.filter(result='pending')

    coins_ids = bets.values_list('token', flat=True)
    coins_dict = get_crypto_prices(coins_ids)

    for bet in bets:
        verification_time = bet.created_at + timedelta(hours=bet.verification_time)

        if now() >= verification_time:
            bet.check_bet_result(coins_dict[bet.token])


    return f"Verified {bets.count()} bets"



async def _send(user_id, message, msg_id):
    bot = Bot(token=tg_bot_token)

    await asyncio.sleep(0.5)  # Delay to prevent rate limiting
    await bot.send_message(user_id, message, request_timeout=10, reply_to_message_id=msg_id)
    await bot.session.close()  # Ensure the session is closed


@shared_task(bind=True)
def send_telegram_message(self, user_id, message, msg_id):
    try:
        async_to_sync(_send)(user_id, message, msg_id)  # Wrap the async call in async_to_sync

    except Exception as e:
        self.retry(exc=e, countdown=5, max_retries=3)
