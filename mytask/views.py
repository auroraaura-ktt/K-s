from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import Http404, FileResponse

from .models import Application, Project, Profile, Skill, Experience, Education, ContactMessage, Album, SocialLink
from .forms import ContactForm


def get_active_profile():
    """Return the active profile or None."""
    try:
        return Profile.objects.get(is_active=True)
    except Profile.DoesNotExist:
        return None


def home(request):
    """Home / landing page with hero section."""
    profile = get_active_profile()
    projects = Project.objects.all().order_by('-date_created')[:6]
    social_links = SocialLink.objects.filter(is_active=True)
    return render(request, 'home.html', {
        'profile': profile,
        'projects': projects,
        'social_links': social_links,
    })


def about(request):
    """About page with skills, experience, and education."""
    profile = get_active_profile()
    skills = Skill.objects.filter(is_featured=True)
    experiences = Experience.objects.all().order_by('-start_date')
    educations = Education.objects.all().order_by('-start_date')
    return render(request, 'about.html', {
        'profile': profile,
        'skills': skills,
        'experiences': experiences,
        'educations': educations,
    })


def education(request):
    """Education page with degrees and certificates."""
    profile = get_active_profile()
    educations = Education.objects.all().order_by('-start_date')
    return render(request, 'education.html', {
        'profile': profile,
        'educations': educations,
    })


def albums(request):
    """Albums / photo gallery listing page."""
    profile = get_active_profile()
    albums = Album.objects.all().order_by('-date_created')
    return render(request, 'albums.html', {
        'profile': profile,
        'albums': albums,
    })


def album_detail(request, album_id):
    """Single album detail page."""
    profile = get_active_profile()
    album = get_object_or_404(Album, id=album_id)
    return render(request, 'album_details.html', {
        'profile': profile,
        'album': album,
    })


def projects(request):
    """Projects / portfolio listing page."""
    profile = get_active_profile()
    all_projects = Project.objects.all().order_by('-date_created')
    featured_projects = Project.objects.filter(is_featured=True).order_by('-date_created')
    return render(request, 'projects.html', {
        'profile': profile,
        'projects': all_projects,
        'featured_projects': featured_projects,
    })


def project_detail(request, project_id):
    """Single project detail page."""
    profile = get_active_profile()
    project = get_object_or_404(Project, id=project_id)

    # Order every project most-recent-first so we can build prev/next
    # navigation and a "More Projects" section around the current one.
    ordered = list(Project.objects.order_by('-date_created', '-id'))
    try:
        index = next(i for i, p in enumerate(ordered) if p.id == project.id)
    except StopIteration:
        index = -1

    prev_project = ordered[index - 1] if 0 < index < len(ordered) else None
    next_project = ordered[index + 1] if 0 <= index < len(ordered) - 1 else None
    more_projects = [p for p in ordered if p.id != project.id][:4]

    return render(request, 'project_detail.html', {
        'profile': profile,
        'project': project,
        'prev_project': prev_project,
        'next_project': next_project,
        'more_projects': more_projects,
    })


def contact(request):
    """Contact page with a message form."""
    profile = get_active_profile()
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your message has been sent! I will get back to you soon.')
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {
        'profile': profile,
        'form': form,
    })


def apps(request):
    """Public Apps listing page (published applications only)."""
    profile = get_active_profile()
    applications = Application.objects.filter(is_published=True).order_by('-date_created')
    return render(request, 'apps.html', {
        'profile': profile,
        'applications': applications,
    })


def app_detail(request, app_id):
    """Single application detail page (published applications only)."""
    profile = get_active_profile()
    app = get_object_or_404(Application, id=app_id, is_published=True)
    return render(request, 'app_detail.html', {
        'profile': profile,
        'app': app,
    })


def app_download(request, app_id):
    """Secure download endpoint for published, publicly downloadable apps.

    Only applications flagged as both published and publicly downloadable can
    be fetched through this endpoint; everything else returns 404 so the
    existence of private/restricted builds is not leaked.
    """
    app = get_object_or_404(
        Application,
        id=app_id,
        is_published=True,
        is_publicly_downloadable=True,
    )
    if not app.file:
        raise Http404('No file is attached to this application.')

    # Serve as an attachment so the browser downloads the binary instead of
    # attempting to display or execute it. Content-Type is forced to a generic
    # binary type and MIME sniffing is disabled.
    file = app.file.open('rb')
    response = FileResponse(
        file,
        as_attachment=True,
        filename=app.original_filename or app.file.name.rsplit('/', 1)[-1],
    )
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Length'] = app.file_size or app.file.size
    response['X-Content-Type-Options'] = 'nosniff'
    return response
