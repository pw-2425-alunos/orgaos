import re
from django import template

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
