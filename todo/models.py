from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Mantras(models.Model):
    mantra = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.mantra

class Auth_names(models.Model):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name

class Quotes(models.Model):
    auth = models.ForeignKey(Auth_names, on_delete=models.CASCADE)
    quote = models.CharField(max_length=300)

    def __str__(self):
        return self.quote[:20]

class FaqDb(models.Model):
    question = models.TextField(default='', blank=True, null=True)
    short_description = models.TextField(default='', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.question[:100])
