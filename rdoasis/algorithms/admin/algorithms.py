from django.contrib import admin
from girder_utils.admin import ReadonlyTabularInline

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, Dataset, DockerImage


class AlgorithmTaskInline(ReadonlyTabularInline):
    model = AlgorithmTask


@admin.register(Algorithm)
class AlgorithmAdmin(admin.ModelAdmin):
    inlines = [AlgorithmTaskInline]
    list_display = ['id', 'name', 'docker_image', 'created', 'modified']


class ChecksumFileInline(ReadonlyTabularInline):
    model = Dataset.files.through


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    inlines = [ChecksumFileInline]
    list_display = ['id', 'name', 'size', 'created', 'modified']


@admin.register(AlgorithmTask)
class AlgorithmTaskAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'algorithm',
        'input_dataset',
        'output_dataset',
        'status',
        'created',
        'modified',
    ]


@admin.register(DockerImage)
class DockerImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'image_id', 'image_file', 'created', 'modified']
