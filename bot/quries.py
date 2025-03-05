from asgiref.sync import sync_to_async

from api.analysis.models import GenData, Prompt
from api.user.models import UserProfile, Bet


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