from rest_framework import serializers

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
