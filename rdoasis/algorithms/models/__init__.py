from typing import Dict, Generator, Union
from zipfile import ZIP_DEFLATED

import celery
from django.db import models
from django.db.models.functions import Length
from django.dispatch import receiver
from django.http.response import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from rgd.models import ChecksumFile, FileSourceType
import zipstream

from rdoasis.algorithms.utils.zip import StreamingZipFile

# Register length transform
models.CharField.register_lookup(Length)


class DockerImage(TimeStampedModel):
    # Optional name
    name = models.CharField(null=True, max_length=255)

    # The image id to pull down
    image_id = models.CharField(null=True, blank=True, max_length=255)

    # If the docker image was provided as a file
    image_file = models.ForeignKey(
        ChecksumFile, related_name='docker_images', null=True, blank=True, on_delete=models.CASCADE
    )

    # TODO: Add field for registry, for other images
    # registry = models.URLField(null=True)

    class Meta:
        constraints = [
            # Ensure that only one of these fields can be set at a time
            models.CheckConstraint(
                check=(
                    models.Q(image_id__isnull=True, image_file__isnull=False)
                    | models.Q(
                        image_id__isnull=False, image_id__length__gt=0, image_file__isnull=True
                    )
                ),
                name='single_image_source',
            )
        ]


class Dataset(TimeStampedModel):
    """A collection of multiple ChecksumFiles."""

    name = models.CharField(max_length=256, unique=True)
    files = models.ManyToManyField(ChecksumFile, blank=True, related_name='datasets')
    size = models.PositiveBigIntegerField(null=True, blank=True)

    def compute_size(self):
        """Compute the total size of all files in this dataset."""
        self.size = sum(
            (file.file.size for file in self.files.all() if file.type == FileSourceType.FILE_FIELD)
        )
        self.save()

        return self.size

    def file_object_generator(self, compress_type=None) -> Generator[Dict, None, None]:
        """Yield zipstream arguments from this dataset's files."""
        for file in self.files.all():
            yield {
                'arcname': file.name,
                'iterable': file.file,
                'compress_type': compress_type,
            }

    def streamed_zip(self) -> zipstream.ZipFile:
        """
        Return the files in this dataset, as a streamed zip file.

        The returned stream yields chunks of the zip file when iterated over.
        """
        z = StreamingZipFile(compression=ZIP_DEFLATED)
        z.write_from_generator(self.file_object_generator())

        return z

    def streamed_zip_response(self, filename=None) -> StreamingHttpResponse:
        download_file_name = filename or f'{self.name}.zip'

        z = self.streamed_zip()
        res = StreamingHttpResponse(z, content_type='application/zip')
        res['Content-Disposition'] = f'attachment; filename="{download_file_name}"'

        return res


@celery.shared_task()
def compute_dataset_size(dataset_id: int):
    dataset: Dataset = Dataset.objects.get(id=dataset_id)
    return dataset.compute_size()


@receiver(models.signals.m2m_changed, sender=Dataset.files.through)
def update_dataset_size(sender, instance: Dataset, action: str, reverse: bool, **kwargs):
    """Compute the dataset size if files have been added/removed."""
    if (
        not reverse
        and instance.pk is not None
        and action in ('post_add', 'post_remove', 'post_clear')
    ):
        compute_dataset_size.delay(instance.pk)


@receiver(models.signals.post_save, sender=Dataset)
def init_dataset_size(sender, instance: Dataset, **kwargs):
    """Compute the dataset size if it's not been set yet."""
    if instance.pk is not None and instance.size is None:
        compute_dataset_size.delay(instance.pk)


class AlgorithmTask(TimeStampedModel):
    """A run of an algorithm."""

    class Status(models.TextChoices):
        CREATED = 'created', _('Created but not queued')
        QUEUED = 'queued', _('Queued for processing')
        RUNNING = 'running', _('Running')
        FAILED = 'failed', _('Failed')
        SUCCEEDED = 'success', _('Succeeded')

    algorithm = models.ForeignKey('Algorithm', related_name='tasks', on_delete=models.CASCADE)
    status = models.CharField(choices=Status.choices, default=Status.QUEUED, max_length=16)
    output_log = models.TextField(null=True, blank=True, default='')
    input_dataset = models.ForeignKey(
        Dataset, related_name='input_tasks', on_delete=models.RESTRICT
    )
    output_dataset = models.ForeignKey(
        Dataset, blank=True, null=True, on_delete=models.RESTRICT, related_name='output_tasks'
    )

    def output_dataset_zip(self) -> zipstream.ZipFile:
        """
        Return the files in this task's output dataset, as a streamed zip file.

        The returned stream yields chunks of the zip file when iterated over.
        """
        z = zipstream.ZipFile()
        for file in self.output_dataset.files.all():
            z.write_iter(file.name, file.file)

        return z


class Algorithm(TimeStampedModel):
    """An algorithm to run."""

    # The name of the Algorithm
    name = models.CharField(max_length=255)

    # The docker image to use
    docker_image = models.ForeignKey(
        DockerImage, related_name='workflow_steps', on_delete=models.CASCADE
    )

    # The command to run the image with
    command = models.CharField(max_length=1000, null=True, blank=True, default=None)

    # The entrypoint of the container
    entrypoint = models.CharField(max_length=1000, null=True, blank=True, default=None)

    # Environment variables to be passed to the container
    environment = models.JSONField(default=dict)

    # Whether the GPU should be requested or not
    gpu = models.BooleanField(default=False)

    class Meta:
        constraints = [
            # Enforce that top level is an object
            models.CheckConstraint(
                name='only_objects', check=models.Q(environment__startswith='{')
            ),
        ]

    @property
    def safe_name(self):
        return '_'.join(self.name.split())

    def run(self, dataset_id: Union[str, int]):
        # Prevent circular import
        from rdoasis.algorithms.tasks import run_algorithm_task

        task = AlgorithmTask.objects.create(algorithm=self, input_dataset_id=dataset_id)
        run_algorithm_task.delay(algorithm_task_id=task.pk)

        return task
