import re
from html import escape

from django import template
from django.utils.safestring import mark_safe

from mytask.models import sanitize_external_url

register = template.Library()

_HEADING = re.compile(r"^(#{1,3})\s+(.+)$")
_UNORDERED_ITEM = re.compile(r"^\s*[-*+]\s+(.+)$")
_ORDERED_ITEM = re.compile(r"^\s*\d+[.)]\s+(.+)$")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline_format(text):
    output = []
    position = 0
    for match in _LINK.finditer(text):
        output.append(escape(text[position:match.start()]))
        label = escape(match.group(1))
        url = sanitize_external_url(match.group(2).strip())
        if url:
            output.append(
                f'<a href="{escape(url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer">{label}</a>'
            )
        else:
            output.append(label)
        position = match.end()
    output.append(escape(text[position:]))
    return "".join(output)


@register.filter
def format_app_description(value):
    """Render a small, safe Markdown-like subset for plain-text descriptions."""
    if not value:
        return ""

    rendered = []
    paragraph = []
    list_type = None

    def flush_paragraph():
        if paragraph:
            rendered.append("<p>" + "<br>".join(_inline_format(line) for line in paragraph) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal list_type
        if list_type:
            rendered.append(f"</{list_type}>")
            list_type = None

    for raw_line in str(value).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            close_list()
            continue

        heading = _HEADING.match(line)
        unordered = _UNORDERED_ITEM.match(line)
        ordered = _ORDERED_ITEM.match(line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            rendered.append(f"<h{level + 1}>{_inline_format(heading.group(2))}</h{level + 1}>")
        elif unordered or ordered:
            flush_paragraph()
            target_list = "ul" if unordered else "ol"
            if list_type != target_list:
                close_list()
                rendered.append(f"<{target_list}>")
                list_type = target_list
            item = (unordered or ordered).group(1)
            rendered.append(f"<li>{_inline_format(item)}</li>")
        else:
            close_list()
            paragraph.append(line)

    flush_paragraph()
    close_list()
    return mark_safe("\n".join(rendered))
