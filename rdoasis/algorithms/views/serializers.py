from rest_framework import serializers

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, DockerImage


class LimitOffsetSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)


class DockerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DockerImage
        fields = '__all__'


class AlgorithmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
        fields = '__all__'
        read_only_fields = ['created', 'modified']

    # Restrict JSONField to DictField with string values
    environment = serializers.DictField(child=serializers.CharField())


class AlgorithmTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlgorithmTask
        exclude = ['output_log']


class AlgorithmTaskLogsSerializer(serializers.Serializer):
    """A serializer for the log action query params."""

    head = serializers.IntegerField(required=False)
    tail = serializers.IntegerField(required=False)
