import os, sys, json, requests
from dotenv import load_dotenv
from pathlib import Path
import django, cloudinary, cloudinary.uploader
from django.conf import settings
from django.core.files.storage import storages

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env.development.local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myblog.settings")
django.setup()
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True,
)

storage = storages["default"]
TO_RESTORE = [
    ("Album.id=1.album_photo",  "album_photos/FB_IMG_1705506267265.jpg"),
    ("Album.id=2.album_photo",  "album_photos/canva-meme-cat-heart-cute-shy-embarrassed-CVBohzyf-nk.jpg"),
    ("Album.id=3.album_photo",  "album_photos/pexels-photo-341970_ZBHXSXQ.webp"),
    ("Project.id=2.photo",      "projects/Screenshot_2026-10-08_135640.png"),
]
results = []
all_ok = True
for label, stored_name in TO_RESTORE:
    e = {"label": label, "stored_name": stored_name}
    try:
        e["exists"] = storage.exists(stored_name)
    except Exception as ex:
        e["exists"] = f"ERROR {ex!r}"
    e["url"] = storage.url(stored_name)
    try:
        r = requests.get(e["url"], timeout=25)
        e["http_status"] = r.status_code
        e["content_type"] = r.headers.get("content-type")
        e["bytes"] = len(r.content)
        e["ok"] = r.status_code == 200
        if r.status_code != 200:
            all_ok = False
    except Exception as ex:
        e["http_status"] = None
        e["error"] = repr(ex)
        e["ok"] = False
        all_ok = False
    results.append(e)

out = {"all_ok": all_ok, "results": results}
Path("tmp_verify_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2))
sys.exit(0 if all_ok else 1)
