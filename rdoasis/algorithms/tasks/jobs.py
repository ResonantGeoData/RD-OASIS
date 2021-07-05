from celery import shared_task
from django.db.models.fields.files import FieldFile

from ..models import Algorithm, AlgorithmJob, ScoreAlgorithm, ScoreJob


@shared_task(time_limit=86400)
def run_algorithm(algorithm_job_id, dry_run=False):
    from .helpers import _run_algorithm

    algorithm_job = AlgorithmJob.objects.get(pk=algorithm_job_id)
    if not dry_run:
        algorithm_job.status = AlgorithmJob.Status.RUNNING
        algorithm_job.save(update_fields=['status'])
    algorithm_job = _run_algorithm(algorithm_job)
    if not dry_run:
        algorithm_job.save()
        # Notify


@shared_task(time_limit=86400)
def validate_algorithm(algorithm_id):
    from .helpers import _validate_docker

    algorithm = Algorithm.objects.get(pk=algorithm_id)
    algorithm_file: FieldFile = algorithm.data
    results = _validate_docker(algorithm_file)
    algorithm.docker_image_id = results.get('docker_image_id')
    algorithm.docker_attrs = results.get('docker_attrs')
    algorithm.docker_validation_failure = results.get('failed')
    algorithm.save(update_fields=['docker_image_id', 'docker_attrs', 'docker_validation_failure'])


@shared_task(time_limit=86400)
def validate_scoring(score_algorithm_id):
    from .helpers import _validate_docker

    score_algorithm = ScoreAlgorithm.objects.get(pk=score_algorithm_id)
    score_algorithm_file: FieldFile = score_algorithm.data
    results = _validate_docker(score_algorithm_file)
    score_algorithm.docker_image_id = results.get('docker_image_id')
    score_algorithm.docker_attrs = results.get('docker_attrs')
    score_algorithm.docker_validation_failure = results.get('failed')
    score_algorithm.save(
        update_fields=['docker_image_id', 'docker_attrs', 'docker_validation_failure']
    )


@shared_task(time_limit=86400)
def run_scoring(score_job_id, dry_run=False):
    from .helpers import _run_scoring

    score_job = ScoreJob.objects.get(pk=score_job_id)
    if not dry_run:
        score_job.status = ScoreJob.Status.RUNNING
        score_job.save(update_fields=['status'])
    score_job = _run_scoring(score_job)
    if not dry_run:
        score_job.save()
        # Notify
