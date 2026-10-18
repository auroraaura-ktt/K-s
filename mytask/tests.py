import json
import os
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from io import BytesIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from .forms import AlbumAdminForm
from .models import Album, Project, ProjectImage

BASE_DIR = Path(__file__).resolve().parent.parent


class ProjectDetailPageTests(TestCase):
    """Regression tests for the Project Details page.

    Two defects motivated these tests:
      1. The inline slideshow script re-triggered its own MutationObserver,
         freezing the page (infinite loop).
      2. @login_required redirected to Django's default /accounts/login/,
         which is not routed here, so sign-in attempts 404'd.
    """

    def setUp(self):
        self.project = Project.objects.create(
            title="Care Connect",
            description="A healthcare project.",
        )
        self.url = f"/project/{self.project.id}/"

    def test_authorized_user_can_open_project_details(self):
        """An authenticated user clicking through from the list gets the page."""
        User.objects.create_user("owner", password="secret123")
        self.client.login(username="owner", password="secret123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Care Connect")
        self.assertTemplateUsed(response, "project_detail.html")

    def test_anonymous_visitor_can_open_project_details(self):
        """The portfolio is public: anonymous users are not blocked."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Care Connect")

    def test_direct_navigation_and_refresh_works(self):
        """Direct hit / refresh on the detail URL renders the project."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["project"].id, self.project.id)

    def test_five_project_photos_render_four_thumbnails_and_gallery(self):
        """Large galleries show a four-item strip and expose all images in lightbox."""
        self.project.photo = "projects/cover.png"
        self.project.save(update_fields=["photo"])
        for index in range(1, 5):
            ProjectImage.objects.create(
                project=self.project,
                image=f"projects/image-{index}.png",
                order=index,
            )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count('data-ab-slide="'), 5)
        self.assertEqual(response.content.decode().count('data-ab-thumb="'), 4)
        self.assertContains(response, "+ 1 more")
        self.assertContains(response, "data-ab-lightbox")

    def test_description_is_rendered_in_readable_paragraphs_without_losing_text(self):
        """The long description reads as paragraphs and nothing is dropped.

        The lead summary and the body may overlap in the source text, so the
        two rendered together must still reproduce the description exactly.
        """
        description = (
            "Care Connect is a digital health record management system. "
            "It ensures smooth interaction among three key stakeholders: "
            "patients, doctors, and administrators. Each role is equipped with "
            "functionalities that cater to its specific needs, ensuring that the "
            "system is both efficient and practical. For patients, the system "
            "provides a convenient way to engage with healthcare services. "
            "They can register online, book appointments with available doctors, "
            "and explore doctor profiles to make informed choices about their care. "
            "Additionally, patients can share reviews and feedback about the clinic, "
            "helping to build trust and improve service quality. For doctors, the "
            "system replaces the burdens of paperwork with digital record management. "
            "They can access their assigned patient lists, update medical histories, "
            "and add notes after each consultation. "
            "Administrators can manage doctors, patients, and clinic settings, "
            "and reports are generated for every stakeholder."
        )
        self.project.description = description
        self.project.save(update_fields=["description"])

        paragraphs = self.project.description_paragraphs
        self.assertGreater(len(paragraphs), 1, "long description should split into paragraphs")
        self.assertEqual(" ".join(paragraphs), description)

        body = " ".join(self.project.description_body_paragraphs)
        combined = f"{self.project.summary} {body}".strip()
        self.assertEqual(combined, description)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "project-description")
        self.assertGreaterEqual(response.content.decode().count("<p>"), 2)

    def test_short_description_is_not_split_or_duplicated(self):
        """A one-sentence description shows once, with no empty body section."""
        self.project.description = "A small utility app."
        self.project.save(update_fields=["description"])

        self.assertEqual(self.project.description_paragraphs, ["A small utility app."])
        self.assertEqual(self.project.summary, "A small utility app.")
        self.assertEqual(
            self.project.description_body_paragraphs, ["A small utility app."]
        )

    def test_nonexistent_project_id_returns_404(self):
        """An invalid project ID gives a clean not-found state, not a crash."""
        response = self.client.get("/project/999999/")

        self.assertEqual(response.status_code, 404)

    def test_live_demo_button_links_directly_to_the_stored_url(self):
        """A valid live URL becomes a direct external Live Demo anchor."""
        self.project.url = "https://shop.example.com/checkout?ref=1"
        self.project.github_url = "https://github.com/example/shop"
        self.project.save(update_fields=["url", "github_url"])

        response = self.client.get(self.url)
        html = response.content.decode()

        # The exact stored URL, unmodified, as a normal external link.
        self.assertIn('href="https://shop.example.com/checkout?ref=1"', html)
        self.assertIn('href="https://github.com/example/shop"', html)
        # Opened directly in a new tab, with an isolated browsing context.
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        # Not routed through the project page or any internal preview URL.
        self.assertNotIn(f'href="{self.url}"', html)

    def test_live_demo_uses_each_projects_own_url(self):
        """No URL is hardcoded or shared between projects."""
        other = Project.objects.create(
            title="Portfolio Website",
            description="Another project.",
            url="https://portfolio.example.com",
            github_url="https://github.com/example/portfolio",
        )
        self.project.url = "https://shop.example.com"
        self.project.save(update_fields=["url"])

        first = self.client.get(self.url).content.decode()
        second = self.client.get(f"/project/{other.id}/").content.decode()

        self.assertIn('href="https://shop.example.com"', first)
        self.assertNotIn('href="https://portfolio.example.com"', first)

        self.assertIn('href="https://portfolio.example.com"', second)
        self.assertNotIn('href="https://shop.example.com"', second)

    def test_live_demo_button_is_hidden_without_a_valid_url(self):
        """Missing, malformed, private and placeholder values render no button."""
        for bad_url in [
            "",
            "not-a-url",
            "javascript:alert(1)",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://192.168.1.10",
        ]:
            with self.subTest(url=bad_url):
                Project.objects.filter(pk=self.project.pk).update(url=bad_url)

                html = self.client.get(self.url).content.decode()

                # No Live Demo action is rendered at all.
                self.assertNotIn("pd-btn-primary", html)
                self.assertNotIn("Live Demo", html)
                # And no URL is invented to stand in for the missing one.
                self.assertNotIn('href="https://example.com"', html)

    def test_justification_is_scoped_to_body_paragraphs(self):
        """Only paragraph copy is justified; UI elements are not.

        The rule must target paragraph selectors inside the right-hand
        panel, never the panel itself, so titles, headings, metadata and
        buttons keep their normal alignment.
        """
        css = (BASE_DIR / "static" / "css" / "design.css").read_text(encoding="utf-8")

        self.assertIn(".pd-prose p {", css.replace("\n", " ").replace("  ", " "))
        self.assertIn("text-align: justify", css)

        # The panel itself must not be justified.
        panel_rule = re.search(
            r"\.project-details-info\s*\{[^}]*\}", css, re.DOTALL
        )
        self.assertIsNotNone(panel_rule)
        self.assertNotIn("text-align: justify", panel_rule.group(0))

        # No global justification was introduced.
        self.assertNotRegex(css, r"(?m)^\s*body\s*\{[^}]*text-align:\s*justify")

    def test_project_list_links_to_the_correct_project_id(self):
        """The list page must pass the real project id in the URL."""
        Project.objects.create(title="Second Project", description="Another one.")

        response = self.client.get("/projects/")

        self.assertEqual(response.status_code, 200)
        for project in Project.objects.all():
            self.assertContains(response, f"/project/{project.id}/")

    def test_authorization_is_preserved_on_admin_pages(self):
        """Anonymous users are still redirected to the real login page."""
        response = self.client.get(f"/myadmin/projects/{self.project.id}/edit/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/myadmin/login/", response["Location"])

    def test_login_redirect_resolves_to_a_real_page(self):
        """Following the redirect must land on a working login page (200)."""
        response = self.client.get(
            f"/myadmin/projects/{self.project.id}/edit/", follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Login")

    def test_authorized_admin_can_reach_project_edit(self):
        """A signed-in user with permission gets the edit form, not a redirect."""
        User.objects.create_user("editor", password="secret123")
        self.client.login(username="editor", password="secret123")

        response = self.client.get(f"/myadmin/projects/{self.project.id}/edit/")

        self.assertEqual(response.status_code, 200)

    def test_detail_page_has_no_infinite_mutation_observer_loop(self):
        """Guard against re-introducing the observer feedback loop.

        The page's inline script is executed in a real DOM. A runaway
        MutationObserver (the original freeze) blows past the allowed
        callback budget and fails this test. Skipped when Node/jsdom
        are unavailable.
        """
        if not self._js_tooling_available():
            self.skipTest("node + jsdom not available")

        response = self.client.get(self.url)
        scripts = re.findall(r"<script>([\s\S]*?)</script>", response.content.decode())
        if not scripts:
            self.skipTest("no inline script rendered on the page")

        result = subprocess.run(
            ["node", os.path.join("tests_js", "mutation_loop_check.js")],
            cwd=BASE_DIR,
            input=json.dumps({"code": "\n".join(scripts)}),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @staticmethod
    def _js_tooling_available():
        return bool(shutil.which("node")) and os.path.isdir(
            os.path.join(BASE_DIR, "node_modules", "jsdom")
        )


class ProjectDetailCssTests(SimpleTestCase):
    """Structural guards for the Project Details stylesheet.

    Three cross-browser defects motivated these tests:
      1. An unclosed rule (.pd-meta-item dd) made the parser swallow the
         very next rule, so .pd-actions - the Live Demo / GitHub row - did
         not exist in any browser.
      2. The base layout rules sat *after* the responsive media queries, so
         the tablet and mobile overrides were dead and phones rendered the
         desktop two-column grid (horizontal overflow).
      3. The lightbox used 100vw / 100dvh with a 95vw image, which could
         push the page wider than the viewport.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.css = (BASE_DIR / "static" / "css" / "design.css").read_text(encoding="utf-8")
        cls.region = cls.css[cls.css.index(".project-details-section {") :]

    def _rule(self, selector, css=None):
        """Return the body of the first flush-left rule for ``selector``."""
        match = re.search(
            rf"(?m)^{re.escape(selector)}\s*\{{([^}}]*)\}}",
            css if css is not None else self.region,
            re.DOTALL,
        )
        self.assertIsNotNone(match, f"{selector} rule is missing or unclosed")
        return match.group(1)

    def _media_block(self, condition):
        """Return the body of a media query by brace matching."""
        start = self.region.index(f"@media {condition}")
        depth = 0
        for index in range(start, len(self.region)):
            char = self.region[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return self.region[start:index]
        self.fail(f"unbalanced braces in @media {condition}")

    def _override_rule(self, selector, block):
        """Return an indented rule body from inside a media query."""
        match = re.search(
            rf"(?m)^\s+{re.escape(selector)}\s*\{{([^}}]*)\}}", block, re.DOTALL
        )
        self.assertIsNotNone(match, f"{selector} override is missing or unclosed")
        return match.group(1)

    def test_braces_are_balanced_and_no_declarations_sit_outside_a_rule(self):
        """Every block is closed and no declaration is orphaned at top level."""
        stripped = re.sub(r"/\*.*?\*/", "", self.css, flags=re.DOTALL)

        self.assertEqual(stripped.count("{"), stripped.count("}"))

        depth = 0
        stray = []
        for line in stripped.splitlines():
            content = line.strip()
            if content.endswith("{"):
                depth += 1
            elif content == "}":
                depth -= 1
            elif depth == 0 and re.match(r"^[a-z-]+\s*:\s*[^;]+;$", content):
                stray.append(content)
        self.assertEqual(stray, [], f"declarations outside any rule: {stray}")

    def test_base_rules_are_declared_before_the_responsive_overrides(self):
        """Base layout rules must come first, or the media queries are dead."""
        mobile = self.region.index("@media (max-width: 767px)")

        for selector in [
            ".project-details-content",
            ".project-details-card",
            ".project-details-inner",
            ".project-media-viewer",
        ]:
            body = self._rule(selector)
            self.assertTrue(body.strip(), f"{selector} base rule is empty")
            base_position = self.region.index(f"{selector} {{")
            self.assertLess(
                base_position,
                mobile,
                f"{selector} base rule must precede the mobile media query",
            )

    def test_action_row_is_a_wrapping_flex_row(self):
        """The Live Demo / GitHub row must exist and wrap, never overflow."""
        actions = self._rule(".pd-actions")

        self.assertIn("display: flex", actions)
        self.assertIn("flex-wrap: wrap", actions)
        self.assertIn("gap:", actions)

    def test_buttons_have_a_stable_box_and_visible_focus_state(self):
        """Anchors styled as buttons keep one predictable size everywhere."""
        button = self._rule(".pd-btn")

        for declaration in [
            "display: inline-flex",
            "align-items: center",
            "justify-content: center",
            "padding:",
            "line-height:",
        ]:
            self.assertIn(declaration, button)
        self.assertIn(".pd-btn:focus-visible", self.region)

    def test_layout_children_can_shrink(self):
        """Grid and flex children may shrink, so text never widens a column."""
        grid = self._rule(".project-details-content")

        self.assertIn("min-width: 0", grid)
        self.assertIn("minmax(0, 1.15fr)", grid)
        self.assertIn("min-height: 560px", grid)
        self.assertNotIn("min-height: 0", grid)

        for selector in [
            ".project-details-info",
            ".project-details-inner",
            ".project-media-panel",
            ".project-media",
        ]:
            self.assertIn("min-width: 0", self._rule(selector))

    def test_mobile_stacks_to_one_column_and_scrolls_naturally(self):
        """Phones get a single column with page scroll, not the desktop grid."""
        mobile = self._media_block("(max-width: 767px)")
        content = self._override_rule(".project-details-content", mobile)

        self.assertIn("display: flex", content)
        self.assertIn("flex-direction: column", content)
        self.assertNotIn("grid-template-columns", content)
        # Scrolling goes back to the page instead of a nested scroll area.
        self.assertIn("overflow: visible", mobile)
        self.assertIn("height: auto", mobile)

    def test_tablet_keeps_the_two_column_layout(self):
        """Tablets still get both panels side by side, sized to fit."""
        tablet = self._media_block("(max-width: 1023px)")
        content = self._override_rule(".project-details-content", tablet)

        self.assertIn("grid-template-columns", content)
        self.assertIn("minmax(320px, 0.95fr)", content)

    def test_no_viewport_width_units_or_unnecessary_important(self):
        """100vw overflows once a scrollbar is present; !important is unneeded."""
        declarations_only = re.sub(r"/\*.*?\*/", "", self.region, flags=re.DOTALL)
        self.assertNotIn("100vw", declarations_only)

        declarations = [
            line.strip()
            for line in self.region.splitlines()
            if "!important" in line and not line.strip().startswith("/*")
        ]
        self.assertEqual(len(declarations), 3, declarations)
        self.assertTrue(
            all(
                line.startswith(
                    ("animation-duration", "transition-duration", "scroll-behavior")
                )
                for line in declarations
            ),
            declarations,
        )

    def test_body_copy_stays_justified_on_every_screen(self):
        """Justification applies to the summary and every body paragraph."""
        justify_block = re.search(
            r"\.pd-summary,\s*\.pd-prose p\s*\{[^}]*text-align:\s*justify[^}]*\}",
            self.region,
            re.DOTALL,
        )

        self.assertIsNotNone(justify_block)
        # No rule may switch a body paragraph back to a different alignment.
        self.assertNotIn("text-align: left", self.region)


class AlbumAdminTests(TestCase):
    def test_admin_form_can_create_album_with_photo(self):
        with TemporaryDirectory() as media_dir:
            storages = {
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": media_dir},
                },
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
                },
            }
            with override_settings(MEDIA_ROOT=media_dir, STORAGES=storages):
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
