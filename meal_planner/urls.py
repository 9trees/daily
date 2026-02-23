from django.urls import path
from . import views

urlpatterns = [    
    path('', views.calendar_view, name='calendar'),
    path('tags/', views.tags_view, name='tags'),
    path('main-dishes/', views.main_dishes_view, name='main_dishes'),
    path('side-dishes/', views.side_dishes_view, name='side_dishes'),
]