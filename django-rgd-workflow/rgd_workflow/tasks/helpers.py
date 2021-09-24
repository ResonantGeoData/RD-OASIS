import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time

import GPUtil
from celery.utils.log import get_task_logger
from django.db.models.fields.files import FieldFile
import docker
from girder_utils.files import field_file_to_local_path
import magic

from ..models import AlgorithmJob, AlgorithmResult, ScoreJob, ScoreResult

logger = get_task_logger(__name__)


def _run_algorithm(algorithm_job):
    algorithm_file: FieldFile = algorithm_job.algorithm.data
    dataset_file: FieldFile = algorithm_job.dataset.data
    try:
        client = docker.from_env(version='auto', timeout=3600)
        image = None
        if algorithm_job.algorithm.docker_image_id:
            try:
                image = client.images.get(algorithm_job.algorithm.docker_image_id)
                logger.info(
                    'Loaded existing docker image %r' % algorithm_job.algorithm.docker_image_id
                )
            except docker.errors.ImageNotFound:
                pass
        if not image:
            with algorithm_file.open() as algorithm_file_obj:
                logger.info('Loading docker image %s' % algorithm_file)
                image = client.images.load(algorithm_file_obj)
                if len(image) != 1:
                    raise Exception('tar file contains more than one image')
                image = image[0]
                algorithm_job.algorithm.docker_image_id = image.attrs['Id']
                algorithm_job.algorithm.save(update_fields=['docker_image_id'])
                logger.info('Loaded docker image %r' % algorithm_job.algorithm.docker_image_id)
        with dataset_file.open() as dataset_file_obj:
            logger.info(
                'Running image %s with data %s'
                % (algorithm_job.algorithm.docker_image_id, dataset_file)
            )
            tmpdir = tempfile.mkdtemp()
            output_path = os.path.join(tmpdir, 'output.dat')
            stderr_path = os.path.join(tmpdir, 'stderr.dat')
            cmd = [
                'docker',
                'run',
                '--rm',
                '-i',
                '--name',
                'algorithm_job_%s_%s' % (algorithm_job.id, time.time()),
            ]
            if len(GPUtil.getAvailable()):
                cmd += ['--gpus', 'all']
            cmd += [str(algorithm_job.algorithm.docker_image_id)]
            logger.info(
                'Running %s <%s >%s 2>%s'
                % (
                    ' '.join([shlex.quote(c) for c in cmd]),
                    shlex.quote(str(dataset_file)),
                    shlex.quote(output_path),
                    shlex.quote(stderr_path),
                )
            )
            try:
                subprocess.check_call(
                    cmd,
                    stdin=dataset_file_obj,
                    stdout=open(output_path, 'wb'),
                    stderr=open(stderr_path, 'wb'),
                )
                result = 0
                algorithm_job.fail_reason = None
            except subprocess.CalledProcessError as exc:
                result = exc.returncode
                logger.info(
                    'Failed to successfully run image %s (%r)'
                    % (algorithm_job.algorithm.docker_image_id, exc)
                )
                algorithm_job.fail_reason = 'Return code: %s\nException:\n%r' % (result, exc)
            logger.info('Finished running image with result %r' % result)
            # Store result
            algorithm_result = AlgorithmResult(algorithm_job=algorithm_job)
            algorithm_result.data.save(
                'algorithm_job_%s.dat' % algorithm_job.id, open(output_path, 'rb')
            )
            algorithm_result.log.save(
                'algorithm_job_%s_log.dat' % algorithm_job.id, open(stderr_path, 'rb')
            )
            algorithm_result.data_mimetype = _get_mimetype(output_path)
            algorithm_result.save()
            shutil.rmtree(tmpdir)
            algorithm_job.status = (
                AlgorithmJob.Status.SUCCEEDED if not result else AlgorithmJob.Status.FAILED
            )
    except Exception as exc:
        logger.exception(f'Internal error run algorithm {algorithm_job.id}: {exc}')
        algorithm_job.status = AlgorithmJob.Status.INTERNAL_FAILURE
        try:
            algorithm_job.fail_reason = exc.args[0]
        except Exception:
            pass
    return algorithm_job


