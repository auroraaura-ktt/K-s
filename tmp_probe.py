import os
import re

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myblog.settings")
django.setup()

from django.test import Client  # noqa: E402

client = Client(SERVER_NAME="localhost")
response = client.get("/project/2/")
html = response.content.decode()

print("status:", response.status_code, "| html len:", len(html))

probes = [
    "project-details-card",
    "project-details-content",
    "project-media-column",
    "project-media-viewer",
    "project-details-panel",
    "project-summary",
    "project-metadata",
    "project-back",
    "About This Project",
    "project-description",
    "ab-lightbox",
    "ab-thumbnail",
    "ab-slide",
    "data-ab-slide",
]
for probe in probes:
    print(("OK  " if probe in html else "MISS"), probe)

match = re.search(r'project-description">(.*?)</div>', html, re.S)
print("paragraph <p> rendered:", match.group(1).count("<p>") if match else 0)

# Full text of the description must still be present (nothing truncated away).
from mytask.models import Project  # noqa: E402

project = Project.objects.first()
flat = re.sub(r"<[^>]+>", " ", match.group(1)) if match else ""
flat = re.sub(r"\s+", " ", flat).strip()
print("desc chars rendered:", len(flat))
print("full description preserved:", len(flat) > 1800)
