from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('login/', views.login, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("projects/", views.projects, name="projects"),
    path("projects/create/", views.create_project, name="create_project"),
    path("projects/view/<int:id>/", views.view_project, name="view_project"),
    path("projects/edit/<int:id>/", views.edit_project, name="edit_project"),
    path("projects/delete/<int:id>/", views.delete_project, name="delete_project"),
    path("settings/", views.settings, name="settings"),
]