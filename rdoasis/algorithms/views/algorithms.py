from django.utils.encoding import smart_str
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import renderers
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin
from rgd.serializers import ChecksumFileSerializer

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, DockerImage

from .serializers import (
    AlgorithmSerializer,
    AlgorithmTaskSerializer,
    DockerImageSerializer,
    LimitOffsetSerializer,
)


class PlainTextRenderer(renderers.BaseRenderer):
    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, media_type=None, renderer_context=None):
        return smart_str(data, encoding=self.charset)


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
        """Run the algorithm, returning the task."""
        alg: Algorithm = get_object_or_404(Algorithm, pk=pk)
        algorithm_task = alg.run()

        return Response(AlgorithmTaskSerializer(algorithm_task).data)

    @swagger_auto_schema(
        query_serializer=LimitOffsetSerializer(), responses={200: ChecksumFileSerializer(many=True)}
    )
    @action(detail=True, methods=['GET'])
    def input(self, request, pk: str):
        """Return the input dataset as a list of files."""
        alg: Algorithm = get_object_or_404(Algorithm, pk=pk)
        queryset = alg.input_dataset.all()

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ChecksumFileSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ChecksumFileSerializer(queryset, many=True)
        return Response(serializer.data)


class AlgorithmTaskViewSet(NestedViewSetMixin, ReadOnlyModelViewSet):
    serializer_class = AlgorithmTaskSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        """Override get_queryset to return steps from this workflow, in order."""
        algorithm_pk = self.request.parser_context['kwargs']['parent_lookup_algorithm__pk']
        return AlgorithmTask.objects.filter(algorithm__pk=algorithm_pk)

    @swagger_auto_schema(responses={200: 'The log text.'})
    @action(detail=True, methods=['GET'], renderer_classes=[PlainTextRenderer])
    def logs(self, request, parent_lookup_algorithm__pk: str, pk: str):
        """Return the task logs."""
        task: AlgorithmTask = get_object_or_404(
            AlgorithmTask, algorithm__pk=parent_lookup_algorithm__pk, pk=pk
        )

        return Response(task.output_log, content_type='text/plain')

    @swagger_auto_schema(
        query_serializer=LimitOffsetSerializer(), responses={200: ChecksumFileSerializer(many=True)}
    )
    @action(detail=True, methods=['GET'])
    def files(self, request, parent_lookup_algorithm__pk: str, pk: str):
        """Return the task output dataset as a list of files."""
        task: AlgorithmTask = get_object_or_404(
            AlgorithmTask, algorithm__pk=parent_lookup_algorithm__pk, pk=pk
        )
        queryset = task.output_dataset.all()

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ChecksumFileSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ChecksumFileSerializer(queryset, many=True)
        return Response(serializer.data)
