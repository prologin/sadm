from rest_framework import filters


class IsOwnerFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects if the ?mine
    query param is set.
    """
    field = 'author'
    query_param = 'mine'

    def filter_queryset(self, request, queryset, view):
        if request.QUERY_PARAMS.get('mine') is not None:
            return queryset.filter(**{self.field: request.user})
        return queryset


def IsOwnerUsing(field='author', query_param='mine'):  # noqa
    """
    Exmample usage:
        filter_backends = [IsOwnerUsing('owner', 'my_objects')]
    """
    return type('IsOwnerUsing%s' % field.capitalize(),
                (IsOwnerFilterBackend,),
                {'field': field, 'query_param': query_param})
