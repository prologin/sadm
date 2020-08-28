from rest_framework import serializers, viewsets, routers, permissions
import django_filters.rest_framework
from . import models

class MachineTheiaSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.MachineTheia
        fields = ['id', 'url', 'host', 'room', 'port']

# router
class MachineTheiaViewSet(viewsets.ModelViewSet):
    queryset = models.MachineTheia.objects.all()
    serializer_class = MachineTheiaSerializer
    permission_classes = [permissions.DjangoModelPermissions]
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = ['host', 'room', 'port']

router = routers.DefaultRouter()
router.register(r'machinetheia', MachineTheiaViewSet)
