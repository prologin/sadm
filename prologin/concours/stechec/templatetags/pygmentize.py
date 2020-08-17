import pygments
import pygments.lexers
import pygments.formatters
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def pygmentize(code, language, **options):
    lexer = pygments.lexers.get_lexer_by_name(language)
    formatter = pygments.formatters.HtmlFormatter(
        linenos=False, cssclass="codehilite", **options
    )
    return mark_safe(pygments.highlight(code, lexer, formatter))
