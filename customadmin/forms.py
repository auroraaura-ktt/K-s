from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps

from io import BytesIO
from zipfile import BadZipFile, ZipFile

from mytask.models import (
    Application,
    ApplicationImage,
    sanitize_external_url,
    Profile,
    Project,
    Skill,
    Experience,
    Education,
    SocialLink,
    Album,
    PerspectivePage,
    PerspectiveSection,
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
    """Form for managing public app details and optional distribution files."""

    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB
    MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024
    MAX_SCREENSHOTS_PER_UPLOAD = 20
    platform = forms.ChoiceField(
        choices=Application.PLATFORM_CHOICES,
        required=False,
        initial='other',
        widget=forms.Select(attrs={'class': 'form-input'}),
    )

    _SIGNATURES = {
        'exe': (b'MZ', 'Windows executable (.exe)'),
        'apk': (b'PK\x03\x04', 'Android package (.apk)'),
        'msi': (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 'Windows installer (.msi)'),
        'zip': (b'PK\x03\x04', 'ZIP archive (.zip)'),
    }

    images = MultipleImageField(label='Screenshots and review photos')

    class Meta:
        model = Application
        fields = [
            'name', 'short_description', 'description', 'platform', 'version',
            'category', 'technologies', 'features', 'website_url', 'download_url', 'file', 'icon',
            'is_published', 'is_publicly_downloadable',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Application name'}),
            'short_description': forms.Textarea(attrs={
                'rows': 2, 'class': 'form-input', 'placeholder': 'A brief introduction',
            }),
            'description': forms.Textarea(attrs={
                'rows': 5, 'class': 'form-input', 'placeholder': 'Detailed app information',
            }),
            'platform': forms.Select(attrs={'class': 'form-input'}),
            'version': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 1.0.0'}),
            'category': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Productivity'}),
            'technologies': forms.Textarea(attrs={
                'rows': 3, 'class': 'form-input', 'placeholder': 'React, Python, Flutter...',
            }),
            'features': forms.Textarea(attrs={
                'rows': 4, 'class': 'form-input', 'placeholder': 'One application feature per line',
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'form-input', 'placeholder': 'https://example.com',
            }),
            'download_url': forms.URLInput(attrs={
                'class': 'form-input', 'placeholder': 'https://github.com/.../releases/download/...',
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-input', 'accept': '.exe,.apk,.msi,.zip',
            }),
            'icon': forms.ClearableFileInput(attrs={
                'class': 'form-input', 'accept': 'image/*',
            }),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_publicly_downloadable': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        help_texts = {
            'version': 'Application version, e.g. 1.0.0',
            'features': 'Optional. Enter one feature per line.',
            'is_published': 'Publish so the app appears on the public Apps page.',
            'is_publicly_downloadable': 'Show available download options to visitors (only applies when published).',
            'file': 'Optional. Files larger than 200 MB should be hosted externally instead.',
            'download_url': 'Optional. Paste a public HTTP(S) URL, including a GitHub Releases asset URL.',
        }

    def clean_website_url(self):
        return self._clean_public_url('website_url')

    def clean_platform(self):
        return self.cleaned_data.get('platform') or 'other'

    def clean_download_url(self):
        return self._clean_public_url('download_url')

    def _clean_public_url(self, field_name):
        value = (self.cleaned_data.get(field_name) or '').strip()
        if value and not sanitize_external_url(value):
            raise forms.ValidationError('Enter a safe public HTTP or HTTPS URL.')
        return value or None

    def clean_images(self):
        images = self.cleaned_data.get('images', [])
        if len(images) > self.MAX_SCREENSHOTS_PER_UPLOAD:
            raise forms.ValidationError(
                f'Upload no more than {self.MAX_SCREENSHOTS_PER_UPLOAD} screenshots at once.'
            )
        for image in images:
            if image.size > self.MAX_SCREENSHOT_SIZE:
                raise forms.ValidationError('Each screenshot must be 10 MB or smaller.')
        return [self._optimize_screenshot(image) for image in images]

    @staticmethod
    def _optimize_screenshot(upload):
        upload.seek(0)
        with Image.open(upload) as source:
            image_format = source.format
            if image_format not in ('JPEG', 'PNG', 'WEBP'):
                upload.seek(0)
                return upload

            image = ImageOps.exif_transpose(source)
            image.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            optimized = BytesIO()
            options = {'optimize': True}
            if image_format in ('JPEG', 'WEBP'):
                options['quality'] = 88
            image.save(optimized, format=image_format, **options)

        if optimized.tell() >= upload.size:
            upload.seek(0)
            return upload
        return SimpleUploadedFile(
            upload.name,
            optimized.getvalue(),
            content_type=upload.content_type,
        )

    def clean(self):
        cleaned_data = super().clean()
        self.image_orders = {}
        if self.instance.pk:
            for image in self.instance.images.all():
                value = self.data.get(f'image_order_{image.pk}')
                if value is None:
                    continue
                try:
                    order = int(value)
                    if order < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    self.add_error('images', 'Screenshot order must be a non-negative number.')
                else:
                    self.image_orders[image.pk] = order
        return cleaned_data

    def save_images(self, application):
        for image in application.images.all():
            if image.pk in self.image_orders:
                image.order = self.image_orders[image.pk]
                image.save(update_fields=['order'])

        next_order = max(
            (image.order for image in application.images.all()),
            default=-1,
        ) + 1
        for offset, upload in enumerate(self.cleaned_data.get('images', [])):
            ApplicationImage.objects.create(
                application=application,
                image=upload,
                order=next_order + offset,
            )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            return file

        if getattr(file, 'size', None) == 0:
            raise forms.ValidationError('The uploaded file is empty.')

        if file.size > self.MAX_FILE_SIZE:
            mb = self.MAX_FILE_SIZE // (1024 * 1024)
            raise forms.ValidationError(
                f'File is too large. Maximum size is {mb} MB; use an external download URL for larger files.'
            )

        extension = (file.name.rsplit('.', 1)[-1] if '.' in file.name else '').lower()
        expected, label = self._SIGNATURES.get(extension, (None, None))
        if expected is None:
            raise forms.ValidationError('Only .exe, .apk, .msi, and .zip files are allowed.')

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
        elif extension in ('apk', 'zip'):
            file.seek(0)
            try:
                with ZipFile(file) as apk:
                    if extension == 'apk' and 'AndroidManifest.xml' not in apk.namelist():
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


class PerspectivePageForm(forms.ModelForm):
    class Meta:
        model = PerspectivePage
        fields = ["title", "introduction", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "introduction": forms.Textarea(attrs={"class": "form-input", "rows": 5}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class PerspectiveSectionForm(forms.ModelForm):
    class Meta:
        model = PerspectiveSection
        fields = ["title", "subtitle", "content", "order", "is_published"]
        labels = {"is_published": "Published on public page"}
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "subtitle": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Optional subtitle",
            }),
            "content": forms.Textarea(attrs={"class": "form-input", "rows": 4}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
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
