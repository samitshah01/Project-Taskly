from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('set-timezone/', views.set_timezone, name='set_timezone'),
    path('login/', views.login, name='login'),
    path('check-username/', views.check_username, name='check_username'),
    
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    path('register/', views.register, name='register'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout, name='logout'),
]