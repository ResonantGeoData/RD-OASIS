# import json
# import os
# import shlex
# import shutil
# import subprocess
# import tempfile
# import time

# import GPUtil
from rdoasis.algorithms.models.workflow import Workflow
from django.conf import settings
from typing import Optional, Tuple
from celery.utils.log import get_task_logger

from rdoasis.algorithms.models import WorkflowStep, WorkflowStepRun
from rdoasis.settings import (
    DevelopmentConfiguration,
    ProductionConfiguration,
    HerokuProductionConfiguration,
)

# from django.db.models.fields.files import FieldFile
# import docker
# import magic


logger = get_task_logger(__name__)


def workflow_step_needs_to_run(step: WorkflowStep):
    """Return True if a step needs to be run."""
    last_run = step.last_run
    return last_run is None or last_run.status == WorkflowStepRun.Status.FAILED


def workflow_step_ready_to_run(step: WorkflowStep):
    """Return True if all parent dependencies of a step are fulfilled."""
    for step in step.parents(depth=1):
        last_run = step.last_run
        if last_run is None or last_run.status != WorkflowStepRun.Status.SUCCEEDED:
            return False

    return True


# TODO: Move to settings
def s3_or_minio_credentials() -> Tuple[str, str]:
    """
    Return the access credentials for S3 or MinIO, depending on the environment.

    Returns a tuple of either
        (access_key, secret_key) for MinIO, or
        (access_key_id, secret_access_key) for S3.
    """
    if settings.CONFIGURATION in [ProductionConfiguration, HerokuProductionConfiguration]:
        return settings.AWS_S3_ACCESS_KEY_ID, settings.AWS_S3_SECRET_ACCESS_KEY

    return settings.MINIO_STORAGE_ACCESS_KEY, settings.MINIO_STORAGE_SECRET_KEY


# TODO: Move to settings
def s3_or_minio_bucket_name() -> str:
    """Return the bucket name used by S3 or Minio, depending on the environment."""
    if settings.CONFIGURATION in [ProductionConfiguration, HerokuProductionConfiguration]:
        return settings.AWS_STORAGE_BUCKET_NAME

    return settings.MINIO_STORAGE_MEDIA_BUCKET_NAME


def minio_storage_url() -> Optional[str]:
    if settings.CONFIGURATION == 'rdoasis.settings.DevelopmentConfiguration':
        # return 'http://localhost:9000'
        return f'http://{settings.MINIO_STORAGE_ENDPOINT}'


def get_workflow_collection_mount_point(workflow: Workflow) -> str:
    """Return the path that should be used to mount a workflow's collection."""
    return f'/mnt/workflow_collection_{workflow.pk}'


