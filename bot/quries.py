from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from asgiref.sync import sync_to_async

from api.analysis.models import GenData, Prompt
from api.user.models import User, UserProfile, Bet, Wallet, Transaction
from api.wallet.mpc_service import create_wallet

@sync_to_async
def create_new_bot():
    user = User.safe_create()
    return user

@sync_to_async
def get_filter_bot():
    user = User.objects.filter(username__startswith="M@!_", username__endswith="_G@")
    return user

@sync_to_async
def get_all_user():
    return UserProfile.objects.all()

@sync_to_async
def add_xp_async(profile: UserProfile, amount: int):
    profile.add_xp(amount)

@sync_to_async
def is_user_over_limit(user_id, hours=1, minutes=0, seconds=0):
    time_limit = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    time_threshold = timezone.now() - time_limit

    recent_uses = GenData.objects.filter(user_id=user_id, created_at__gte=time_threshold).count()

    if recent_uses >= 20:
        first_recent = GenData.objects.filter(user_id=user_id, created_at__gte=time_threshold).order_by("created_at").first()
        if first_recent:
            next_available_time = first_recent.created_at + time_limit
            return True, next_available_time.astimezone(timezone.get_current_timezone())
        else:
            return True, timezone.now() + time_limit
    
    return False, None

@sync_to_async
def add_gen_data_to_db(text, user_id):
    GenData.objects.create(
        text=text,
        user_id=user_id,
    )

@sync_to_async
def add_bets_to_db(user_id, token, entry_price, symbol):
    user_profile = UserProfile.objects.get(user__id=user_id)

    new_bet = Bet.objects.create(user=user_profile,
                       token=token,
                       amount=10,
                       verification_time=1,
                       entry_price=entry_price,
                       symbol=symbol)

    return new_bet.id

@sync_to_async
def update_bet(bet_id, **kwargs):
    try:
        bet = Bet.objects.get(id=bet_id)
        for key, value in kwargs.items():
            setattr(bet, key, value)
        bet.save()
        return bet.id
    except Bet.DoesNotExist:
        # handle the case where the bet with the given ID does not exist
        return None

@sync_to_async
def get_prompt():
    return  Prompt.objects.first()

@sync_to_async
def get_my_stats(user_id):
    return UserProfile.objects.get(user__id=user_id)

@sync_to_async
def get_or_create_wallet(user_id: int) -> Wallet:
    profile = UserProfile.objects.get(user__id=user_id)

    wallet, created = Wallet.objects.get_or_create(
        user=profile,
        defaults={
            "wallet_address": create_wallet_sync()
        }
    )
    return wallet, created

def create_wallet_sync() -> str:
    import asyncio
    return asyncio.run(create_wallet())

@sync_to_async
def get_wallet_if_exist(user_id):
    try:
        profile = UserProfile.objects.get(user__id=user_id)
        return Wallet.objects.get(user=profile)
    except (UserProfile.DoesNotExist, Wallet.DoesNotExist):
        return None


@sync_to_async
def record_transaction(
    wallet, tx_hash: str, user, amount: float, token: str, chain_id: int, status: str, retry_count: int = 0
):
    Transaction.objects.create(
        wallet=wallet,
        tx_hash=tx_hash,
        user=user,
        amount=Decimal(amount),
        token=token,
        chain_id=chain_id,
        retry_count=retry_count,
        status=status,
    )