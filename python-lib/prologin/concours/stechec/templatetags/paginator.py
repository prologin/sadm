from django import template

register = template.Library()


@register.inclusion_tag('stechec/paginator.html', takes_context=True)
def paginator(context, adjacent_pages=2):
    """
    To be used in conjunction with the object_list generic view.

    Adds pagination context variables for use in displaying first, adjacent and
    last page links in addition to those created by the object_list generic
    view.

    http://djangosnippets.org/snippets/73/
    """
    page = context['page_obj']
    pagin = context['paginator']
    page_numbers = [
        n
        for n in range(
            page.number - adjacent_pages, page.number + adjacent_pages + 1
        )
        if 0 < n <= pagin.num_pages
    ]
    return {
        'request': context['request'],
        'page': page,
        'paginator': pagin,
        'page_numbers': page_numbers,
        'show_first': 1 not in page_numbers,
        'show_last': pagin.num_pages not in page_numbers,
    }
