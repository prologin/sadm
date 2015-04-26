from rest_framework import permissions, throttling


class CreateMatchUserThrottle(throttling.UserRateThrottle):
    rate = '4/min'


class IsOwnerOrReadOnly(permissions.IsAuthenticated):
    """
    Object-level permission to only allow staff or owners of an object to edit it.
    Allow read-only access for everybody (authenticated).
    """
    field = 'author'

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_staff:
            return True

        # Instance must have an attribute named self.field
        return getattr(obj, self.field) == request.user


def IsOwnerUsing(field):  # noqa
    """
    Exmample usage:
        permission_classes = [IsOwnerUsing('owner')]
    """
    return type('IsOwnerUsing%s' % field.capitalize(), (IsOwnerOrReadOnly,), {'field': field})
