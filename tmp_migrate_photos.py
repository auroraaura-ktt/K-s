"""
One-time migration: restore previously uploaded photos by copying the existing
local media files into Cloudinary using the exact public_id that
MediaCloudinaryStorage derives from each stored DB name.

MediaCloudinaryStorage.url(name) does: public_id = 'media/' + name   (PREFIX = MEDIA_URL = '/media/')
so a DB-stored name 'album_photos/FB_IMG_1705506267265.jpg' resolves to the
Cloudinary public_id 'media/album_photos/FB_IMG_1705506267265.jpg'.

No database records are modified. Original local files are preserved (already
backed up to media_backup_*). This is idempotent: already-uploaded resources
are skipped.
"""
import os
import sys
import mimetypes
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env.development.local")

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myblog.settings")
django.setup()

import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.core.files.storage import storages
from mytask.models import Album, AlbumImage, Profile, Project, Education, Application

# Explicitly configure the Cloudinary SDK from env (app_settings only configures
# it when a CLOUDINARY_STORAGE dict is present in settings; here credentials are
# supplied via individual env vars, so we configure it directly).
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True,
)

storage = storages["default"]
print("Storage backend:", storage.__class__.__name__)
print("Cloudinary configured:", bool(cloudinary.config().cloud_name))

# (label, stored_db_name, local_media_path)
TO_RESTORE = [
    ("Album.id=1.album_photo",  "album_photos/FB_IMG_1705506267265.jpg",
     settings.MEDIA_ROOT / "album_photos/FB_IMG_1705506267265.jpg"),
    ("Album.id=2.album_photo",  "album_photos/canva-meme-cat-heart-cute-shy-embarrassed-CVBohzyf-nk.jpg",
     settings.MEDIA_ROOT / "album_photos/canva-meme-cat-heart-cute-shy-embarrassed-CVBohzyf-nk.jpg"),
    ("Album.id=3.album_photo",  "album_photos/pexels-photo-341970_ZBHXSXQ.webp",
     settings.MEDIA_ROOT / "album_photos/pexels-photo-341970_ZBHXSXQ.webp"),
    ("Project.id=2.photo",      "projects/Screenshot_2026-10-08_135640.png",
     settings.MEDIA_ROOT / "projects/Screenshot_2026-10-08_135640.png"),
]

results = []
for label, stored_name, local_path in TO_RESTORE:
    entry = {"label": label, "stored_name": stored_name, "local_exists": local_path.exists()}
    cloud_public_id = "media/" + stored_name  # matches what url()/exists() derive
    if not local_path.exists():
        entry.update(status="SKIPPED-MISSING-LOCAL", reason="local file not found")
        results.append(entry)
        continue

    # Skip if Cloudinary already has this exact resource.
    if storage.exists(stored_name):
        entry.update(status="ALREADY_IN_CLOUDINARY")
    else:
        with open(local_path, "rb") as fh:
            content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
            resp = cloudinary.uploader.upload(
                fh,
                public_id=cloud_public_id,
                resource_type="image",
                content_type=content_type,
                tags=["media", "migration-restore"],
            )
        entry["cloudinary_public_id"] = resp.get("public_id")
        entry["cloudinary_version"] = resp.get("version")

    # Verify the URL the application will actually render.
    url = storage.url(stored_name)
    entry["rendered_url"] = url
    try:
        r = requests.get(url, timeout=30)
        entry["http_status"] = r.status_code
        entry["content_type"] = r.headers.get("content-type")
        entry["bytes"] = len(r.content)
        entry["status"] = entry.get("status") or ("OK" if r.status_code == 200 else "HTTP_ERROR")
    except Exception as exc:
        entry["http_status"] = None
        entry["error"] = repr(exc)
        entry["status"] = "FETCH_FAILED"

    results.append(entry)

print("\n=== MIGRATION REPORT ===")
for e in results:
    print(f"{e['label']:35} stored={e['stored_name']!r:55} local={e['local_exists']} "
          f"status={e.get('status')} http={e.get('http_status')} ct={e.get('content_type')} bytes={e.get('bytes')}")
    if e.get('error'):
        print("   ERROR:", e['error'])
    if e.get('rendered_url'):
        print("   URL  :", e['rendered_url'])

all_ok = all(e.get("status") == "OK" and e.get("http_status") == 200 for e in results)
print("\nALL IMAGES RESTORED AND VERIFIED:", all_ok)
sys.exit(0 if all_ok else 1)
