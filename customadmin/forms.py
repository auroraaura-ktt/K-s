from django import forms
from django.contrib.auth.forms import AuthenticationForm

from zipfile import BadZipFile, ZipFile

from mytask.models import (
    Application,
    Profile,
    Project,
    Skill,
    Experience,
    Education,
    SocialLink,
    Album,
)


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    """Validate every selected image with Django's content-based decoder."""

    widget = MultipleImageInput

    def __init__(self, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('widget', MultipleImageInput(attrs={
            'class': 'form-input',
            'accept': 'image/*,.heic,.heif',
        }))
        super().__init__(**kwargs)

    def clean(self, data, initial=None):
        if data in self.empty_values:
            return []
        uploads = data if isinstance(data, (list, tuple)) else [data]
        image_field = forms.ImageField()
        return [image_field.clean(upload) for upload in uploads if upload]


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
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-input', 'accept': 'image/*,.heic,.heif',
            }),
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
    images = MultipleImageField(label='Additional photos')

    class Meta:
        model = Project
        fields = [
            'title', 'description', 'photo', 'url', 'github_url',
            'is_featured',
            # Optional case-study details. All are blank-safe, so older
            # projects simply leave these sections out of the detail page.
            'role', 'client', 'status',
            'technologies', 'features', 'responsibilities', 'additional_info',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Project title'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-input', 'accept': 'image/*,.heic,.heif',
            }),
            'url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'github_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/...'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'role': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full Stack Developer'}),
            'client': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Personal'}),
            'status': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Completed'}),
            'technologies': forms.Textarea(attrs={'rows': 3, 'class': 'form-input', 'placeholder': 'React\nTypeScript\nNode.js'}),
            'features': forms.Textarea(attrs={'rows': 4, 'class': 'form-input', 'placeholder': 'One feature per line'}),
            'responsibilities': forms.Textarea(attrs={'rows': 3, 'class': 'form-input', 'placeholder': 'One responsibility per line'}),
            'additional_info': forms.Textarea(attrs={'rows': 3, 'class': 'form-input'}),
        }

class ApplicationForm(forms.ModelForm):
    """Form for uploading and managing downloadable applications (.exe / .apk)."""

    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

    # Executable / installer file signatures (magic bytes) so we validate the
    # actual file content and do not trust the client-provided extension/MIME.
    _SIGNATURES = {
        'exe': (b'MZ', 'Windows executable (.exe)'),
        'apk': (b'PK\x03\x04', 'Android package (.apk)'),
    }

    class Meta:
        model = Application
        fields = [
            'name', 'description', 'version', 'file', 'icon',
            'is_published', 'is_publicly_downloadable',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Application name'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-input', 'placeholder': 'What does this application do?'}),
            'version': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 1.0.0'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': '.exe,.apk'}),
            'icon': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_publicly_downloadable': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        help_texts = {
            'version': 'Application version, e.g. 1.0.0',
            'is_published': 'Publish so the app appears on the public Apps page.',
            'is_publicly_downloadable': 'Allow visitors to download the file (only applies when published).',
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            # On edits, a missing file means "keep the existing file."
            return file

        # Reject empty files.
        if getattr(file, 'size', None) == 0:
            raise forms.ValidationError('The uploaded file is empty.')

        # Enforce a maximum file size.
        if file.size > self.MAX_FILE_SIZE:
            mb = self.MAX_FILE_SIZE // (1024 * 1024)
            raise forms.ValidationError(f'File is too large. Maximum size is {mb} MB.')

        # Validate actual file content (magic bytes), not the client-provided
        # extension or MIME type.
        extension = (file.name.rsplit('.', 1)[-1] if '.' in file.name else '').lower()
        expected, label = self._SIGNATURES.get(extension, (None, None))
        if expected is None:
            raise forms.ValidationError('Only .exe and .apk files are allowed.')

        header = file.read(len(expected))
        file.seek(0)
        if not header.startswith(expected):
            raise forms.ValidationError(
                f'File content does not match a valid {label}. '
                'The file may be corrupted or of an unsupported type.'
            )

        if extension == 'exe':
            file.seek(0)
            dos_header = file.read(64)
            if len(dos_header) < 64:
                raise forms.ValidationError('The Windows executable is incomplete or corrupted.')
            pe_offset = int.from_bytes(dos_header[0x3C:0x40], 'little')
            if pe_offset < 64 or pe_offset + 4 > file.size:
                raise forms.ValidationError('The Windows executable has an invalid PE header.')
            file.seek(pe_offset)
            if file.read(4) != b'PE\x00\x00':
                raise forms.ValidationError('The file does not contain a valid Windows PE signature.')
        else:
            file.seek(0)
            try:
                with ZipFile(file) as apk:
                    if 'AndroidManifest.xml' not in apk.namelist():
                        raise forms.ValidationError(
                            'The APK archive is missing AndroidManifest.xml.'
                        )
            except BadZipFile as exc:
                raise forms.ValidationError('The APK file is not a valid ZIP archive.') from exc
        file.seek(0)
        return file

    def clean_version(self):
        return (self.cleaned_data.get('version') or '').strip()

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()


class AlbumForm(forms.ModelForm):
    images = MultipleImageField(label='Additional photos')

    class Meta:
        model = Album
        fields = [
            'album_name', 'album_description', 'album_photo',
        ]
        widgets = {
            'album_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Album title'}),
            'album_description': forms.Textarea(attrs={'rows': 4, 'class': 'form-input'}),
            'album_photo': forms.ClearableFileInput(attrs={
                'class': 'form-input', 'accept': 'image/*,.heic,.heif',
            }),
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
            'certificate': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'application/pdf,image/*,.heic,.heif',
            }),
        }

    def clean_certificate(self):
        certificate = self.cleaned_data.get('certificate')
        if not certificate:
            return certificate

        extension = (certificate.name.rsplit('.', 1)[-1] if '.' in certificate.name else '').lower()
        if extension == 'pdf':
            certificate.seek(0)
            if not certificate.read(5).startswith(b'%PDF-'):
                raise forms.ValidationError('The uploaded certificate is not a valid PDF file.')
        elif extension in {
            'jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tif', 'tiff',
            'avif', 'heic', 'heif',
        }:
            try:
                forms.ImageField().clean(certificate)
            except forms.ValidationError as exc:
                raise forms.ValidationError(
                    'Upload a valid PDF or image certificate.'
                ) from exc
        else:
            raise forms.ValidationError('Upload a PDF or image certificate.')

        certificate.seek(0)
        return certificate


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
