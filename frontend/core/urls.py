# US-14: Django Website - Basic URLs
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),


    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path('observations/', views.observations, name='observations'),

    path('dashboard/update-token/', views.update_token_view, name='update_token'),
    path('satellites/', views.satellites, name='satellites'),
    path('subscribe/<int:product_id>/', views.subscribe, name='subscribe'),
]
