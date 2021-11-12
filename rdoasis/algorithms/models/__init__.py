from typing import Union

from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from rgd.models import ChecksumFile, FileSourceType
import zipstream


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
                    models.Q(image_id__isnull=False, image_file__isnull=True)
                    | models.Q(image_id__isnull=True, image_file__isnull=False)
                ),
                name='single_image_source',
            )
        ]


class Dataset(TimeStampedModel):
    """A collection of multiple ChecksumFiles."""

    name = models.CharField(max_length=256, unique=True)
    files = models.ManyToManyField(ChecksumFile, blank=True, related_name='datasets')
    size = models.PositiveBigIntegerField(null=True)

    def compute_size(self):
        """Compute the total size of all files in this dataset."""
        self.size = sum(
            (f.file.size for f in self.files.all() if f.type == FileSourceType.FILE_FIELD)
        )
        self.save()

        return self.size


@receiver(models.signals.m2m_changed, sender=Dataset.files.through)
def update_dataset_size(sender, instance: Dataset, action: str, reverse: bool, **kwargs):
    if not reverse and action in ('post_add', 'post_remove', 'post_clear'):
        instance.compute_size()


@receiver(models.signals.post_save, sender=Dataset)
def init_dataset_size(sender, instance: Dataset, **kwargs):
    if instance.size is None:
        instance.compute_size()


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
