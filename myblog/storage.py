import os
from hashlib import sha256
from pathlib import Path, PurePosixPath

from cloudinary_storage.storage import MediaCloudinaryStorage
from django.core.files.storage import FileSystemStorage
from PIL import Image, ImageOps


class LocalHybridMediaStorage(FileSystemStorage):
    """Use local files normally and Cloudinary for existing server uploads."""

    DISPLAY_DERIVATIVE_EXTENSIONS = {'.heic', '.heif', '.tif', '.tiff', '.avif'}

    @staticmethod
    def _is_cloudinary_name(name):
        return str(name).replace('\\', '/').startswith('media/')

    @property
    def cloudinary_storage(self):
        return PortfolioMediaCloudinaryStorage()

    def url(self, name):
        if self._is_cloudinary_name(name):
            return self.cloudinary_storage.url(name)
        if PurePosixPath(str(name).replace('\\', '/')).suffix.lower() in self.DISPLAY_DERIVATIVE_EXTENSIONS:
            return super().url(self._ensure_display_derivative(name))
        return super().url(name)

    def _display_derivative_name(self, name):
        digest = sha256(str(name).replace('\\', '/').encode('utf-8')).hexdigest()
        return f'.display-cache/{digest}.webp'

    def _ensure_display_derivative(self, name):
        derivative_name = self._display_derivative_name(name)
        source_path = Path(self.path(name))
        derivative_path = Path(self.path(derivative_name))
        derivative_path.parent.mkdir(parents=True, exist_ok=True)

        if (derivative_path.is_file()
                and derivative_path.stat().st_mtime >= source_path.stat().st_mtime):
            return derivative_name

        temporary_path = derivative_path.with_name(
            f'.{derivative_path.stem}.{os.getpid()}.tmp.webp'
        )
        try:
            with Image.open(source_path) as source:
                source.seek(0)
                oriented = ImageOps.exif_transpose(source)
                mode = 'RGBA' if 'A' in oriented.getbands() else 'RGB'
                converted = oriented.convert(mode)
                save_options = {'format': 'WEBP', 'quality': 90, 'method': 6}
                icc_profile = source.info.get('icc_profile')
                if icc_profile:
                    save_options['icc_profile'] = icc_profile
                converted.save(temporary_path, **save_options)
            os.replace(temporary_path, derivative_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

        return derivative_name

    def open(self, name, mode='rb'):
        if self._is_cloudinary_name(name):
            return self.cloudinary_storage.open(name, mode)
        return super().open(name, mode)

    def exists(self, name):
        if self._is_cloudinary_name(name):
            return self.cloudinary_storage.exists(name)
        return super().exists(name)

    def size(self, name):
        if self._is_cloudinary_name(name):
            return self.cloudinary_storage.size(name)
        return super().size(name)

    def delete(self, name):
        if self._is_cloudinary_name(name):
            self.cloudinary_storage.delete(name)
            return
        result = super().delete(name)
        if PurePosixPath(str(name).replace('\\', '/')).suffix.lower() in self.DISPLAY_DERIVATIVE_EXTENSIONS:
            super().delete(self._display_derivative_name(name))
        return result


class PortfolioMediaCloudinaryStorage(MediaCloudinaryStorage):
    """Route image and downloadable file uploads to the right Cloudinary type.

    django-cloudinary-storage uploads media names with their extension in the
    public ID. Cloudinary also needs the delivery format suffix, so an image
    stored as ``photo.jpg`` is served from ``photo.jpg.jpg``. Keep the stored
    database name intact and add that suffix only to the generated URL. Other
    files such as APKs, EXEs, PDFs and resumes must use Cloudinary's ``raw``
    resource type so they remain downloadable and are not processed as images.
    """

    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff',
        '.heic', '.heif', '.avif',
    }
    IMAGE_UPLOAD_DIRS = {'profile', 'projects', 'album_photos', 'app-icons'}

    def _get_resource_type(self, name):
        path = PurePosixPath(str(name).replace('\\', '/'))
        extension = path.suffix.lower()
        directories = {part.lower() for part in path.parts[:-1]}
        if extension in self.IMAGE_EXTENSIONS or directories & self.IMAGE_UPLOAD_DIRS:
            return 'image'
        return 'raw'

    def _get_url(self, name):
        url = super()._get_url(name)
        normalized_name = str(name).replace('\\', '/')
        extension = PurePosixPath(normalized_name).suffix.lower()
        if extension in self.IMAGE_EXTENSIONS and not url.lower().endswith(extension + extension):
            url = f'{url}{extension}'
        return url

    def url(self, name):
        url = self._get_url(name)
        normalized_name = str(name).replace('\\', '/')
        extension = PurePosixPath(normalized_name).suffix.lower()
        if extension in self.IMAGE_EXTENSIONS or not extension:
            return url.replace('/image/upload/', '/image/upload/f_auto/', 1)
        return url

    def delete(self, name):
        # Older records store paths without MEDIA_URL's prefix, while newer
        # uploads store the already-prefixed Cloudinary public ID.
        return super().delete(self._prepend_prefix(name))
