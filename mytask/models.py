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
    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    website = models.URLField(blank=True)
    resume = models.FileField(
        upload_to='resume/',
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


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
