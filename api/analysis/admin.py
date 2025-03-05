from __future__ import annotations

from django.contrib import admin
from api.analysis.models import  GenData, Prompt



@admin.register(GenData)
class GenDataAdmin(admin.ModelAdmin):

    list_display = ("id", "title")
    fields = ["id", "title", "tradingview_img_url", "text", "user"]
    readonly_fields = ["id"]

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):

    list_display = ("id", "timeframe")
    fields = ["id", "timeframe", "text"]
    readonly_fields = ["id"]
