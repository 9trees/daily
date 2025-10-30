from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.blogin, name='login'),
    path('signup', views.signup, name='signup'),
    path('signout', views.signout, name='signout'),
    path('faq', views.faqdb, name='faq'),
]