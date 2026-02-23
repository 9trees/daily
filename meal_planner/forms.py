from django import forms

from .models import MainDish, SideDish, Tag


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }


class MainDishForm(forms.ModelForm):
    class Meta:
        model = MainDish
        fields = ["name", "description", "ingredients", "tags"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "ingredients": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "tags": forms.SelectMultiple(attrs={"class": "form-select"}),
        }


class SideDishForm(forms.ModelForm):
    class Meta:
        model = SideDish
        fields = ["name", "description", "ingredients", "tags"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "ingredients": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "tags": forms.SelectMultiple(attrs={"class": "form-select"}),
        }
