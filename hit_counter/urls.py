from django.urls import path

from . import views


app_name = 'hit_counter'

urlpatterns = [
    path('', views.log_hit, name='log-hit'),
    path('<slug:code>/', views.hit_count, name='hit-count'),
]
