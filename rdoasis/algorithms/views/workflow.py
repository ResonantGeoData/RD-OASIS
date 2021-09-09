from rest_framework import serializers
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.viewsets import ModelViewSet

from rdoasis.algorithms.models import Workflow


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = '__all__'
        read_only_fields = ['collection']


class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.all().select_related('collection')
    serializer_class = WorkflowSerializer
    pagination_class = LimitOffsetPagination
    http_method_names = ['get', 'head', 'post', 'put', 'delete']
