from django.core.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from rdoasis.algorithms.models import DockerImage, Workflow, WorkflowStep


class DockerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DockerImage
        fields = '__all__'


class WorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workflow
        fields = '__all__'
        read_only_fields = ['collection']


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        fields = '__all__'


class WorkflowStepReturnSerializer(WorkflowStepSerializer):
    docker_image = DockerImageSerializer()
    parents = serializers.SerializerMethodField()

    def get_parents(self, obj: WorkflowStep):
        return [p.pk for p in obj.parents(depth=1)]


class WorkflowStepCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStep
        exclude = ['workflow']


class WorkflowStepLinkSerializer(serializers.Serializer):
    parent = serializers.IntegerField()
    child = serializers.IntegerField()


class WorkflowViewSet(ModelViewSet):
    queryset = Workflow.objects.all().select_related('collection')
    serializer_class = WorkflowSerializer
    pagination_class = LimitOffsetPagination


class WorkflowStepViewSet(NestedViewSetMixin, ReadOnlyModelViewSet):
    serializer_class = WorkflowStepReturnSerializer
    pagination_class = LimitOffsetPagination
    lookup_field = 'id'

    def get_queryset(self):
        """Override get_queryset to return steps from this workflow, in order."""
        workflow_pk = self.request.parser_context['kwargs']['parent_lookup_workflow__pk']
        workflow: Workflow = get_object_or_404(Workflow, pk=workflow_pk)
        return workflow._steps_queryset(None)

    @swagger_auto_schema(
        request_body=WorkflowStepCreateSerializer(), responses={200: WorkflowStepSerializer()}
    )
    def create(self, request, parent_lookup_workflow__pk: str):
        """Add a root step to the workflow."""
        workflow: Workflow = get_object_or_404(Workflow, pk=parent_lookup_workflow__pk)
        serializer = WorkflowStepSerializer(data={**request.data, 'workflow': workflow.pk})
        serializer.is_valid(raise_exception=True)

        step, created = WorkflowStep.objects.get_or_create(**serializer.validated_data)
        if not created:
            return Response(
                'A step with this name already exists in this workflow.',
                status=HTTP_400_BAD_REQUEST,
            )

        # Insert step into the workflow
        workflow.add_root_step(step)

        return Response(WorkflowStepReturnSerializer(step).data)

    @swagger_auto_schema(
        request_body=WorkflowStepCreateSerializer(), responses={200: WorkflowStepSerializer()}
    )
    def update(self, request, parent_lookup_workflow__pk: str, id: str):
        """Update the workflow step."""
        workflow: Workflow = get_object_or_404(Workflow, pk=parent_lookup_workflow__pk)
        workflow_step: WorkflowStep = get_object_or_404(WorkflowStep, pk=id)

        serializer = WorkflowStepSerializer(data={**request.data, 'workflow': workflow.pk})
        serializer.is_valid(raise_exception=True)

        # Use update_or_create to update and return the new step in one shot
        workflow_step, _ = WorkflowStep.objects.update_or_create(defaults=serializer.validated_data)
        return Response(WorkflowStepReturnSerializer(workflow_step).data)

    def destroy(self, request, parent_lookup_workflow__pk: str, id: str):
        workflow_step: WorkflowStep = get_object_or_404(WorkflowStep, pk=id)
        workflow_step.delete()

        return Response(status=HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=WorkflowStepCreateSerializer(), responses={200: WorkflowStepSerializer()}
    )
    @action(detail=True, methods=['POST'])
    def append(self, request, parent_lookup_workflow__pk: str, id: str):
        """Create a workflow step as a child of another step."""
        workflow: Workflow = get_object_or_404(Workflow, pk=parent_lookup_workflow__pk)
        base_workflow_step: WorkflowStep = get_object_or_404(WorkflowStep, pk=id)

        serializer = WorkflowStepSerializer(data={**request.data, 'workflow': workflow.pk})
        serializer.is_valid(raise_exception=True)

        new_workflow_step, created = WorkflowStep.objects.get_or_create(**serializer.validated_data)
        if not created:
            return Response(
                'A step with this name already exists in this workflow.',
                status=HTTP_400_BAD_REQUEST,
            )

        base_workflow_step.append_step(new_workflow_step)
        return Response(WorkflowStepSerializer(new_workflow_step).data)

    @swagger_auto_schema(
        request_body=WorkflowStepLinkSerializer(), responses={200: WorkflowStepSerializer()}
    )
    @action(detail=False, methods=['POST'])
    def link(self, request, parent_lookup_workflow__pk: str):
        """Link an existing workflow step to another."""
        serializer = WorkflowStepLinkSerializer(data={**request.data})
        serializer.is_valid(raise_exception=True)

        parent_workflow_step: WorkflowStep = get_object_or_404(
            WorkflowStep, pk=serializer.validated_data['parent']
        )
        child_workflow_step: WorkflowStep = get_object_or_404(
            WorkflowStep, pk=serializer.validated_data['child']
        )

        try:
            parent_workflow_step.append_step(child_workflow_step)
        except ValidationError as e:
            return Response(e.message, status=HTTP_400_BAD_REQUEST)

        return Response(WorkflowStepSerializer(child_workflow_step).data)
