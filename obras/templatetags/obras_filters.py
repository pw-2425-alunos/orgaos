import re
from django import template
from django.conf import settings
from django.utils.html import escape, format_html, urlize
from django.utils.safestring import mark_safe

register = template.Library()

ANCHOR_TAG_RE = re.compile(
    r'^\s*<a\s+[^>]*href\s*=\s*(["\'])(?P<href>.*?)\1[^>]*>(?P<label>.*?)</a>\s*$',
    re.IGNORECASE | re.DOTALL,
)


@register.filter
def eq(value, arg):
    return str(value) == str(arg)


@register.filter
def format_orgaos(value):
    """
    Transforms values like '6org' to '6 órgãos'
    Examples:
    - '6org' -> '6 órgãos'
    - '5 org' -> '5 órgãos'
    - '2' -> '2' (unchanged)
    - '' -> '' (unchanged for default filter to handle)
    """
    if not value:
        return value
    
    # Pattern: number followed by optional whitespace and 'org' (case-insensitive)
    match = re.match(r'^(\d+)\s*org$', str(value).strip(), re.IGNORECASE)
    if match:
        num = match.group(1)
        return f"{num} órgãos"
    
    return value


@register.filter
def normalize_catalog_media_urls(value, request=None):
    """
    Rewrites legacy absolute /media/ links saved in catalog HTML to the current MEDIA_URL.
    This keeps old imported content working when the app is mounted under a URL prefix (e.g. /web).
    """
    if not value:
        return value

    html = str(value)
    media_url = getattr(settings, "MEDIA_URL", "/media/") or "/media/"
    media_url = media_url if media_url.endswith("/") else f"{media_url}/"

    # If Django is mounted under a prefix (e.g. /web) and MEDIA_URL is still /media/,
    # infer the prefix from request.path vs request.path_info.
    if request is not None:
        request_path = getattr(request, "path", "") or ""
        path_info = getattr(request, "path_info", "") or ""
        script_prefix = ""

        if path_info and request_path.endswith(path_info):
            script_prefix = request_path[: len(request_path) - len(path_info)]

        if script_prefix and media_url.startswith("/") and not media_url.startswith(f"{script_prefix}/"):
            media_url = f"{script_prefix}{media_url}"

    if media_url == "/media/":
        return html

    return re.sub(
        r'((?:src|href)\s*=\s*["\'])/media/',
        rf'\1{media_url}',
        html,
        flags=re.IGNORECASE,
    )


@register.filter
def render_referencias(value):
    """
    Renders references safely:
    - If value is a single <a href="...">...</a>, keep it as a clickable link.
    - Otherwise, escape text and auto-link plain URLs.
    """
    if not value:
        return ""

    text = str(value).strip()
    anchor_match = ANCHOR_TAG_RE.match(text)

    if anchor_match:
        href = (anchor_match.group("href") or "").strip()
        if href.startswith(("http://", "https://")):
            raw_label = anchor_match.group("label") or ""
            # Remove nested tags from label to avoid injecting arbitrary HTML.
            label = re.sub(r"<[^>]+>", "", raw_label).strip() or href
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
                href,
                label,
            )

    return autolink_text(text)


@register.filter(needs_autoescape=True)
def autolink_text(value, autoescape=True):
    """
    Escapes plain text and converts URLs into clickable links.
    """
    if not value:
        return ""

    text = escape(str(value)) if autoescape else str(value)
    return mark_safe(urlize(text, nofollow=True, autoescape=autoescape))


@register.filter
def split_referencias(value):
    """
    Splits references text into entries separated by ';'.
    """
    if not value:
        return []

    partes = [parte.strip() for parte in str(value).split(";")]
    return [parte for parte in partes if parte]
