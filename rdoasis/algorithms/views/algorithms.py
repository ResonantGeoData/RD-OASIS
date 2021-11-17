from django.utils.encoding import smart_str
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import renderers
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin
from rgd.serializers import ChecksumFileSerializer

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, Dataset, DockerImage
from rdoasis.algorithms.views.utils import paginate_action

from .serializers import (
    AlgorithmQuerySerializer,
    AlgorithmRunSerializer,
    AlgorithmSerializer,
    AlgorithmTaskLogsSerializer,
    AlgorithmTaskQuerySerializer,
    AlgorithmTaskSerializer,
    DatasetListSerializer,
    DatasetSerializer,
    DockerImageSerializer,
    LimitOffsetSerializer,
)


class PlainTextRenderer(renderers.BaseRenderer):
    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, media_type=None, renderer_context=None):
        return smart_str(data, encoding=self.charset)


class ZipFileRenderer(renderers.BaseRenderer):
    media_type = 'application/zip'
    format = ''

    def render(self, data, media_type=None, renderer_context=None):
        return data


class DockerImageViewSet(ModelViewSet):
    queryset = DockerImage.objects.all()
    serializer_class = DockerImageSerializer
    pagination_class = LimitOffsetPagination


class AlgorithmViewSet(ModelViewSet):
    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return

        queryset = Algorithm.objects.all()
        docker_image__pk = self.request.GET.get('docker_image__pk', None)
        if docker_image__pk is not None:
            queryset = queryset.filter(docker_image__pk=docker_image__pk)

        return queryset

    @swagger_auto_schema(query_serializer=AlgorithmQuerySerializer())
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @swagger_auto_schema(method='POST', request_body=AlgorithmRunSerializer())
    @action(detail=True, methods=['POST'])
    def run(self, request, pk):
        """Run the algorithm, returning the task."""
        serializer = AlgorithmRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        alg: Algorithm = get_object_or_404(Algorithm, pk=pk)
        algorithm_task = alg.run(serializer.validated_data['input_dataset'])

        return Response(AlgorithmTaskSerializer(algorithm_task).data)

    @swagger_auto_schema(query_serializer=LimitOffsetSerializer())
    @action(detail=True, methods=['GET'])
    @paginate_action(AlgorithmTaskSerializer)
    def tasks(self, request, pk):
        return AlgorithmTask.objects.filter(algorithm__pk=pk)


class DatasetViewSet(ModelViewSet):
    serializer_class = DatasetSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return

        queryset = Dataset.objects.all()
        include_output_datasets = self.request.GET.get('include_output_datasets', 'false') == 'true'
        if not include_output_datasets:
            queryset = queryset.filter(output_tasks=None)

        return queryset

    @swagger_auto_schema(
        query_serializer=DatasetListSerializer(), responses={200: DatasetSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        query_serializer=LimitOffsetSerializer(), responses={200: ChecksumFileSerializer(many=True)}
    )
    @action(detail=True, methods=['GET'])
    @paginate_action(ChecksumFileSerializer)
    def files(self, request, pk: str):
        """Return the task output dataset as a list of files."""
        dataset: Dataset = get_object_or_404(Dataset.objects.prefetch_related('files'), pk=pk)
        queryset = dataset.files.all()

        return queryset

    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                'The Dataset Zip File', schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            '404': 'Not Found',
        },
        produces='application/octet-stream',
    )
    @action(
        detail=True,
        methods=['GET'],
        renderer_classes=[ZipFileRenderer],
    )
    def download(self, request, pk: str):
        """Return a zip of the files."""
        dataset: Dataset = get_object_or_404(Dataset, pk=pk)
        return dataset.streamed_zip_response()


class AlgorithmTaskViewSet(NestedViewSetMixin, ReadOnlyModelViewSet):
    serializer_class = AlgorithmTaskSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return

        queryset = AlgorithmTask.objects.all()
        algorithm__pk = self.request.GET.get('algorithm__pk', None)
        if algorithm__pk is not None:
            queryset = queryset.filter(algorithm__pk=algorithm__pk)

        return queryset

    @swagger_auto_schema(query_serializer=AlgorithmTaskQuerySerializer())
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @swagger_auto_schema(
        query_serializer=AlgorithmTaskLogsSerializer(), responses={200: 'The log text.'}
    )
    @action(detail=True, methods=['GET'], renderer_classes=[PlainTextRenderer])
    def logs(self, request, pk: str):
        """Return the task logs."""
        # Fetch task
        task: AlgorithmTask = get_object_or_404(AlgorithmTask, pk=pk)

        # Grab params
        serializer = AlgorithmTaskLogsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        head = serializer.validated_data.get('head')
        tail = serializer.validated_data.get('tail')

        # Slice text if required
        response_text = task.output_log
        if head or tail:
            lines = response_text.splitlines()
            lines = lines[-tail:] if tail else lines[:head]
            response_text = '\n'.join(lines)

        return Response(response_text, content_type='text/plain')

    @swagger_auto_schema(
        query_serializer=LimitOffsetSerializer(), responses={200: ChecksumFileSerializer(many=True)}
    )
    @action(detail=True, methods=['GET'])
    @paginate_action(ChecksumFileSerializer)
    def input(self, request, pk: str):
        """Return the input dataset as a list of files."""
        return get_object_or_404(
            AlgorithmTask.objects.select_related('input_dataset'), pk=pk
        ).input_dataset.files.all()

    @swagger_auto_schema(
        query_serializer=LimitOffsetSerializer(), responses={200: ChecksumFileSerializer(many=True)}
    )
    @action(detail=True, methods=['GET'])
    @paginate_action(ChecksumFileSerializer)
    def output(self, request, pk: str):
        """Return the task output dataset as a list of files."""
        task: AlgorithmTask = get_object_or_404(AlgorithmTask, pk=pk)
        output_dataset = task.output_dataset

        return output_dataset.files.all() if output_dataset is not None else []

    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                'The Zipped Output Files', schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            '404': 'Not Found',
        },
        produces='application/octet-stream',
    )
    @action(
        detail=True,
        methods=['GET'],
        url_path='output/download',
        renderer_classes=[ZipFileRenderer],
    )
    def download_output(self, request, pk: str):
        """Return a zip of the output files."""
        task: AlgorithmTask = get_object_or_404(
            AlgorithmTask.objects.select_related('output_dataset'), pk=pk
        )
        output_dataset: Dataset = task.output_dataset

        return output_dataset.streamed_zip_response(
            filename=f'{task.algorithm.safe_name}__task_{task.pk}__output.zip'
        )