# def _run_algorithm(algorithm_job):
#     algorithm_file: FieldFile = algorithm_job.algorithm.data
#     dataset_file: FieldFile = algorithm_job.dataset.data
#     try:
#         client = docker.from_env(version='auto', timeout=3600)
#         image = None
#         if algorithm_job.algorithm.docker_image_id:
#             try:
#                 image = client.images.get(algorithm_job.algorithm.docker_image_id)
#                 logger.info(
#                     'Loaded existing docker image %r' % algorithm_job.algorithm.docker_image_id
#                 )
#             except docker.errors.ImageNotFound:
#                 pass
#         if not image:
#             with algorithm_file.open() as algorithm_file_obj:
#                 logger.info('Loading docker image %s' % algorithm_file)
#                 image = client.images.load(algorithm_file_obj)
#                 if len(image) != 1:
#                     raise Exception('tar file contains more than one image')
#                 image = image[0]
#                 algorithm_job.algorithm.docker_image_id = image.attrs['Id']
#                 algorithm_job.algorithm.save(update_fields=['docker_image_id'])
#                 logger.info('Loaded docker image %r' % algorithm_job.algorithm.docker_image_id)
#         with dataset_file.open() as dataset_file_obj:
#             logger.info(
#                 'Running image %s with data %s'
#                 % (algorithm_job.algorithm.docker_image_id, dataset_file)
#             )
#             tmpdir = tempfile.mkdtemp()
#             output_path = os.path.join(tmpdir, 'output.dat')
#             stderr_path = os.path.join(tmpdir, 'stderr.dat')
#             cmd = [
#                 'docker',
#                 'run',
#                 '--rm',
#                 '-i',
#                 '--name',
#                 'algorithm_job_%s_%s' % (algorithm_job.id, time.time()),
#             ]
#             if len(GPUtil.getAvailable()):
#                 cmd += ['--gpus', 'all']
#             cmd += [str(algorithm_job.algorithm.docker_image_id)]
#             logger.info(
#                 'Running %s <%s >%s 2>%s'
#                 % (
#                     ' '.join([shlex.quote(c) for c in cmd]),
#                     shlex.quote(str(dataset_file)),
#                     shlex.quote(output_path),
#                     shlex.quote(stderr_path),
#                 )
#             )
#             try:
#                 subprocess.check_call(
#                     cmd,
#                     stdin=dataset_file_obj,
#                     stdout=open(output_path, 'wb'),
#                     stderr=open(stderr_path, 'wb'),
#                 )
#                 result = 0
#                 algorithm_job.fail_reason = None
#             except subprocess.CalledProcessError as exc:
#                 result = exc.returncode
#                 logger.info(
#                     'Failed to successfully run image %s (%r)'
#                     % (algorithm_job.algorithm.docker_image_id, exc)
#                 )
#                 algorithm_job.fail_reason = 'Return code: %s\nException:\n%r' % (result, exc)
#             logger.info('Finished running image with result %r' % result)
#             # Store result
#             algorithm_result = AlgorithmResult(algorithm_job=algorithm_job)
#             algorithm_result.data.save(
#                 'algorithm_job_%s.dat' % algorithm_job.id, open(output_path, 'rb')
#             )
#             algorithm_result.log.save(
#                 'algorithm_job_%s_log.dat' % algorithm_job.id, open(stderr_path, 'rb')
#             )
#             algorithm_result.data_mimetype = _get_mimetype(output_path)
#             algorithm_result.save()
#             shutil.rmtree(tmpdir)
#             algorithm_job.status = (
#                 AlgorithmJob.Status.SUCCEEDED if not result else AlgorithmJob.Status.FAILED
#             )
#     except Exception as exc:
#         logger.exception(f'Internal error run algorithm {algorithm_job.id}: {exc}')
#         algorithm_job.status = AlgorithmJob.Status.INTERNAL_FAILURE
#         try:
#             algorithm_job.fail_reason = exc.args[0]
#         except Exception:
#             pass
#     return algorithm_job


# def _validate_docker(docker_file):
#     results = {}
#     try:
#         with docker_file.open() as docker_file_obj:
#             client = docker.from_env(version='auto', timeout=3600)
#             logger.info('Loading docker image %s' % docker_file)
#             image = client.images.load(docker_file_obj)
#             if len(image) != 1:
#                 raise Exception('tar file contains more than one image')
#             image = image[0]
#             results['docker_image_id'] = image.attrs['Id']
#             results['docker_attrs'] = json.dumps(image.attrs)
#             logger.info('Loaded docker image %r' % results['docker_image_id'])
#     except Exception as exc:
#         logger.exception(f'Internal error validating docker image: {exc}')
#         try:
#             results['failed'] = exc.args[0]
#         except Exception:
#             results['failed'] = repr(exc)
#     return results


# def _get_mimetype(file_path):
#     mimetype = magic.from_file(file_path, mime=True)
#     # check if mimetype has something useful
#     # empty file returns inode/x-empty
#     if mimetype == 'inode/x-empty':
#         # if no mime type, it can be null(None)
#         return None
#     uncompressed_magic = magic.Magic(mime=True, uncompress=True)
#     uncompressed_mimetype = uncompressed_magic.from_file(file_path)
#     if mimetype == uncompressed_mimetype:
#         return mimetype
#     else:
#         file_mimetype = '%s,%s' % (mimetype, uncompressed_mimetype)
#         # store both mimetypes and return
#         return file_mimetype
