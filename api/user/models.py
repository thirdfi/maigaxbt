from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import SET_NULL
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class User(AbstractUser):

   def save(self, *args, **kwargs):
        UserProfile.objects.get_or_create(user=self)

        super().save(*args, **kwargs)

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False, null=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False, null=True)
    created_by = models.ForeignKey(User, SET_NULL, null=True, blank=True,
                                   related_name="created_%(model_name)ss")
    updated_by = models.ForeignKey(User, SET_NULL, null=True, blank=True,
                                   related_name="updated_%(model_name)ss")

    class Meta:
        abstract = True
        ordering = ("id",)



class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    xp_points = models.IntegerField(default=0)

    def add_xp(self, amount):
        """Increase XP and update the leaderboard."""
        self.xp_points += amount
        self.save()

    def remove_xp(self, amount):
        """Decrease XP (if needed)."""
        self.xp_points = max(0, self.xp_points - amount)
        self.save()

    def __str__(self):
        return f"{self.user.username} - XP: {self.xp_points}"


class Bet(BaseModel):
    STATUS_CHOICES = [('inactive', 'Inactive'),('pending', 'Pending'), ('won', 'Won'), ('lost', 'Lost')]

    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    token = models.CharField(max_length=50)
    prediction = models.CharField(max_length=10, choices=[('agree', 'Agree'), ('disagree', 'Disagree')])
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    verification_time = models.IntegerField(help_text="Time in hours for bet verification", default=1)
    entry_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)  # Store price at bet time
    result = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    msg_id = models.IntegerField(null=True, blank=True)
    symbol = models.CharField(max_length=100, null=True, blank=True)
    chat_type = models.CharField(max_length=20, choices=[('private', 'Private'), ('group', 'Group'), ('supergroup', 'Supergroup')])
    chat_id = models.BigIntegerField(null=True, blank=True) 

    def check_bet_result(self, current_price):
        """Check if the bet was correct based on price movement, notify if won"""
        from tasks.app import send_telegram_message

        if not self.entry_price:
            return  # Can't check without entry price

        price_change = Decimal(current_price) - self.entry_price
        is_correct_prediction = (price_change > 0 and self.prediction == 'agree') or \
                                (price_change < 0 and self.prediction == 'disagree')

        receiver_id = self.chat_id if self.chat_type in ["group", "supergroup"] else self.user.user.id

        if is_correct_prediction:
            self.result = 'won'
            self.user.add_xp(10)
            xp_reward = 10
            message = (f"🎉 @{self.user.user.username} won the bet on {self.symbol}! +10 XP added! 🎯"
                       if self.chat_type in ["group", "supergroup"]
                       else f"🎉 You won the bet on {self.symbol}! +10 XP added! 🎯")
        else:
            self.result = 'lost'
            self.user.add_xp(1)
            xp_reward = 1
            message = (f"☠️ @{self.user.user.username} lost the bet on {self.symbol}. +1 XP for the effort! 💪 Better luck next time! 😢"
                       if self.chat_type in ["group", "supergroup"]
                       else f"☠️ You lost the bet on {self.symbol}. +1 XP for the effort! 💪 Better luck next time! 😢")
            
        send_telegram_message.delay(receiver_id, message, self.msg_id)
        self.save()
        
        return xp_reward, self.user, self.msg_id, receiver_id, self.chat_type 

class Leaderboard(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    rank = models.IntegerField(default=0)

    def update_rank(self):
        """Update ranking logic based on XP points."""
        top_users = UserProfile.objects.order_by('-xp_points')
        for idx, user in enumerate(top_users):
            Leaderboard.objects.update_or_create(user=user, defaults={'rank': idx + 1})

    def __str__(self):
        return f"Rank {self.rank}: {self.user.user.username} - {self.user.xp_points} XP"


class Wallet(BaseModel):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    wallet_address = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.user.user.username} - Wallet: {self.wallet_address}"

class Transaction(BaseModel):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)  
    tx_hash = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    token = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='pending') 
    chain_id = models.IntegerField(default=0)
    retry_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.user.username} - TX: {self.tx_hash}"
