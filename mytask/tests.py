from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .forms import AlbumAdminForm
from .models import Album


class AlbumAdminTests(TestCase):
    def test_admin_form_can_create_album_with_photo(self):
        image_file = BytesIO()
        Image.new("RGB", (100, 100), color="red").save(image_file, format="PNG")
        image_file.seek(0)

        image = SimpleUploadedFile(
            "test.png",
            image_file.read(),
            content_type="image/png",
        )

        form = AlbumAdminForm(
            data={
                "album_name": "Summer Trip",
                "album_description": "A lovely album",
            },
            files={"album_photo_file": image},
        )

        self.assertTrue(form.is_valid(), form.errors)
        album = form.save()

        self.assertEqual(album.album_name, "Summer Trip")
        self.assertTrue(album.album_photo)
        self.assertTrue(album.album_photo.name.startswith("album_photos/"))
