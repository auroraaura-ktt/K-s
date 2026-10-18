from django.apps import AppConfig


class MytaskConfig(AppConfig):
    name = 'mytask'

    def ready(self):
        # Register HEIC/HEIF with Pillow so Django's ImageField validates the
        # real image data instead of accepting these files by extension alone.
        from pillow_heif import register_heif_opener

        register_heif_opener()