def _run_scoring(score_job):
    score_algorithm_file: FieldFile = score_job.score_algorithm.data
    algorithm_result_file: FieldFile = score_job.algorithm_result.data
    groundtruth_file: FieldFile = score_job.groundtruth.data
    try:
        client = docker.from_env(version='auto', timeout=3600)
        image = None
        if score_job.score_algorithm.docker_image_id:
            try:
                image = client.images.get(score_job.score_algorithm.docker_image_id)
                logger.info(
                    'Loaded existing docker image %r' % score_job.score_algorithm.docker_image_id
                )
            except docker.errors.ImageNotFound:
                pass
        if not image:
            with field_file_to_local_path(score_algorithm_file) as score_algorithm_path:
                logger.info('Loading docker image %s' % score_algorithm_path)
                image = client.images.load(open(score_algorithm_path, 'rb'))
                if len(image) != 1:
                    raise Exception('tar file contains more than one image')
                image = image[0]
                score_job.score_algorithm.docker_image_id = image.attrs['Id']
                score_job.score_algorithm.save(update_fields=['docker_image_id'])
                logger.info('Loaded docker image %r' % score_job.score_algorithm.docker_image_id)
        with field_file_to_local_path(
            algorithm_result_file
        ) as algorithm_result_path, field_file_to_local_path(groundtruth_file) as groundtruth_path:
            logger.info(
                'Running image %s with groundtruth %s and results %s'
                % (
                    score_job.score_algorithm.docker_image_id,
                    groundtruth_path,
                    algorithm_result_path,
                )
            )
            tmpdir = tempfile.mkdtemp()
            output_path = os.path.join(tmpdir, 'output.dat')
            stderr_path = os.path.join(tmpdir, 'stderr.dat')
            cmd = [
                'docker',
                'run',
                '--rm',
                '-i',
                '--name',
                'score_job_%s_%s' % (score_job.id, time.time()),
                '-v',
                '%s:%s:ro' % (groundtruth_path, '/groundtruth.dat'),
                str(score_job.score_algorithm.docker_image_id),
            ]
            logger.info(
                'Running %s <%s >%s 2>%s'
                % (
                    ' '.join([shlex.quote(c) for c in cmd]),
                    shlex.quote(str(algorithm_result_path)),
                    shlex.quote(output_path),
                    shlex.quote(stderr_path),
                )
            )
            try:
                subprocess.check_call(
                    cmd,
                    stdin=open(algorithm_result_path, 'rb'),
                    stdout=open(output_path, 'wb'),
                    stderr=open(stderr_path, 'wb'),
                )
                result = 0
                score_job.fail_reason = None
            except subprocess.CalledProcessError as exc:
                result = exc.returncode
                logger.info(
                    'Failed to successfully run image %s (%r)' % (score_algorithm_path, exc)
                )
                score_job.fail_reason = 'Return code: %s\nException:\n%r' % (result, exc)
            logger.info('Finished running image with result %r' % result)
            score_result = ScoreResult(score_job=score_job)
            score_result.data.save('score_job_%s.dat' % score_job.id, open(output_path, 'rb'))
            score_result.log.save('score_job_%s_log.dat' % score_job.id, open(stderr_path, 'rb'))
            score_result.overall_score, score_result.result_type = _overall_score_and_result_type(
                score_result.data
            )
            score_result.save()
            shutil.rmtree(tmpdir)
            score_job.status = ScoreJob.Status.SUCCEEDED if not result else ScoreJob.Status.FAILED
    except Exception as exc:
        logger.exception(f'Internal error run score_algorithm {score_job.id}: {exc}')
        score_job.status = ScoreJob.Status.INTERNAL_FAILURE
        try:
            score_job.fail_reason = exc.args[0]
        except Exception:
            pass
    return score_job


def _validate_docker(docker_file):
    results = {}
    try:
        with docker_file.open() as docker_file_obj:
            client = docker.from_env(version='auto', timeout=3600)
            logger.info('Loading docker image %s' % docker_file)
            image = client.images.load(docker_file_obj)
            if len(image) != 1:
                raise Exception('tar file contains more than one image')
            image = image[0]
            results['docker_image_id'] = image.attrs['Id']
            results['docker_attrs'] = json.dumps(image.attrs)
            logger.info('Loaded docker image %r' % results['docker_image_id'])
    except Exception as exc:
        logger.exception(f'Internal error validating docker image: {exc}')
        try:
            results['failed'] = exc.args[0]
        except Exception:
            results['failed'] = repr(exc)
    return results


def _overall_score_and_result_type(datafile):
    # In the future, inspect the data to determine the result type.
    # For now, just extract a float from the data file
    try:
        overall_score = float(datafile.readline())
        result_type = ScoreResult.ResultTypes.SIMPLE
    except ValueError:
        return None, None
    return overall_score, result_type


def _get_mimetype(file_path):
    mimetype = magic.from_file(file_path, mime=True)
    # check if mimetype has something useful
    # empty file returns inode/x-empty
    if mimetype == 'inode/x-empty':
        # if no mime type, it can be null(None)
        return None
    uncompressed_magic = magic.Magic(mime=True, uncompress=True)
    uncompressed_mimetype = uncompressed_magic.from_file(file_path)
    if mimetype == uncompressed_mimetype:
        return mimetype
    else:
        file_mimetype = '%s,%s' % (mimetype, uncompressed_mimetype)
        # store both mimetypes and return
        return file_mimetype
