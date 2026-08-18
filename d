import os

content = """from django import forms

from .models import Project, ContactMessage


class ContactForm(forms.ModelForm):
    \"\"\"Form for visitors to send a message via the contact page.\"\"\"
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
"""

filepath = os.path.join(os.path.dirname(__file__), '..', 'mytask', 'forms.py')
with open(filepath, 'w') as f:
    f.write(content)
print('File written successfully to', filepath)
