from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms


class CrearUserForms(UserCreationForm):
	class Meta:
		model = User
		fields = ['username', 'first_name', 'password1', 'password2']

