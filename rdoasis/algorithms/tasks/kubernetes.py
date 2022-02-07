import os
from pathlib import Path
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

        # Define job vars
        self.temp_path = Path(tempfile.mkdtemp())
        self.job_name = f'algorithm-{self.algorithm.pk}-task-{self.algorithm_task.pk}'
        self.image_id = self.algorithm_task.algorithm.docker_image.image_id
        self.main_container_name = re.sub(r'[^a-zA-Z\d-]', '-', self.image_id.lower())

    def _sidecar_container_env_vars(self):
        from kubernetes import client, config

        # Load config from outside of k8s cluster
        config.load_kube_config()

        return [
            client.V1EnvVar(
                name='DJANGO_DATABASE_URL',
                value=os.getenv('DJANGO_DATABASE_URL_K8S', os.environ['DJANGO_DATABASE_URL']),
            ),
            client.V1EnvVar(
                name='DJANGO_CELERY_BROKER_URL',
                value=os.getenv(
                    'DJANGO_CELERY_BROKER_URL_K8S', os.environ['DJANGO_CELERY_BROKER_URL']
                ),
            ),
            client.V1EnvVar(
                name='DJANGO_MINIO_STORAGE_ENDPOINT',
                value=os.getenv(
                    'DJANGO_MINIO_STORAGE_ENDPOINT_K8S', os.environ['DJANGO_MINIO_STORAGE_ENDPOINT']
                ),
            ),
            #
            # Remain the same
            client.V1EnvVar(
                name='DJANGO_CONFIGURATION',
                value=os.environ['DJANGO_CONFIGURATION'],
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
            client.V1EnvVar(name='JOB_NAME', value=self.job_name),
            client.V1EnvVar(name='CONTAINER_NAME', value=self.main_container_name),
            client.V1EnvVar(name='TASK_ID', value=str(self.algorithm_task.pk)),
            client.V1EnvVar(name='TEMP_DIR', value=str(self.temp_path)),
        ]

    def _construct_job(self):
        from kubernetes import client, config

        # Load config from outside of k8s cluster
        config.load_kube_config()

        # Define volume mount
        volume_mount = client.V1VolumeMount(name='task-data', mount_path=str(self.temp_path))

        # Define main container
        main_container = client.V1Container(
            name=self.main_container_name,
            image=self.image_id,
            args=shlex.split(self.algorithm_task.algorithm.command),
            volume_mounts=[volume_mount],
            working_dir=str(self.temp_path),
            # resources=client.V1ResourceRequirements(limits={'nvidia.com/gpu': 1}),
        )

        # Container that will initialize the pod emptyDir with data
        init_container = client.V1Container(
            name=f'{self.main_container_name}--init',
            image='oasis-sidecar',
            volume_mounts=[volume_mount],
            image_pull_policy='Never',
            command=['/opt/django-project/manage.py'],
            args=['setup_container_k8s'],
            env=self._sidecar_container_env_vars(),
        )

        # Container that will monitor the main container and upload the resulting logs & data
        monitor_container = client.V1Container(
            name=f'{self.main_container_name}--monitor',
            image='oasis-sidecar',
            volume_mounts=[volume_mount],
            image_pull_policy='Never',
            env=self._sidecar_container_env_vars(),
        )

        # Define job template
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(name=self.job_name),
            spec=client.V1PodSpec(
                restart_policy='Never',
                init_containers=[init_container],
                containers=[monitor_container, main_container],
                volumes=[
                    client.V1Volume(
                        name='task-data',
                        empty_dir=client.V1EmptyDirVolumeSource(),
                    ),
                ],
                service_account_name='job-robot',
            ),
        )

        # Instantiate and return the job object
        return client.V1Job(
            api_version='batch/v1',
            kind='Job',
            metadata=client.V1ObjectMeta(name=self.job_name),
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
        from kubernetes import client, config

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
