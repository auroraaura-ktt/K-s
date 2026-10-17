import re

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.utils import timezone
import uuid

# Sentence boundary used when re-flowing hard-wrapped descriptions.
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')

# Paragraphs are grouped up to roughly this many characters so a long
# description reads as a few comfortable blocks instead of one tall wall.
_PARAGRAPH_TARGET_CHARS = 420

# The lead summary at the top of the detail panel is capped at roughly
# this many characters, cut on a sentence boundary.
_SUMMARY_TARGET_CHARS = 180

# Optional list-style project fields are stored as free text and parsed into
# lists on the way out. Splitting on newlines first means an author can write
# one item per line; commas and semicolons keep single-line lists working.
_LIST_SPLIT = re.compile(r'[\n;]+|,')
_LIST_ITEM_TRIM = re.compile(r'^[\s\-*•·✓✔–—]+|[\s,;]+$')


def _parse_list_field(value):
    """Turn an optional free-text field into a clean list of items.

    Returns an empty list for missing/blank values so templates can simply
    check `{% if project.technologies %}` and skip the whole section.
    """
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = _LIST_SPLIT.split(str(value))
    return [clean for clean in (_LIST_ITEM_TRIM.sub('', str(i)) for i in items) if clean]


# Hosts that must never be published as a public "Live Demo" link. A
# developer can still store one by accident, but the detail page will not
# render a button that leaks a local machine or a private network address.
_PRIVATE_URL_HOSTS = re.compile(
    r'^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1\]?|0\.0\.0\.0)',
    re.IGNORECASE,
)

_url_validator = URLValidator(schemes=['http', 'https'])


def sanitize_external_url(value):
    """Return a safe external URL string, or '' when it cannot be trusted.

    The stored value is used verbatim whenever possible - no scheme is
    rewritten, no path is rebuilt and nothing is truncated. It is only
    rejected when it is blank, not a syntactically valid http(s) URL, or
    points at a private/loopback host, in which case callers simply render
    no link at all rather than a broken or leaking one.
    """
    if not value:
        return ''

    url = str(value).strip()
    if not url:
        return ''

    try:
        _url_validator(url)
    except ValidationError:
        return ''

    # Reject credentials embedded in the URL and private/loopback hosts.
    remainder = url.split('://', 1)[-1]
    if remainder.split('@')[-1] != remainder:
        return ''

    host = remainder.split('/', 1)[0].split('?', 1)[0].split('#', 1)[0]
    host = host.rsplit(':', 1)[0] if host.count(':') == 1 else host
    if not host or _PRIVATE_URL_HOSTS.match(host):
        return ''

    return url



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

    # ----- Optional case-study fields -------------------------------------
    # Every field below is blank by default, so existing projects keep
    # rendering exactly as before and each section is only shown when the
    # author actually filled something in.
    role = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. Full Stack Developer",
    )
    client = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Completed, In Progress",
    )
    technologies = models.TextField(
        blank=True,
        help_text="One per line, or separated by commas",
    )
    features = models.TextField(
        blank=True,
        help_text="One key feature per line, or separated by commas",
    )
    responsibilities = models.TextField(
        blank=True,
        help_text="One responsibility per line, or separated by commas",
    )
    additional_info = models.TextField(
        blank=True,
        help_text="Any extra notes shown as an additional information section",
    )

    def __str__(self):
        return self.title

    @property
    def technology_list(self):
        return _parse_list_field(self.technologies)

    @property
    def feature_list(self):
        return _parse_list_field(self.features)

    @property
    def responsibility_list(self):
        return _parse_list_field(self.responsibilities)

    @property
    def live_url(self):
        """The project's own live/demo URL, or '' when unusable.

        Used verbatim: no scheme rewriting, no rebuilding, no truncation
        and no fallback to any other URL. Templates render the Live Demo
        action only when this is non-empty, so a project without a real
        public URL simply gets no button rather than a broken one.
        """
        return sanitize_external_url(self.url)

    @property
    def repository_url(self):
        """The project's own GitHub URL, or '' when unusable."""
        return sanitize_external_url(self.github_url)

    @property
    def all_photos(self):
        """Main photo first, followed by any additional project images."""
        photos = []
        if self.photo:
            photos.append(self.photo)
        photos += [img.image for img in self.images.all()]
        return photos

    @property
    def description_paragraphs(self):
        """Split the description into readable paragraphs.

        Project descriptions are usually typed as hard-wrapped plain text,
        so a single string with no blank lines. Rendering that verbatim makes
        a very tall, hard-to-scan column. This re-flows the text and groups
        whole sentences into a handful of paragraphs, which keeps the full
        description while giving the page a comfortable reading rhythm.

        Descriptions that already contain blank-line separated paragraphs are
        respected as written.
        """
        text = (self.description or '').strip()
        if not text:
            return []

        # Honour paragraphs the author actually typed.
        blocks = [re.sub(r'\s+', ' ', part).strip()
                  for part in re.split(r'\n\s*\n', text)]
        blocks = [block for block in blocks if block]

        if len(blocks) < 2:
            # Hard-wrapped text: re-flow, then regroup sentences.
            flow = re.sub(r'\s+', ' ', text).strip()
            sentences = [s.strip() for s in _SENTENCE_SPLIT.split(flow) if s.strip()]

            blocks = []
            current = ''
            for sentence in sentences:
                if current and len(current) + len(sentence) + 1 > _PARAGRAPH_TARGET_CHARS:
                    blocks.append(current)
                    current = sentence
                else:
                    current = f'{current} {sentence}'.strip()
            if current:
                blocks.append(current)

        return blocks

    @property
    def summary(self):
        """A short lead sentence for the top of the detail panel.

        Cut on a sentence boundary so it always reads as a finished
        thought, and so it is a strict prefix of the description when
        the description has more to say (see description_body_paragraphs).
        """
        paragraphs = self.description_paragraphs
        if not paragraphs:
            return ''

        first = paragraphs[0]
        if len(first) <= _SUMMARY_TARGET_CHARS:
            return first

        summary = ''
        for sentence in _SENTENCE_SPLIT.split(first):
            sentence = sentence.strip()
            if not sentence:
                continue
            if summary and len(summary) + len(sentence) + 1 > _SUMMARY_TARGET_CHARS:
                break
            summary = f'{summary} {sentence}'.strip()

        return summary or first[:_SUMMARY_TARGET_CHARS].rsplit(' ', 1)[0] + '...'

    @property
    def description_body_paragraphs(self):
        """Description paragraphs for the 'About This Project' section.

        When the lead summary is only the opening sentences of a longer
        description, that first paragraph would otherwise be printed
        twice - once under the title and again under the heading. The
        overlapping part is dropped here so the text reads once, top to
        bottom, while every remaining sentence is still shown.

        Falls back to the full description whenever dropping anything
        would leave the section empty, so no text is ever lost.
        """
        paragraphs = self.description_paragraphs
        if len(paragraphs) < 2:
            return paragraphs

        first = paragraphs[0]
        summary = self.summary
        # Only safe when the summary is the start of the first paragraph
        # and leaves the rest of it to be shown here.
        if summary and summary != first and first.startswith(summary):
            remainder = first[len(summary):].strip()
            if remainder:
                return [remainder] + paragraphs[1:]

        return paragraphs


