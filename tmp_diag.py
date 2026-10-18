import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env.development.local")

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myblog.settings')
django.setup()

from django.conf import settings
from mytask.models import Album, AlbumImage, Profile, Project, Education, Application

print("=== SETTINGS ===")
print("DEBUG:", settings.DEBUG)
print("USE_CLOUDINARY:", getattr(settings, '_USE_CLOUDINARY', 'N/A'))
print("MEDIA_URL:", settings.MEDIA_URL)
print("MEDIA_ROOT:", settings.MEDIA_ROOT)
print("STORAGES default BACKEND:", settings.STORAGES['default']['BACKEND'])
print("ALLOWED_HOSTS:", settings.ALLOWED_HOSTS)

print("\n=== LOCAL MEDIA FILES ===")
media_root = settings.MEDIA_ROOT
local_files = []
if media_root.exists():
    for f in sorted(media_root.rglob('*')):
        if f.is_file():
            rel = f.relative_to(media_root).as_posix()
            local_files.append(rel)
            print("  LOCAL:", rel)
else:
    print("  (media root does not exist)")
local_set = set(local_files)

print("\n=== DB RECORDS ===")
db_references = []  # (model, pk, field, name)

def check(name, label):
    if name:
        db_references.append((label, name))
        exists_local = name in local_set
        print(f"  [{label}] {name}  local_exists={exists_local}")

for a in Album.objects.all().order_by('id'):
    print(f"\nAlbum id={a.id} name={a.album_name!r} date_created={a.date_created}")
    check(a.album_photo.name if a.album_photo else None, f"Album.{a.id}.album_photo")
    for img in a.images.all().order_by('order', 'id'):
        check(img.image.name if img.image else None, f"AlbumImage.{img.id}.image (album {a.id})")

for p in Profile.objects.all().order_by('id'):
    print(f"\nProfile id={p.id} name={p.name!r}")
    check(p.photo.name if p.photo else None, f"Profile.{p.id}.photo")

for pr in Project.objects.all().order_by('id'):
    print(f"\nProject id={pr.id} title={pr.title!r}")
    # look for image fields
    for f in pr._meta.fields:
        if f.name in ('image', 'thumbnail', 'cover', 'photo'):
            val = getattr(pr, f.name)
            check(val.name if val else None, f"Project.{pr.id}.{f.name}")

for e in Education.objects.all().order_by('id'):
    print(f"\nEducation id={e.id} degree={e.degree!r}")
    check(e.certificate.name if e.certificate else None, f"Education.{e.id}.certificate")

for app in Application.objects.all().order_by('id'):
    print(f"\nApplication id={app.id}")
    check(app.file.name if app.file else None, f"Application.{app.id}.file")

print("\n=== SUMMARY ===")
print(f"Total DB file references: {len(db_references)}")
missing_local = [r for r in db_references if not r[1] or r[1] not in local_set]
print(f"References NOT found locally: {len(missing_local)}")
for label, name in missing_local:
    print(f"  MISSING-LOCAL: {label} -> {name!r}")

print("\n=== CLOUDINARY CHECK ===")
import cloudinary, cloudinary.api
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True,
)
# Get all resources (paginate)
cloud_public_ids = set()
cursor = None
while True:
    kwargs = dict(type='upload', resource_type='image', max_results=500)
    if cursor:
        kwargs['next_cursor'] = cursor
    res = cloudinary.api.resources(**kwargs)
    for r in res.get('resources', []):
        cloud_public_ids.add(r['public_id'])
    cursor = res.get('next_cursor')
    if not cursor:
        break
print(f"Cloudinary image resources total: {len(cloud_public_ids)}")

for label, name in db_references:
    if not name:
        continue
    in_cloud = name in cloud_public_ids
    print(f"  {'IN_CLOUD' if in_cloud else 'NOT_IN_CLOUD':12} {label} -> {name!r}")
