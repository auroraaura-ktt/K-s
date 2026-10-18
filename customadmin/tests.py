from unittest.mock import patch
from tempfile import TemporaryDirectory
from io import BytesIO
from html.parser import HTMLParser
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from myblog.storage import PortfolioMediaCloudinaryStorage
from mytask.models import Application, Album, AlbumImage, Education, Project, ProjectImage
from .forms import ApplicationForm, EducationForm


class FormNestingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.has_nested_forms = False

    def handle_starttag(self, tag, attrs):
        if tag == 'form':
            self.has_nested_forms |= self.depth > 0
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == 'form':
            self.depth = max(0, self.depth - 1)


class AdminWorkflowRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('editor', password='test-password')
        self.client.force_login(self.user)

    def test_education_create_saves_the_form_once(self):
        original_save = EducationForm.save
        with patch.object(
            EducationForm, 'save', autospec=True, side_effect=original_save
        ) as save_mock:
            response = self.client.post('/myadmin/education/add/', {
                'institution': 'Example University',
                'degree': 'BSc',
                'field_of_study': 'Computing',
                'start_date': '2020-01-01',
                'end_date': '',
                'description': 'Coursework',
            })

        self.assertRedirects(response, '/myadmin/education/')
        self.assertEqual(save_mock.call_count, 1)
        self.assertEqual(Education.objects.count(), 1)

    def test_education_certificate_accepts_pdf_and_rejects_fake_pdf_or_executable(self):
        data = {
            'institution': 'Example University',
            'degree': 'BSc',
            'field_of_study': 'Computing',
            'start_date': '2020-01-01',
            'end_date': '',
            'description': 'Coursework',
        }
        valid_pdf = SimpleUploadedFile('certificate.pdf', b'%PDF-1.7\nvalid test fixture')
        self.assertTrue(EducationForm(data, {'certificate': valid_pdf}).is_valid())

        fake_pdf = SimpleUploadedFile('certificate.pdf', b'not a PDF')
        self.assertFalse(EducationForm(data, {'certificate': fake_pdf}).is_valid())

        executable = SimpleUploadedFile('certificate.exe', b'MZ' + b'\x00' * 80)
        self.assertFalse(EducationForm(data, {'certificate': executable}).is_valid())

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get('/myadmin/logout/').status_code, 405)
        response = self.client.post('/myadmin/logout/')
        self.assertRedirects(response, '/myadmin/login/')
        self.assertRedirects(self.client.get('/myadmin/dashboard/'), '/myadmin/login/?next=/myadmin/dashboard/')

    def test_project_image_delete_requires_post_and_correct_parent(self):
        project = Project.objects.create(title='Project', description='Details')
        other_project = Project.objects.create(title='Other', description='Details')
        image = ProjectImage.objects.create(project=project, image='projects/photo.png')
        url = f'/myadmin/projects/{project.pk}/image/{image.pk}/delete/'

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(
            self.client.post(
                f'/myadmin/projects/{other_project.pk}/image/{image.pk}/delete/'
            ).status_code,
            404,
        )
        self.assertTrue(ProjectImage.objects.filter(pk=image.pk).exists())

        response = self.client.post(url)
        self.assertRedirects(response, f'/myadmin/projects/{project.pk}/edit/')
        self.assertFalse(ProjectImage.objects.filter(pk=image.pk).exists())

    def test_inline_image_delete_form_is_separate_from_project_edit_form(self):
        project = Project.objects.create(title='Project', description='Details')
        image = ProjectImage.objects.create(project=project, image='projects/photo.png')

        response = self.client.get(f'/myadmin/projects/{project.pk}/edit/')
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'form="delete-project-image-{image.pk}"', html)
        parser = FormNestingParser()
        parser.feed(html)
        self.assertFalse(parser.has_nested_forms)

    def test_album_image_delete_requires_post_and_correct_parent(self):
        album = Album.objects.create(album_name='Album')
        other_album = Album.objects.create(album_name='Other')
        image = AlbumImage.objects.create(album=album, image='album_photos/photo.png')
        url = f'/myadmin/albums/{album.pk}/image/{image.pk}/delete/'

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(
            self.client.post(
                f'/myadmin/albums/{other_album.pk}/image/{image.pk}/delete/'
            ).status_code,
            404,
        )
        self.assertTrue(AlbumImage.objects.filter(pk=image.pk).exists())

        response = self.client.post(url)
        self.assertRedirects(response, f'/myadmin/albums/{album.pk}/edit/')
        self.assertFalse(AlbumImage.objects.filter(pk=image.pk).exists())

    def test_inline_image_delete_form_is_separate_from_album_edit_form(self):
        album = Album.objects.create(album_name='Album')
        image = AlbumImage.objects.create(album=album, image='album_photos/photo.png')

        response = self.client.get(f'/myadmin/albums/{album.pk}/edit/')
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'form="delete-album-image-{image.pk}"', html)
        parser = FormNestingParser()
        parser.feed(html)
        self.assertFalse(parser.has_nested_forms)

    def test_cloudinary_uses_raw_resources_for_downloadable_files(self):
        storage = PortfolioMediaCloudinaryStorage()

        for filename in ('apps/release.apk', 'apps/setup.exe', 'certificates/degree.pdf'):
            with self.subTest(filename=filename):
                self.assertEqual(storage._get_resource_type(filename), 'raw')

        self.assertEqual(storage._get_resource_type('projects/photo.webp'), 'image')
        self.assertEqual(
            storage._get_resource_type('media/album_photos/extensionless-id'), 'image'
        )
        self.assertIn('/raw/upload/', storage.url('media/apps/release.apk'))

    def test_application_form_checks_extensions_and_file_signatures(self):
        valid_data = {'name': 'Release', 'description': 'Build', 'version': '1.0'}
        exe_bytes = bytearray(128)
        exe_bytes[:2] = b'MZ'
        exe_bytes[0x3C:0x40] = (64).to_bytes(4, 'little')
        exe_bytes[64:68] = b'PE\x00\x00'
        valid_exe = SimpleUploadedFile('setup.exe', bytes(exe_bytes))
        self.assertTrue(ApplicationForm(valid_data, {'file': valid_exe}).is_valid())

        fake_exe = SimpleUploadedFile('setup.exe', b'not an executable')
        form = ApplicationForm(valid_data, {'file': fake_exe})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

        malformed_exe = bytearray(80)
        malformed_exe[:2] = b'MZ'
        fake_pe = SimpleUploadedFile('setup.exe', bytes(malformed_exe))
        self.assertFalse(ApplicationForm(valid_data, {'file': fake_pe}).is_valid())

        apk_bytes = BytesIO()
        with ZipFile(apk_bytes, 'w') as archive:
            archive.writestr('AndroidManifest.xml', b'binary manifest')
        valid_apk = SimpleUploadedFile('release.apk', apk_bytes.getvalue())
        self.assertTrue(ApplicationForm(valid_data, {'file': valid_apk}).is_valid())

        malformed_apk = SimpleUploadedFile('release.apk', b'PK\x03\x04not an apk')
        self.assertFalse(ApplicationForm(valid_data, {'file': malformed_apk}).is_valid())

    def test_public_application_download_returns_original_file_as_attachment(self):
        file_bytes = b'MZ' + b'portfolio-test-binary'
        with TemporaryDirectory() as media_dir:
            storages = {
                'default': {
                    'BACKEND': 'django.core.files.storage.FileSystemStorage',
                    'OPTIONS': {'location': media_dir},
                },
                'staticfiles': {
                    'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
                },
            }
            with override_settings(MEDIA_ROOT=media_dir, STORAGES=storages):
                app = Application.objects.create(
                    name='Test release',
                    description='Temporary test upload',
                    version='1.0',
                    file=SimpleUploadedFile('release.exe', file_bytes),
                    is_published=True,
                    is_publicly_downloadable=True,
                )

                response = self.client.get(f'/app/{app.pk}/download/')

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'application/octet-stream')
                self.assertIn('attachment;', response['Content-Disposition'])
                self.assertEqual(b''.join(response.streaming_content), file_bytes)
