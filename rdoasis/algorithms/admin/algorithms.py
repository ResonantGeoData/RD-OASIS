from django.contrib import admin

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, DockerImage


@admin.register(Algorithm)
class AlgorithmAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'docker_image', 'created', 'modified']


@admin.register(AlgorithmTask)
class AlgorithmTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'algorithm', 'status', 'created', 'modified']


@admin.register(DockerImage)
class DockerImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'image_id', 'image_file', 'created', 'modified']
