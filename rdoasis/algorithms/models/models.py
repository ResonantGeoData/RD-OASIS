from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from s3_file_field import S3FileField

from . import validators

# We may want to have some sort of access permissions on Task, Dataset,
# Groundtruth, etc.


class DeferredFieldsManager(models.Manager):
    def __init__(self, *deferred_fields):
        self.deferred_fields = deferred_fields
        super().__init__()

    def get_queryset(self):
        return super().get_queryset().defer(*self.deferred_fields)


class Task(models.Model):
    """
    Data processing task.

    A task is a conceptual activity.  Datasets associated with a task, when
    processed by appropriate algorithms, produce results.
    """

    def __str__(self):
        return self.name

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    created = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    def get_absolute_url(self):
        return reverse('task-detail', kwargs={'pk': self.pk, 'name': self.name})


class Dataset(models.Model):
    """
    Dataset for algorithms.

    A dataset is a combined set of inputs for an algorithm.
    """

    def __str__(self):
        return self.name

    # A tarball of data
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    created = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)
    tasks = models.ManyToManyField(Task)
    # TODO: If we try to edit data and this has been referenced anywhere, we
    # need to make a new model and mark this one as inactive
    data = S3FileField()


class Groundtruth(models.Model):
    """
    Groundtruth.

    Groundtruth is the expected output of a specific algorithm on a specific
    dataset.
    """

    # The data used by the scorer to compare the output of the algorithm

    def __str__(self):
        return self.name

    class Meta:
        """Groundtruth is for a specific task and dataset."""

        unique_together = ('task', 'dataset')

    name = models.CharField(max_length=100)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    created = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)
    # public is True for test datasets, False for internal datasets
    public = models.BooleanField(default=False)
    # TODO: If we try to edit data and this has been referenced anywhere, we
    # need to make a new model and mark this one as inactive
    data = S3FileField()


class Algorithm(models.Model):
    """
    Data processing alogorithm.

    An algorithm is a docker image that takes a dataset on stdin, outputs logs
    on stderr and results on stdout.
    """

    def __str__(self):
        return self.name

    # A docker that takes a dataset and outputs results
    # A docker tarball; when creating, we can offer to pull a docker
    name = models.CharField(max_length=100, unique=True)
    # TODO: allow for multiple tasks
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    created = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)
    # TODO: If we try to edit data and this has been referenced anywhere, we
    # need to make a new model and mark this one as inactive
    data = S3FileField(validators=[validators.MimetypeValidator(['application/x-tar'])])
    docker_image_id = models.TextField(null=True, blank=True)
    docker_attrs = models.TextField(null=True, blank=True)
    docker_validation_failure = models.TextField(null=True, blank=True)

    def get_absolute_url(self):
        return reverse('algorithm-detail', kwargs={'creator': str(self.creator), 'pk': self.pk})

    def validate_algorithm(self):
        """Validate the algorithm asynchronously."""
        from .. import tasks

        tasks.validate_algorithm.delay(self.id)

    def _post_save(self, created, *args, **kwargs):
        if (
            not created
            and kwargs.get('update_fields')
            and 'data' not in kwargs.get('update_fields')
        ):
            return
        self.validate_algorithm()


class ScoreAlgorithm(models.Model):
    """
    Scoring alogorithm.

    A scoring algorithm is a docker image that takes results from an algorithm
    on stdin and groundtruth as a file at /groundtruth.dat, then outputs logs
    on stderr and results on stdout.
    """

    def __str__(self):
        return self.name

    # A docker that takes an algorithm's output and a groundtruth as input and
    # outputs a score
    # A docker tarball; when creating, we can offer to pull a docker
    name = models.CharField(max_length=100, unique=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    created = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)
    # TODO: If we try to edit data and this has been referenced anywhere, we
    # need to make a new model and mark this one as inactive
    data = S3FileField(
        validators=[validators.MimetypeValidator(['application/x-tar'])],
    )
    docker_image_id = models.TextField(null=True, blank=True)
    docker_attrs = models.TextField(null=True, blank=True)
    docker_validation_failure = models.TextField(null=True, blank=True)

    def validate_score_algorithm(self):
        """Validate the algorithm asynchronously."""
        from .. import tasks

        tasks.validate_scoring.delay(self.id)

    def _post_save(self, created, *args, **kwargs):
        if (
            not created
            and kwargs.get('update_fields')
            and 'data' not in kwargs.get('update_fields')
        ):
            return
        self.validate_score_algorithm()


class AlgorithmJob(models.Model):
    """
    Algorithm job.

    An algorithm job tracks running an algorithm on a specific dataset.
    """

    class Meta:
        ordering = ['-created']

    class Status(models.TextChoices):
        CREATED = 'created', _('Created but not queued')
        QUEUED = 'queued', _('Queued for processing')
        RUNNING = 'running', _('Processing')
        INTERNAL_FAILURE = 'internal_failure', _('Internal failure')
        FAILED = 'failed', _('Failed')
        SUCCEEDED = 'success', _('Succeeded')

    algorithm = models.ForeignKey(Algorithm, on_delete=models.DO_NOTHING)
    dataset = models.ForeignKey(Dataset, on_delete=models.DO_NOTHING)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    created = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default=Status.QUEUED, choices=Status.choices)
    fail_reason = models.TextField(null=True, blank=True)

    # it might be nice to have an array of status/timestamp/log for tracking
    # when status changed.

    def get_absolute_url(self):
        return reverse('job-detail', kwargs={'creator': str(self.creator), 'pk': self.pk})

    @property
    def results(self):
        """Get all associated AlgorithmResult objects."""
        return self.algorithmresult_set.all()

    def run_algorithm(self):
        """Run the job asynchronously."""
        from .. import tasks

        tasks.run_algorithm.delay(self.id)

    def _post_save(self, created, *args, **kwargs):
        if (
            not created
            and kwargs.get('update_fields')
            and 'status' not in kwargs.get('update_fields')
        ):
            return
        if self.status == self.Status.QUEUED:
            self.run_algorithm()
        # We may want to implement canceling here


class AlgorithmResult(models.Model):
    """
    Algorithm result.

    When an algorithm job runs an algorithm on a dataset, it produces an
    algorithm result.
    """

    algorithm_job = models.ForeignKey(AlgorithmJob, on_delete=models.CASCADE, blank=True, null=True)
    created = models.DateTimeField(default=timezone.now)
    data = S3FileField()
    log = S3FileField(null=True, blank=True)
    data_mimetype = models.TextField(null=True, blank=True)


class ScoreJob(models.Model):
    """
    Score job.

    A score job tracks running a scoring algorithm on algorithm results and the
    groundtruth associated with the algorithm job's dataset.
    """

    class Status(models.TextChoices):
        CREATED = 'created', _('Created but not queued')
        QUEUED = 'queued', _('Queued for processing')
        RUNNING = 'running', _('Processing')
        INTERNAL_FAILURE = 'internal_failure', _('Internal failure')
        FAILED = 'failed', _('Failed')
        SUCCEEDED = 'success', _('Succeeded')

    previous_status = None

    score_algorithm = models.ForeignKey(ScoreAlgorithm, on_delete=models.DO_NOTHING)
    algorithm_result = models.ForeignKey(AlgorithmResult, on_delete=models.DO_NOTHING)
    groundtruth = models.ForeignKey(Groundtruth, on_delete=models.DO_NOTHING)
    creator = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING)
    created = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default=Status.QUEUED, choices=Status.choices)
    fail_reason = models.TextField(null=True, blank=True)

    # it might be nice to have an array of status/timestamp/log for tracking
    # when status changed.

    def run_scoring(self):
        """Run the job asynchronously."""
        import sys

        from .. import tasks

        sys.stderr.write('SCORE JOB %r\n' % [self.id])
        tasks.run_scoring.delay(self.id)

    def _post_save(self, created, *args, **kwargs):
        if (
            not created
            and kwargs.get('update_fields')
            and 'status' not in kwargs.get('update_fields')
        ):
            return
        if self.status == self.Status.QUEUED:
            self.run_scoring()
        # We may want to implement canceling here


class ScoreResult(models.Model):
    class ResultTypes(models.TextChoices):
        SIMPLE = 'simple', _('Direct value')
        ROC = 'roc', _('Receiver Operating Characteristic')

    score_job = models.ForeignKey(ScoreJob, on_delete=models.CASCADE, blank=True, null=True)
    created = models.DateTimeField(default=timezone.now)
    data = S3FileField()
    log = S3FileField(null=True, blank=True)
    overall_score = models.FloatField(
        null=True, blank=True, validators=[MaxValueValidator(1.0), MinValueValidator(0.0)]
    )
    result_type = models.CharField(
        max_length=10, choices=ResultTypes.choices, null=True, blank=True
    )
