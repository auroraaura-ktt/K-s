"""Temporary helper: render the real Project Details page to static HTML.

Used only to verify the Project Details CSS in a real browser. Not part of
the application.
"""
import os

import django
from django.test.runner import DiscoverRunner
from django.test.utils import setup_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tmp_test_settings")
django.setup()

setup_test_environment()
runner = DiscoverRunner(verbosity=0, interactive=False)
old_config = runner.setup_databases()

from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402
from mytask.models import Project, ProjectImage  # noqa: E402

PHOTOS = [
    "projects/Screenshot_2026-09-27_225350.png",
    "projects/Screenshot_2026-09-27_225350_ULDHfQm.png",
]

LONG_DESCRIPTION = (
    "Care Connect is a digital health record management system that links "
    "patients, doctors and administrators in one place. Patients register "
    "online, book appointments with available doctors and keep track of "
    "their own visit history. Doctors open their assigned patient list, "
    "update medical histories and add consultation notes without touching "
    "a single sheet of paper. Administrators manage staff, clinics and "
    "reports, and every stakeholder gets a dashboard that only shows what "
    "they are allowed to see. The platform was built to remove the "
    "duplicate paperwork that slows clinics down, so a receptionist can "
    "admit a patient in seconds and a doctor can read the same record "
    "immediately afterwards.\n\n"
    "The system stores records behind role based permissions, keeps a full "
    "audit trail for every change, and exposes a reporting layer that "
    "clinic managers use to plan staffing. Deployment notes and the "
    "installer live at "
    "https://internal.example.com/deployments/care-connect/release-notes-2026-09?channel=stable "
    "and the demo environment is rebuilt on every merge to main."
)

NAV_DESCRIPTION = "A companion booking portal for the same clinic network."

cares = Project.objects.create(
    title="Care Connect - Digital Health Record Management Platform",
    description=LONG_DESCRIPTION,
    photo=PHOTOS[0],
    url="https://care-connect.example.com/demo?ref=portfolio",
    github_url="https://github.com/example/care-connect",
    role="Full Stack Developer",
    client="Sunrise Medical Group",
    status="Completed",
    is_featured=True,
    technologies="Python\nDjango\nPostgreSQL\nRedis\nDocker\nVanilla JavaScript",
    features=(
        "Online patient registration and appointment booking\n"
        "Doctor dashboards with assigned patient lists\n"
        "Digital medical history with a full audit trail\n"
        "Administrator reporting for staffing decisions"
    ),
    responsibilities=(
        "Owned the data model and the permissions layer\n"
        "Built the appointment scheduling engine\n"
        "Wrote the reporting endpoints and the deployment pipeline"
    ),
    additional_info=(
        "Built over eight weeks with a two-person team.\n"
        "Reference material: https://example.com/docs/really-long-unbroken-reference-link/care-connect"
    ),
)
for index, photo in enumerate(PHOTOS[1:], start=1):
    ProjectImage.objects.create(project=cares, image=photo, order=index)

Project.objects.create(
    title="Clinic Booking Portal",
    description=NAV_DESCRIPTION,
    url="https://booking.example.com",
    github_url="https://github.com/example/booking",
)

hostile = Project.objects.create(
    title="Supercalifragilisticexpialidocious" * 3,
    description=(
        "A stress project used to verify that unbroken content cannot "
        "widen the page. " + "A" * 120 + " "
        "https://example.com/" + "b" * 120 + " "
        "More ordinary sentences follow so the paragraph still wraps "
        "like normal prose in every browser."
    ),
    url="https://stress.example.com/very/deep/path?query=" + "c" * 80,
    github_url="https://github.com/example/stress",
    role="Principal Developer And Accessibility Reviewer Extraordinaire",
    client="Incredibly Long Client Name Holdings International Limited",
)
ProjectImage.objects.create(project=hostile, image=PHOTOS[1], order=1)

User.objects.create_user("owner", password="secret123")

client = Client(SERVER_NAME="localhost")


def snapshot(url, path, login=False):
    if login:
        client.login(username="owner", password="secret123")
    html = client.get(url).content.decode()
    html = html.replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
    html = html.replace('src="/media/', 'src="media/').replace('href="/media/', 'href="media/')
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(html)
    print("wrote", path, len(html), "bytes")


snapshot(f"/project/{cares.id}/", "tmp_pd_render.html")
snapshot(f"/project/{hostile.id}/", "tmp_pd_render_hostile.html")
snapshot(f"/project/{cares.id}/", "tmp_pd_render_auth.html", login=True)

runner.teardown_databases(old_config)
