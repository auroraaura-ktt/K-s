from django import forms
from django.contrib.auth.forms import AuthenticationForm

from mytask.models import (
    Profile,
    Project,
    Skill,
    Experience,
    Education,
)


class AdminLoginForm(AuthenticationForm):
    """Custom login form for the admin panel."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
        })
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'name', 'title', 'bio', 'photo', 'email', 'phone',
            'location', 'github', 'linkedin', 'twitter', 'website',
            'resume', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your name'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your title'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+1 234 567 890'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'City, Country'}),
            'github': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/...'}),
            'linkedin': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://linkedin.com/in/...'}),
            'twitter': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://twitter.com/...'}),
            'website': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'resume': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://.../resume.pdf'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'title', 'description', 'photo', 'url', 'github_url',
            'is_featured',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Project title'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'github_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/...'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'proficiency', 'icon', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Skill name'}),
            'proficiency': forms.NumberInput(attrs={
                'class': 'form-input', 'min': 0, 'max': 100,
                'placeholder': '0-100',
            }),
            'icon': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '🚀 or fa-code'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = [
            'title', 'company', 'location', 'description',
            'start_date', 'end_date', 'is_current',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Job title'}),
            'company': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Company name'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'City, State'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = [
            'institution', 'degree', 'field_of_study',
            'start_date', 'end_date', 'description',
        ]
        widgets = {
            'institution': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'University/School name'}),
            'degree': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Degree e.g. BSc'}),
            'field_of_study': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Field of study'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }