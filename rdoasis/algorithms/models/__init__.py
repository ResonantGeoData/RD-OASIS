from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from rgd.models import ChecksumFile


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
    output_dataset = models.ManyToManyField(
        ChecksumFile, blank=True, related_name='algorithm_tasks'
    )


class Algorithm(TimeStampedModel):
    """An algorithm to run."""

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

    # The input data
    input_dataset = models.ManyToManyField(ChecksumFile, blank=True, related_name='algorithms')

    class Meta:
        constraints = [
            # Enforce that top level is an object
            models.CheckConstraint(
                name='only_objects', check=models.Q(environment__startswith='{')
            ),
        ]

    def run(self):
        # Prevent circular import
        from rdoasis.algorithms.tasks import run_algorithm

        task = AlgorithmTask.objects.create(algorithm=self)
        run_algorithm.delay(algorithm_task_id=task.pk)

        return task
