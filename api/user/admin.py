from __future__ import annotations

from typing import Any

from django.contrib import admin

from api.user.models import User, UserProfile, Bet


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    filter_horizontal = ("groups", "user_permissions")

    list_display = (
        "id",
        "username",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    def save_model(
        self,
        request: Any,
        obj: User,
        form: None,
        change: bool,  # noqa: FBT001
    ) -> None:
        """Update user password if it is not raw.

        This is needed to hash password when updating user from admin panel.
        """
        has_raw_password = obj.password.startswith("pbkdf2_sha256")
        if not has_raw_password:
            obj.set_password(obj.password)

        super().save_model(request, obj, form, change)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "xp_points",
    )


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "token",
        "prediction",
        "amount",
        "verification_time",
        "entry_price",
        "result",
        "msg_id",
        "symbol",
    )