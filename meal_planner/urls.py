from django.urls import path
from . import views

urlpatterns = [    
    path('', views.calendar_view, name='calendar'),
    path('meal/add/', views.meal_add, name='meal_add'),
    path('meal/<int:pk>/edit/', views.meal_edit, name='meal_edit'),
    path('meal/<int:pk>/delete/', views.meal_delete, name='meal_delete'),
    path('tags/', views.tags_view, name='tags'),
    path('main-dishes/', views.main_dishes_view, name='main_dishes'),
    path('side-dishes/', views.side_dishes_view, name='side_dishes'),
]