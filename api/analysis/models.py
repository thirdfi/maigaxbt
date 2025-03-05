from __future__ import annotations

from django.db import models
from api.user.models import User, BaseModel


class Prompt (BaseModel):
    timeframe = models.CharField(max_length=4)
    text = models.TextField()

    def __str__(self):
        return self.text[:10]



class GenData(BaseModel):
    title = models.CharField(max_length=255)
    text = models.TextField()
    tradingview_img_url = models.ImageField(upload_to="images/")
    user = models.ForeignKey(User, related_name="gendatas", on_delete=models.CASCADE)

    def __str__(self):
        return self.title
