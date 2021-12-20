from django.db import models

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
