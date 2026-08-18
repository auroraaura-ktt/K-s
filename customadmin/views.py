from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from mytask.models import (
    Profile,
    Project,
    Skill,
    Experience,
    Education,
    ContactMessage,
)
from .forms import (
    AdminLoginForm,
    ProfileForm,
    ProjectForm,
    SkillForm,
    ExperienceForm,
    EducationForm,
)


# Authentication

def admin_login(request):
    """Custom admin login view."""
    if request.user.is_authenticated:
        return redirect('customadmin:dashboard')

    form = AdminLoginForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Welcome back!')
            return redirect('customadmin:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'customadmin/login.html', {'form': form})


@login_required
def admin_logout(request):
    """Custom admin logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('customadmin:login')


# Dashboard

@login_required
def dashboard(request):
    """Admin dashboard with overview statistics."""
    stats = {
        'projects': Project.objects.count(),
        'skills': Skill.objects.count(),
        'experiences': Experience.objects.count(),
        'educations': Education.objects.count(),
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
        'total_messages': ContactMessage.objects.count(),
    }
    return render(request, 'customadmin/dashboard.html', {'stats': stats})


# Profile CRUD

@login_required
def profile_list(request):
    profiles = Profile.objects.all()
    return render(request, 'customadmin/profile_list.html', {'profiles': profiles})


@login_required
def profile_add(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile added successfully.')
            return redirect('customadmin:profile_list')
    else:
        form = ProfileForm()
    return render(request, 'customadmin/profile_form.html', {'form': form, 'action': 'Add'})


@login_required
def profile_edit(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('customadmin:profile_list')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'customadmin/profile_form.html', {'form': form, 'action': 'Edit'})


@login_required
def profile_delete(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    if request.method == 'POST':
        profile.delete()
        messages.success(request, 'Profile deleted successfully.')
        return redirect('customadmin:profile_list')
    return render(request, 'customadmin/confirm_delete.html', {
        'object': profile, 'model_name': 'Profile',
    })


# Project CRUD

@login_required
def project_list(request):
    projects = Project.objects.all().order_by('-date_created')
    return render(request, 'customadmin/project_list.html', {'projects': projects})


@login_required
def project_add(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project added successfully.')
            return redirect('customadmin:project_list')
    else:
        form = ProjectForm()
    return render(request, 'customadmin/project_form.html', {'form': form, 'action': 'Add'})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully.')
            return redirect('customadmin:project_list')
    else:
        form = ProjectForm(instance=project)
    return render(request, 'customadmin/project_form.html', {'form': form, 'action': 'Edit'})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted successfully.')
        return redirect('customadmin:project_list')
    return render(request, 'customadmin/confirm_delete.html', {
        'object': project, 'model_name': 'Project',
    })


# Skill CRUD

@login_required
def skill_list(request):
    skills = Skill.objects.all()
    return render(request, 'customadmin/skill_list.html', {'skills': skills})


@login_required
def skill_add(request):
    if request.method == 'POST':
        form = SkillForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Skill added successfully.')
            return redirect('customadmin:skill_list')
    else:
        form = SkillForm()
    return render(request, 'customadmin/skill_form.html', {'form': form, 'action': 'Add'})


@login_required
def skill_edit(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    if request.method == 'POST':
        form = SkillForm(request.POST, instance=skill)
        if form.is_valid():
            form.save()
            messages.success(request, 'Skill updated successfully.')
            return redirect('customadmin:skill_list')
    else:
        form = SkillForm(instance=skill)
    return render(request, 'customadmin/skill_form.html', {'form': form, 'action': 'Edit'})


@login_required
def skill_delete(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    if request.method == 'POST':
        skill.delete()
        messages.success(request, 'Skill deleted successfully.')
        return redirect('customadmin:skill_list')
    return render(request, 'customadmin/confirm_delete.html', {
        'object': skill, 'model_name': 'Skill',
    })


# Experience CRUD

@login_required
def experience_list(request):
    experiences = Experience.objects.all().order_by('-start_date')
    return render(request, 'customadmin/experience_list.html', {'experiences': experiences})


@login_required
def experience_add(request):
    if request.method == 'POST':
        form = ExperienceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Experience added successfully.')
            return redirect('customadmin:experience_list')
    else:
        form = ExperienceForm()
    return render(request, 'customadmin/experience_form.html', {'form': form, 'action': 'Add'})


@login_required
def experience_edit(request, pk):
    experience = get_object_or_404(Experience, pk=pk)
    if request.method == 'POST':
        form = ExperienceForm(request.POST, instance=experience)
        if form.is_valid():
            form.save()
            messages.success(request, 'Experience updated successfully.')
            return redirect('customadmin:experience_list')
    else:
        form = ExperienceForm(instance=experience)
    return render(request, 'customadmin/experience_form.html', {'form': form, 'action': 'Edit'})


@login_required
def experience_delete(request, pk):
    experience = get_object_or_404(Experience, pk=pk)
    if request.method == 'POST':
        experience.delete()
        messages.success(request, 'Experience deleted successfully.')
        return redirect('customadmin:experience_list')
    return render(request, 'customadmin/confirm_delete.html', {
        'object': experience, 'model_name': 'Experience',
    })


# Education CRUD

@login_required
def education_list(request):
    educations = Education.objects.all().order_by('-start_date')
    return render(request, 'customadmin/education_list.html', {'educations': educations})


@login_required
def education_add(request):
    if request.method == 'POST':
        form = EducationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Education added successfully.')
            return redirect('customadmin:education_list')
    else:
        form = EducationForm()
    return render(request, 'customadmin/education_form.html', {'form': form, 'action': 'Add'})


@login_required
def education_edit(request, pk):
    education = get_object_or_404(Education, pk=pk)
    if request.method == 'POST':
        form = EducationForm(request.POST, instance=education)
        if form.is_valid():
            form.save()
            messages.success(request, 'Education updated successfully.')
            return redirect('customadmin:education_list')
    else:
        form = EducationForm(instance=education)
    return render(request, 'customadmin/education_form.html', {'form': form, 'action': 'Edit'})


@login_required
def education_delete(request, pk):
    education = get_object_or_404(Education, pk=pk)
    if request.method == 'POST':
        education.delete()
        messages.success(request, 'Education deleted successfully.')
        return redirect('customadmin:education_list')
    return render(request, 'customadmin/confirm_delete.html', {
        'object': education, 'model_name': 'Education',
    })


# Contact Messages

@login_required
def message_list(request):
    messages_list = ContactMessage.objects.all().order_by('-date_sent')
    return render(request, 'customadmin/message_list.html', {'messages_list': messages_list})


@login_required
def message_detail(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    if not message.is_read:
        message.is_read = True
        message.save()
    return render(request, 'customadmin/message_detail.html', {'message': message})


@login_required
def message_delete(request, pk):
    message = get_object_or_404(ContactMessage, pk=pk)
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Message deleted successfully.')
        return redirect('customadmin:message_list')
    return render(request, 'customadmin/confirm_delete.html', {
        'object': message, 'model_name': 'Contact Message',
    })