class ProjectImage(models.Model):
    """Additional photo belonging to a project."""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(upload_to='projects/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Project image: {self.project.title}"


def app_upload_path(instance, filename):
    """Opaque private storage key; never derive a path from the client name."""
    extension = filename.rsplit('.', 1)[-1].lower()
    return f'apps/{uuid.uuid4().hex}.{extension}'


class Application(models.Model):
    """Downloadable Windows or Android application in the single-owner portfolio."""
    PLATFORM_CHOICES = [('windows', 'Windows'), ('android', 'Android')]
    name = models.CharField(max_length=200)
    description = models.TextField()
    version = models.CharField(max_length=50)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, editable=False)
    file = models.FileField(
        upload_to=app_upload_path,
        validators=[FileExtensionValidator(['exe', 'apk'])],
        max_length=500,
    )
    original_filename = models.CharField(max_length=255, editable=False)
    file_size = models.PositiveBigIntegerField(default=0, editable=False)
    icon = models.ImageField(upload_to='app-icons/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    is_publicly_downloadable = models.BooleanField(default=False)
    date_created = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created', '-id']

    def save(self, *args, **kwargs):
        if self.file:
            name = self.file.name
            extension = name.rsplit('.', 1)[-1].lower()
            if extension not in ('exe', 'apk'):
                raise ValidationError('Only .exe and .apk files are allowed.')
            self.platform = 'windows' if extension == 'exe' else 'android'
            if hasattr(self.file, 'size'):
                self.file_size = self.file.size
            if hasattr(self.file, 'name'):
                self.original_filename = name.rsplit('/', 1)[-1].rsplit('\\\\', 1)[-1][:255]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


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

    @property
    def all_photos(self):
        """Main photo first, followed by any additional album images."""
        photos = []
        if self.album_photo:
            photos.append(self.album_photo)
        photos += [img.image for img in self.images.all()]
        return photos


class AlbumImage(models.Model):
    """Additional photo belonging to an album."""
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(upload_to='album_photos/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Album image: {self.album.album_name}"
