from django.db import models


class Profile(models.Model):
    """Personal profile information for the portfolio."""
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, help_text="e.g. Full Stack Developer")
    bio = models.TextField(help_text="Short biography or introduction")
    photo = models.ImageField(
        upload_to='profile/',
        blank=True,
        null=True,
    )
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    github = models.CharField(max_length=300, blank=True)
    linkedin = models.CharField(max_length=300, blank=True)
    twitter = models.CharField(max_length=300, blank=True)
    website = models.CharField(max_length=300, blank=True)
    resume = models.FileField(
        upload_to='resume/',
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class SocialLink(models.Model):
    """Custom social link with configurable name and URL (shown on home hero)."""
    name = models.CharField(max_length=50, help_text="e.g. GitHub, LinkedIn, Instagram, Email")
    url = models.CharField(max_length=300, help_text="Full URL (or email address for mailto links)")
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional Font Awesome class, e.g. 'fa-brands fa-instagram'. Auto-detected from name if blank.",
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower = first)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

    @property
    def href(self):
        """Return a usable link: prefixes mailto: for bare email addresses."""
        url = (self.url or '').strip()
        if '@' in url and not url.lower().startswith(('http://', 'https://', 'mailto:')):
            return f'mailto:{url}'
        return url

    @property
    def icon_class(self):
        """Explicit icon if set, otherwise auto-detect from the name."""
        if self.icon:
            return self.icon
        name = (self.name or '').lower()
        url = (self.url or '').lower()
        if 'github' in name or 'github.com' in url:
            return 'fa-brands fa-github'
        if 'linkedin' in name or 'linkedin.com' in url:
            return 'fa-brands fa-linkedin-in'
        if 'instagram' in name or 'instagram.com' in url:
            return 'fa-brands fa-instagram'
        if 'tiktok' in name or 'tiktok.com' in url:
            return 'fa-brands fa-tiktok'
        if 'youtube' in name or 'youtube.com' in url:
            return 'fa-brands fa-youtube'
        if 'facebook' in name or 'facebook.com' in url:
            return 'fa-brands fa-facebook'
        if 'twitter' in name or name == 'x' or 'x.com' in url:
            return 'fa-brands fa-x-twitter'
        if 'email' in name or 'mail' in name:
            return 'fa-regular fa-envelope'
        return 'fa-solid fa-link'


class Project(models.Model):
    """Portfolio project."""
    title = models.CharField(max_length=200)
    description = models.TextField()
    photo = models.ImageField(
        upload_to='projects/',
        blank=True,
        null=True,
    )
    url = models.URLField(blank=True, help_text="Live demo URL")
    github_url = models.URLField(blank=True, help_text="GitHub repository URL")
    date_created = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Skill(models.Model):
    """A skill with proficiency level."""
    name = models.CharField(max_length=100)
    proficiency = models.IntegerField(
        help_text="Proficiency level (0-100)",
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Icon class or emoji",
    )
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Experience(models.Model):
    """Work experience entry."""
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} at {self.company}"


class Education(models.Model):
    """Education entry."""
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    certificate = models.FileField(
        upload_to='certificates/',
        blank=True,
        null=True,
        help_text="Certificate file (PDF or image) for this degree/program",
    )

    def __str__(self):
        return f"{self.degree} at {self.institution}"


class ContactMessage(models.Model):
    """Message sent via the contact form."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"


class Album(models.Model):
    """Photo album collection."""
    album_name = models.CharField(max_length=200)
    album_description = models.TextField(blank=True)
    album_photo = models.ImageField(
        upload_to='album_photos/',
        blank=True,
        null=True,
    )
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.album_name
