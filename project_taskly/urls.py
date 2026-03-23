from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('check-username/', views.check_username, name='check_username'),
    
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    path('register/', views.register, name='register'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout, name='logout'),
    path("projects/", views.projects, name="projects"),
    path("projects/create/", views.create_project, name="create_project"),
    path("projects/view/<int:id>/", views.view_project, name="view_project"),
    path("projects/edit/<int:id>/", views.edit_project, name="edit_project"),
    path("projects/delete/<int:id>/", views.delete_project, name="delete_project"),
    path("settings/", views.settings, name="settings"),
]