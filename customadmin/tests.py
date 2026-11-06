from unittest.mock import PropertyMock, patch
from tempfile import TemporaryDirectory
from io import BytesIO
from html.parser import HTMLParser
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from myblog.storage import PortfolioMediaCloudinaryStorage
from mytask.models import (
    Application,
    ApplicationImage,
    Album,
    AlbumImage,
    Education,
    PerspectivePage,
    Project,
    ProjectImage,
)
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
            storage._get_resource_type('app-screenshots/screenshot-id'), 'image'
        )
        self.assertEqual(storage._get_resource_type('app-icons/logo-id'), 'image')
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


class AppManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            'app-admin',
            password='test-password',
            is_staff=True,
        )
        self.user = User.objects.create_user('regular-user', password='test-password')
        self.app = Application.objects.create(
            name='Portfolio app',
            short_description='A public preview',
            description='Detailed app information',
            platform='web',
            is_published=True,
        )

    def _png_upload(self, name):
        data = BytesIO()
        Image.new('RGB', (32, 24), color='blue').save(data, format='PNG')
        return SimpleUploadedFile(name, data.getvalue(), content_type='image/png')

    def test_only_staff_can_access_app_management_routes(self):
        protected_urls = [
            '/myadmin/applications/',
            '/myadmin/applications/add/',
            f'/myadmin/applications/{self.app.pk}/edit/',
            f'/myadmin/applications/{self.app.pk}/delete/',
            f'/myadmin/applications/{self.app.pk}/preview/',
        ]
        for url in protected_urls:
            with self.subTest(url=url, user='anonymous'):
                self.client.logout()
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/myadmin/login/', response['Location'])

            with self.subTest(url=url, user='regular'):
                self.client.force_login(self.user)
                self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.user)
        response = self.client.post('/myadmin/applications/add/', {
            'name': 'Unauthorized app',
            'platform': 'web',
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Application.objects.filter(name='Unauthorized app').exists())

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/myadmin/applications/').status_code, 200)

    def test_admin_can_create_published_app_with_only_required_name_and_type(self):
        self.client.force_login(self.admin)
        response = self.client.post('/myadmin/applications/add/', {
            'name': 'No download yet',
            'is_published': 'on',
        })

        self.assertRedirects(response, '/myadmin/applications/')
        app = Application.objects.get(name='No download yet')
        self.assertTrue(app.is_published)
        self.assertFalse(app.file)
        self.assertFalse(app.download_url)
        self.assertFalse(app.website_url)
        self.assertEqual(app.platform, 'other')
        self.assertEqual(app.images.count(), 0)

    def test_external_download_can_be_used_without_uploading_a_file(self):
        self.client.force_login(self.admin)
        url = 'https://github.com/example/project/releases/download/v1/app.apk'
        response = self.client.post('/myadmin/applications/add/', {
            'name': 'External release',
            'platform': 'android',
            'download_url': url,
            'is_published': 'on',
            'is_publicly_downloadable': 'on',
        })

        self.assertRedirects(response, '/myadmin/applications/')
        app = Application.objects.get(name='External release')
        self.assertEqual(app.download_url, url)
        self.assertFalse(app.file)

        public_detail = self.client.get(f'/app/{app.pk}/')
        self.assertContains(public_detail, url)
        self.assertNotContains(public_detail, f'/app/{app.pk}/download/')

    def test_external_urls_reject_unsafe_schemes_and_private_hosts(self):
        for value in ('javascript:alert(1)', 'http://127.0.0.1/file', 'https://[::1]/file'):
            with self.subTest(url=value):
                form = ApplicationForm({
                    'name': 'Unsafe link',
                    'platform': 'web',
                    'download_url': value,
                })
                self.assertFalse(form.is_valid())
                self.assertIn('download_url', form.errors)

    def test_uploaded_file_and_external_url_can_coexist(self):
        data = bytearray(128)
        data[:2] = b'MZ'
        data[0x3C:0x40] = (64).to_bytes(4, 'little')
        data[64:68] = b'PE\x00\x00'
        form = ApplicationForm(
            {
                'name': 'Dual source',
                'platform': 'windows',
                'download_url': 'https://example.com/releases/setup.exe',
            },
            {'file': SimpleUploadedFile('setup.exe', bytes(data))},
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_application_preserves_existing_file_with_unknown_size(self):
        self.app.file = 'apps/existing-release.apk'
        self.app.save(update_fields=['file'])
        form = ApplicationForm(
            {'name': self.app.name, 'platform': 'android'},
            instance=self.app,
        )

        with patch(
            'django.db.models.fields.files.FieldFile.size',
            new_callable=PropertyMock,
            return_value=None,
        ):
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data['file'].name, 'apps/existing-release.apk')

    def test_multiple_screenshots_can_be_added_reordered_and_removed(self):
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
                self.client.force_login(self.admin)
                response = self.client.post(
                    '/myadmin/applications/add/',
                    {
                        'name': 'Gallery app',
                        'platform': 'web',
                        'images': [self._png_upload('first.png'), self._png_upload('second.png')],
                        'is_published': 'on',
                    },
                )
                self.assertRedirects(response, '/myadmin/applications/')
                app = Application.objects.get(name='Gallery app')
                self.assertEqual(app.images.count(), 2)
                self.assertNotIn(
                    'first.png',
                    app.images.first().image.name,
                )
                self.assertContains(self.client.get(f'/app/{app.pk}/'), 'Screenshots')

                first, second = list(app.images.all())
                response = self.client.post(
                    f'/myadmin/applications/{app.pk}/edit/',
                    {
                        'name': app.name,
                        'platform': app.platform,
                        f'image_order_{first.pk}': '1',
                        f'image_order_{second.pk}': '0',
                        'is_published': 'on',
                    },
                )
                self.assertRedirects(response, '/myadmin/applications/')
                first.refresh_from_db()
                second.refresh_from_db()
                self.assertEqual((first.order, second.order), (1, 0))

                response = self.client.get(
                    f'/myadmin/applications/{app.pk}/image/{first.pk}/delete/'
                )
                self.assertEqual(response.status_code, 405)
                response = self.client.post(
                    f'/myadmin/applications/{app.pk}/image/{first.pk}/delete/'
                )
                self.assertRedirects(response, f'/myadmin/applications/{app.pk}/edit/')
                self.assertEqual(ApplicationImage.objects.filter(application=app).count(), 1)

    def test_public_pages_exclude_unpublished_apps_and_missing_downloads_fail_gracefully(self):
        unpublished = Application.objects.create(
            name='Unpublished app',
            platform='web',
            is_published=False,
        )
        self.assertContains(self.client.get('/apps/'), self.app.name)
        self.assertNotContains(self.client.get('/apps/'), unpublished.name)
        self.assertEqual(self.client.get(f'/app/{unpublished.pk}/').status_code, 404)

        app_without_download = Application.objects.create(
            name='No downloadable content',
            platform='web',
            is_published=True,
            is_publicly_downloadable=True,
        )
        detail = self.client.get(f'/app/{app_without_download.pk}/')
        self.assertNotContains(detail, f'/app/{app_without_download.pk}/download/')
        self.assertNotContains(detail, 'External download')

        self.assertEqual(self.client.get(f'/app/{self.app.pk}/download/').status_code, 404)

    def test_missing_uploaded_file_returns_not_found_instead_of_server_error(self):
        app = Application.objects.create(
            name='Missing file',
            platform='windows',
            file='apps/missing-release.exe',
            is_published=True,
            is_publicly_downloadable=True,
        )

        self.assertEqual(self.client.get(f'/app/{app.pk}/download/').status_code, 404)


class PerspectiveManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            'perspective-admin',
            password='test-password',
            is_staff=True,
        )
        self.user = User.objects.create_user('perspective-user', password='test-password')
        self.page = PerspectivePage.objects.get(pk=1)

    def test_only_staff_can_edit_perspective_content(self):
        url = '/myadmin/more-about-me/'

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/myadmin/login/', response['Location'])

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {'title': 'Unauthorized'}).status_code, 403)
        self.assertEqual(self.client.get('/myadmin/perspective/').status_code, 301)

        self.page.refresh_from_db()
        self.assertEqual(self.page.title, 'More About Me')

        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sections')
        self.assertContains(response, '+ Add Section')
        self.assertContains(response, 'Permanently delete the selected section(s)?')

    def test_staff_can_edit_publish_and_reorder_sections(self):
        self.client.force_login(self.admin)
        sections = list(self.page.sections.all())
        data = {
            'title': 'More About Me',
            'introduction': 'A revised introduction from the admin.',
            'is_published': 'on',
            'sections-TOTAL_FORMS': str(len(sections) + 2),
            'sections-INITIAL_FORMS': str(len(sections)),
            'sections-MIN_NUM_FORMS': '0',
            'sections-MAX_NUM_FORMS': '1000',
        }

        for index, section in enumerate(sections):
            data.update({
                f'sections-{index}-id': str(section.pk),
                f'sections-{index}-title': section.title,
                f'sections-{index}-subtitle': section.subtitle,
                f'sections-{index}-content': section.content,
                f'sections-{index}-order': str(10 if index == 0 else index + 1),
                f'sections-{index}-is_published': 'on',
            })
        data.update({
            f'sections-{len(sections)}-id': '',
            f'sections-{len(sections)}-title': 'A New Thought',
            f'sections-{len(sections)}-subtitle': 'A short personal note',
            f'sections-{len(sections)}-content': 'A new editable section.',
            f'sections-{len(sections)}-order': '0',
            f'sections-{len(sections)}-is_published': 'on',
            f'sections-{len(sections) + 1}-id': '',
            f'sections-{len(sections) + 1}-title': 'A Private Draft',
            f'sections-{len(sections) + 1}-subtitle': '',
            f'sections-{len(sections) + 1}-content': '',
            f'sections-{len(sections) + 1}-order': '0',
        })

        response = self.client.post('/myadmin/more-about-me/', data)

        self.assertRedirects(response, '/myadmin/more-about-me/')
        self.page.refresh_from_db()
        self.assertEqual(self.page.introduction, 'A revised introduction from the admin.')
        self.assertTrue(self.page.is_published)
        self.assertEqual(self.page.sections.first().title, 'A New Thought')
        self.assertEqual(self.page.sections.get(title='Who I Am').order, 10)
        self.assertEqual(self.page.sections.count(), len(sections) + 2)

        public_page = self.client.get('/about/more-about-me/')
        self.assertContains(public_page, 'A New Thought')
        self.assertContains(public_page, 'A short personal note')
        self.assertNotContains(public_page, 'A Private Draft')

    def test_dashboard_shows_current_perspective_count_and_management_link(self):
        self.client.force_login(self.admin)

        response = self.client.get('/myadmin/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'More About Me · published / total sections')
        self.assertContains(response, '5/5')
        self.assertContains(response, 'Page published')
        self.assertContains(response, 'href="/myadmin/more-about-me/"')

        self.page.sections.filter(title='Who I Am').update(is_published=False)
        response = self.client.get('/myadmin/dashboard/')
        self.assertContains(response, '4/5')
        self.page.is_published = False
        self.page.save(update_fields=['is_published'])
        response = self.client.get('/myadmin/dashboard/')
        self.assertContains(response, 'Page unpublished')

    def test_staff_can_delete_a_section_and_it_stays_deleted(self):
        self.client.force_login(self.admin)
        section = self.page.sections.get(title='Who I Am')
        sections = list(self.page.sections.all())
        data = {
            'title': self.page.title,
            'introduction': self.page.introduction,
            'is_published': 'on',
            'sections-TOTAL_FORMS': str(len(sections)),
            'sections-INITIAL_FORMS': str(len(sections)),
            'sections-MIN_NUM_FORMS': '0',
            'sections-MAX_NUM_FORMS': '1000',
        }
        for index, item in enumerate(sections):
            data.update({
                f'sections-{index}-id': str(item.pk),
                f'sections-{index}-title': item.title,
                f'sections-{index}-subtitle': item.subtitle,
                f'sections-{index}-content': item.content,
                f'sections-{index}-order': str(item.order),
            })
            if item.is_published:
                data[f'sections-{index}-is_published'] = 'on'
        data['sections-0-DELETE'] = 'on'

        response = self.client.post('/myadmin/more-about-me/', data)

        self.assertRedirects(response, '/myadmin/more-about-me/')
        self.assertFalse(self.page.sections.filter(pk=section.pk).exists())
        self.assertFalse(self.client.get('/about/more-about-me/').context['perspective_page'].sections.filter(pk=section.pk).exists())
