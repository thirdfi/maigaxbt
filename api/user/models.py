from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import SET_NULL



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

    def check_bet_result(self, current_price):
        """Check if the bet was correct based on price movement, notify if won"""
        from tasks.app import send_telegram_message

        username = self.user.user.username 
        user_id = self.user.user.id    
        is_group = self.msg_id is not None  

        if not self.entry_price:
            return  # Can't check without entry price
    
        price_change = self.entry_price - Decimal(current_price)
        if (price_change > 0 and self.prediction == 'agree') or (price_change < 0 and self.prediction == 'disagree'):
            self.result = 'won'
            self.user.add_xp(10)

            message = f"🎉 Congratulations! {username} won! +10 XP for {self.symbol} bet" if is_group else \
                      f"🎉 Congratulations! You won! +10 XP for {self.symbol} bet"


            send_telegram_message.delay(user_id, message, self.msg_id)

        else:
            self.result = 'lost'

            message = f"☠️ @{username} lost! on {self.symbol} bet" if is_group else \
                      f"☠️ You lost! on {self.symbol} bet"

            send_telegram_message.delay(user_id, message, self.msg_id)

        self.save()


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
