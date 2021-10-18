from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, DockerImage

from .serializers import AlgorithmSerializer, AlgorithmTaskSerializer, DockerImageSerializer


class DockerImageViewSet(ModelViewSet):
    queryset = DockerImage.objects.all()
    serializer_class = DockerImageSerializer
    pagination_class = LimitOffsetPagination


class AlgorithmViewSet(ModelViewSet):
    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    pagination_class = LimitOffsetPagination

    @swagger_auto_schema(method='POST', request_body=no_body)
    @action(detail=True, methods=['POST'])
    def run(self, request, pk):
        alg: Algorithm = get_object_or_404(Algorithm, pk=pk)
        algorithm_task = alg.run()

        return Response(AlgorithmTaskSerializer(algorithm_task).data)


class AlgorithmTaskViewSet(NestedViewSetMixin, ReadOnlyModelViewSet):
    serializer_class = AlgorithmTaskSerializer
    pagination_class = LimitOffsetPagination
    lookup_field = 'id'

    def get_queryset(self):
        """Override get_queryset to return steps from this workflow, in order."""
        algorithm_pk = self.request.parser_context['kwargs']['parent_lookup_algorithm__pk']
        return AlgorithmTask.objects.filter(algorithm__pk=algorithm_pk)
