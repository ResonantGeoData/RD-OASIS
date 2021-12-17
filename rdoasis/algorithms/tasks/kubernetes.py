from pathlib import Path
import os
import re
import shlex
import tempfile

import celery
from celery.utils.log import get_task_logger
from rdoasis.algorithms.models import Algorithm, AlgorithmTask


logger = get_task_logger(__name__)


class ManagedK8sTask(celery.Task):
    def _setup(self, **kwargs):
        # Set algorithm task and update status
        self.algorithm_task: AlgorithmTask = AlgorithmTask.objects.select_related(
            'algorithm', 'input_dataset', 'output_dataset'
        ).get(pk=kwargs['algorithm_task_id'])
        self.algorithm_task.status = AlgorithmTask.Status.RUNNING
        self.algorithm_task.save()

        # Set algorithm
        self.algorithm: Algorithm = self.algorithm_task.algorithm

    def _construct_job(self):
        from kubernetes import client, config

        # Load config from outside of k8s cluster
        config.load_kube_config()

        # Define volume
        volume = client.V1Volume(
            name='task-data',
            empty_dir=client.V1EmptyDirVolumeSource(),
        )

        job_name = 'test'
        temp_path = Path(tempfile.mkdtemp())

        # Define container with volume mount
        image_id = self.algorithm_task.algorithm.docker_image.image_id
        args = shlex.split(self.algorithm_task.algorithm.command)
        main_container_name = re.sub(r'[^a-zA-Z\d-]', '-', image_id.lower())
        main_container = client.V1Container(
            name=main_container_name,
            image=image_id,
            args=args,
            volume_mounts=[client.V1VolumeMount(name='task-data', mount_path=str(temp_path))],
            working_dir=str(temp_path),
            # resources=client.V1ResourceRequirements(limits={'nvidia.com/gpu': 1}),
        )

        monitor_container = client.V1Container(
            name=f'{main_container_name}--monitor',
            image='oasis-sidecar',
            volume_mounts=[client.V1VolumeMount(name='task-data', mount_path=str(temp_path))],
            image_pull_policy='Never',
            lifecycle=client.V1Lifecycle(
                post_start=client.V1Handler(
                    _exec=client.V1ExecAction(
                        command=['/opt/django-project/manage.py', 'setup_container_k8s']
                    ),
                ),
            ),
            env=[
                # Django envs
                client.V1EnvVar(
                    name='DJANGO_CONFIGURATION',
                    value='DevelopmentConfiguration',
                ),
                client.V1EnvVar(
                    name='DJANGO_DATABASE_URL',
                    value='postgres://postgres:postgres@host.minikube.internal:5432/django',
                ),
                client.V1EnvVar(
                    name='DJANGO_CELERY_BROKER_URL',
                    value='amqp://host.minikube.internal:5672/',
                ),
                client.V1EnvVar(
                    name='DJANGO_MINIO_STORAGE_ENDPOINT',
                    value='host.minikube.internal:9000',
                ),
                client.V1EnvVar(
                    name='DJANGO_MINIO_STORAGE_ACCESS_KEY',
                    value=os.environ['DJANGO_MINIO_STORAGE_ACCESS_KEY'],
                ),
                client.V1EnvVar(
                    name='DJANGO_MINIO_STORAGE_SECRET_KEY',
                    value=os.environ['DJANGO_MINIO_STORAGE_SECRET_KEY'],
                ),
                client.V1EnvVar(
                    name='DJANGO_STORAGE_BUCKET_NAME',
                    value=os.environ['DJANGO_STORAGE_BUCKET_NAME'],
                ),
                #
                # Extra envs
                client.V1EnvVar(name='JOB_NAME', value=job_name),
                client.V1EnvVar(name='CONTAINER_NAME', value=main_container_name),
                client.V1EnvVar(name='TASK_ID', value=str(self.algorithm_task.pk)),
                client.V1EnvVar(name='TEMP_DIR', value=str(temp_path)),
            ],
            # resources=client.V1ResourceRequirements(limits={'nvidia.com/gpu': 1}),
        )

        # Define job template
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(name=job_name),
            spec=client.V1PodSpec(
                restart_policy="Never",
                # Monitor container must be defined first, so the post_start lifecycle hook
                # delays the main container from starting
                containers=[monitor_container, main_container],
                volumes=[volume],
                service_account_name='job-robot',
            ),
        )

        # Instantiate and return the job object
        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name="test"),
            spec=client.V1JobSpec(
                template=template,
                backoff_limit=0,
                ttl_seconds_after_finished=30,
            ),
        )

    def __call__(self, *args, **kwargs):
        self._setup(**kwargs)
        return super().__call__(*args, **kwargs)

    def run_algorithm_task_k8s(self, *args, **kwargs):
        # Import kubernetes here so django can import task
        from kubernetes import config, client

        # Load config from outside of k8s cluster
        config.load_kube_config()

        api = client.BatchV1Api()
        job: client.V1Job = self._construct_job()
        job: client.V1Job = api.create_namespaced_job(namespace='default', body=job)


@celery.shared_task(base=ManagedK8sTask, bind=True)
def run_algorithm_task_k8s(self: ManagedK8sTask, *args, **kwargs):
    """
    Run an algorithm task.

    Args:
        algorithm_task_id: The ID of the algorithm task to run.s

    Returns:
        The status code returned from docker.
    """
    return self.run_algorithm_task_k8s(*args, **kwargs)
