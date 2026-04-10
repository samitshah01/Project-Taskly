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
    path('dashboard/tasks/create/', views.create_task, name='create_task'),
    path('dashboard/tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('dashboard/tasks/<int:task_id>/update/', views.update_task, name='update_task'),
    path('dashboard/tasks/<int:task_id>/status/', views.update_task_status, name='update_task_status'),
    path('dashboard/tasks/<int:task_id>/comments/add/', views.add_task_comment, name='add_task_comment'),
    path('dashboard/tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('dashboard/projects/create/', views.create_project, name='create_project'),
    path('dashboard/projects/<int:project_id>/update/', views.update_project, name='update_project'),
    path('dashboard/projects/<int:project_id>/team/', views.manage_project_team, name='manage_project_team'),
    path('dashboard/projects/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('dashboard/projects', views.projects, name='projects'),
    path('dashboard/projects/<int:project_id>/', views.project_board, name='project_board'),
    path('dashboard/profile', views.profile, name='profile'),
    path('logout/', views.logout, name='logout'),
]
