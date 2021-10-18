from rest_framework import serializers

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, DockerImage


class DockerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DockerImage
        fields = '__all__'


class AlgorithmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Algorithm
        fields = '__all__'
        read_only_fields = ['created', 'modified']


class AlgorithmTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlgorithmTask
        fields = '__all__'
