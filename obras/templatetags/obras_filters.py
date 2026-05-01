import re
from django import template
from django.conf import settings

register = template.Library()


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
