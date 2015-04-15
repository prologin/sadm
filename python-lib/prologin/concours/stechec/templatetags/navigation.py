import urllib.parse
from django import template
register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, url):
    request = context['request']
    path = urllib.parse.urlsplit(request.path)
    url = urllib.parse.urlsplit(url)
    if path.path == url.path:
        return 'active'
    return ''