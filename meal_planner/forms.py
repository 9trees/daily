from django import forms

from .models import MainDish, Meal, SideDish, Tag


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


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ["date", "type", "main_dish", "side_dishes", "tags"]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "type": forms.Select(attrs={"class": "form-select"}),
            "main_dish": forms.Select(attrs={"class": "form-select"}),
            "side_dishes": forms.SelectMultiple(attrs={"class": "form-select"}),
            "tags": forms.SelectMultiple(attrs={"class": "form-select"}),
        }
