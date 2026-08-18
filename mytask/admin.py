from django.contrib import admin
from .models import (
    Profile,
    Project,
    Skill,
    Experience,
    Education,
    ContactMessage,
    Album,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'title', 'email')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_featured', 'date_created')
    list_filter = ('is_featured', 'date_created')
    search_fields = ('title', 'description')
    date_hierarchy = 'date_created'
    ordering = ('-date_created',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'proficiency', 'is_featured')
    list_filter = ('is_featured',)
    search_fields = ('name',)


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'start_date', 'is_current')
    list_filter = ('is_current', 'start_date')
    search_fields = ('title', 'company')
    ordering = ('-start_date',)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('degree', 'institution', 'start_date')
    search_fields = ('degree', 'institution')
    ordering = ('-start_date',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'date_sent', 'is_read')
    list_filter = ('is_read', 'date_sent')
    search_fields = ('name', 'email', 'subject')
    date_hierarchy = 'date_sent'
    ordering = ('-date_sent',)


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('album_name', 'date_created')
    search_fields = ('album_name', 'album_description')
    ordering = ('-date_created',)
