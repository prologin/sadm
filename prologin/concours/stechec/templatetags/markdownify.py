import markdown2
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def markdownify(content, **options):
    html = markdown2.markdown(content)
    return mark_safe(html)
