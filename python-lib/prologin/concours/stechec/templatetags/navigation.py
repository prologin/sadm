import urllib.parse
from django import template
from django.http import QueryDict
register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, url):
    request = context['request']
    path = urllib.parse.urlsplit(request.path)
    url = urllib.parse.urlsplit(url)
    if path.path == url.path:
        return 'active'
    return ''


@register.simple_tag
def querystring(request=None, **kwargs):
    if request is None:
        qs = QueryDict()
    else:
        qs = request.GET.copy()
    # Can't use update() here as it would just append to the querystring
    for k, v in kwargs.items():
        qs[k] = v
    return qs.urlencode()
