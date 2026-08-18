from django import forms

from .models import Project, ContactMessage, Album


class AlbumAdminForm(forms.ModelForm):
    """Form for creating albums via the admin."""
    album_photo_file = forms.ImageField(required=False, label='Album Photo')

    class Meta:
        model = Album
        fields = ['album_name', 'album_description', 'album_photo_file']

    def save(self, commit=True):
        album = super().save(commit=False)
        if self.cleaned_data.get('album_photo_file'):
            album.album_photo = self.cleaned_data['album_photo_file']
        if commit:
            album.save()
        return album


class ContactForm(forms.ModelForm):
    """Form for visitors to send a message via the contact page."""
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Email',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Subject',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 5,
                'placeholder': 'Your Message',
            }),
        }
