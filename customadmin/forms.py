from django import forms
from django.contrib.auth.forms import AuthenticationForm

from mytask.models import (
    Profile,
    Project,
    Skill,
    Experience,
    Education,
    SocialLink,
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
    github = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'github.com/yourname'}),
        help_text="Full URL, domain, or just your username.",
    )
    linkedin = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'linkedin.com/in/yourname'}),
        help_text="Full URL, domain, or just your username.",
    )
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'yourwebsite.com'}),
    )

    class Meta:
        model = Profile
        fields = [
            'name', 'title', 'bio', 'photo', 'email', 'phone',
            'location', 'github', 'linkedin', 'website',
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
            'website': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'resume': forms.ClearableFileInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


    @staticmethod
    def _normalize_url(value):
        """Make link fields forgiving: accept usernames/domains and prefix https://."""
        value = (value or '').strip()
        if not value:
            return value
        if value.lower().startswith(('http://', 'https://', 'mailto:')):
            return value
        return f'https://{value}'

    def clean_github(self):
        value = self.cleaned_data.get('github', '').strip().lstrip('@')
        if value and '.' not in value:
            value = f'github.com/{value}'
        return self._normalize_url(value)

    def clean_linkedin(self):
        value = self.cleaned_data.get('linkedin', '').strip().lstrip('@')
        if value and '.' not in value:
            value = f'linkedin.com/in/{value}'
        return self._normalize_url(value)

    def clean_website(self):
        return self._normalize_url(self.cleaned_data.get('website', ''))


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
            'start_date', 'end_date', 'description', 'certificate',
        ]
        widgets = {
            'institution': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'University/School name'}),
            'degree': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Degree e.g. BSc'}),
            'field_of_study': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Field of study'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'certificate': forms.ClearableFileInput(attrs={'class': 'form-input'}),
        }


class SocialLinkForm(forms.ModelForm):
    class Meta:
        model = SocialLink
        fields = ['name', 'url', 'icon', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. GitHub, LinkedIn, Instagram, Email'}),
            'url': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/you  (or your@email.com)'}),
            'icon': forms.TextInput(attrs={'class': 'form-input', 'placeholder': "Optional: e.g. fa-brands fa-instagram"}),
            'order': forms.NumberInput(attrs={'class': 'form-input', 'min': 0, 'placeholder': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
