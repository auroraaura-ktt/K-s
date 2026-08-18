from .models import Profile


def site_profile(request):
    """Make the active profile available globally in templates."""
    profile = None
    try:
        profile = Profile.objects.filter(is_active=True).first()
    except Profile.DoesNotExist:
        pass
    return {'site_profile': profile}