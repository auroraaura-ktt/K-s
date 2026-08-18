from django.urls import path
from . import views

app_name = 'customadmin'

urlpatterns = [
    # Auth
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Profile
    path('profile/', views.profile_list, name='profile_list'),
    path('profile/add/', views.profile_add, name='profile_add'),
    path('profile/<int:pk>/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<int:pk>/delete/', views.profile_delete, name='profile_delete'),

    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/add/', views.project_add, name='project_add'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),

    # Skills
    path('skills/', views.skill_list, name='skill_list'),
    path('skills/add/', views.skill_add, name='skill_add'),
    path('skills/<int:pk>/edit/', views.skill_edit, name='skill_edit'),
    path('skills/<int:pk>/delete/', views.skill_delete, name='skill_delete'),

    # Experience
    path('experience/', views.experience_list, name='experience_list'),
    path('experience/add/', views.experience_add, name='experience_add'),
    path('experience/<int:pk>/edit/', views.experience_edit, name='experience_edit'),
    path('experience/<int:pk>/delete/', views.experience_delete, name='experience_delete'),

    # Education
    path('education/', views.education_list, name='education_list'),
    path('education/add/', views.education_add, name='education_add'),
    path('education/<int:pk>/edit/', views.education_edit, name='education_edit'),
    path('education/<int:pk>/delete/', views.education_delete, name='education_delete'),

    # Contact Messages
    path('messages/', views.message_list, name='message_list'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/<int:pk>/delete/', views.message_delete, name='message_delete'),
]
