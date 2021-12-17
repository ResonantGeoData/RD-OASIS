from pathlib import Path
import tempfile
import re
import os

import celery
from celery.utils.log import get_task_logger
from rdoasis.algorithms.models import Algorithm, AlgorithmTask


from rdoasis.algorithms.tasks.common import ManagedTask

logger = get_task_logger(__name__)


class ManagedK8sTask(ManagedTask):
    def _setup(self, **kwargs):
        # Set algorithm task and update status
        self.algorithm_task: AlgorithmTask = AlgorithmTask.objects.select_related(
            'algorithm', 'input_dataset', 'output_dataset'
        ).get(pk=kwargs['algorithm_task_id'])
        self.algorithm_task.status = AlgorithmTask.Status.RUNNING
        self.algorithm_task.save()

        # Set algorithm
        self.algorithm: Algorithm = self.algorithm_task.algorithm

        # Generate directory names
        # self._generate_directories()
        self._create_directories()

        # Ensure necessary files and directories exist
        # self._make_directories()

        # Download input
        # self._download_input_dataset()

    def _create_directories(self):
        # Create root dir
        self.root_dir = Path(tempfile.mkdtemp())

        # Create input and output dir
        self.input_dir = self.root_dir / 'input'
        self.output_dir = self.root_dir / 'output'

    def _cleanup(self):
        """Do nothing."""
        pass

    def _run_algorithm_task_k8s(self, *args, **kwargs):
        # Import kubernetes here so django can import task
        from kubernetes import config, client

        # Load config from outside of k8s cluster
        config.load_kube_config()

        api = client.BatchV1Api()
        job: client.V1Job = _construct_job(str(self.root_dir), self.algorithm_task)
        job: client.V1Job = api.create_namespaced_job(namespace='default', body=job)


def _construct_job(temp_path: str, alg_task: AlgorithmTask):
    from kubernetes import client, config

    # Load config from outside of k8s cluster
    config.load_kube_config()

    # Define volume
    volume = client.V1Volume(
        name='task-data',
        empty_dir=client.V1EmptyDirVolumeSource(),
    )

    pod_name = 'test'

    # Define container with volume mount
    image_id = alg_task.algorithm.docker_image.image_id
    args = alg_task.algorithm.command.split()
    main_container_name = re.sub(r'[^a-zA-Z\d-]', '-', image_id.lower())
    main_container = client.V1Container(
        name=main_container_name,
        image=image_id,
        args=args,
        volume_mounts=[client.V1VolumeMount(name='task-data', mount_path=temp_path)],
        working_dir=temp_path,
        # resources=client.V1ResourceRequirements(limits={'nvidia.com/gpu': 1}),
    )

    monitor_container = client.V1Container(
        name=f'{main_container_name}--monitor',
        image='oasis-sidecar',
        volume_mounts=[client.V1VolumeMount(name='task-data', mount_path=temp_path)],
        image_pull_policy='Never',
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
            client.V1EnvVar(name='POD_NAME', value=pod_name),
            client.V1EnvVar(name='CONTAINER_NAME', value=main_container_name),
            client.V1EnvVar(name='TASK_ID', value=f'"{alg_task.pk}"'),
            client.V1EnvVar(name='TEMP_DIR', value=temp_path),
        ]
        # resources=client.V1ResourceRequirements(limits={'nvidia.com/gpu': 1}),
    )

    # Define job template
    template = client.V1PodTemplateSpec(
        # metadata=client.V1ObjectMeta(labels={"name": "test"}),
        metadata=client.V1ObjectMeta(name=pod_name),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[main_container, monitor_container],
            volumes=[volume],
            service_account_name='job-robot',
            automount_service_account_token=False,
        ),
    )

    # Define the job
    spec = client.V1JobSpec(template=template, backoff_limit=0, ttl_seconds_after_finished=30)

    # Instantiate and return the job object
    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="test"),
        spec=spec,
    )


# def _run_algorithm_task_k8s(self: ManagedK8sTask, *args, **kwargs):
#     # Import kubernetes here so django can import task
#     from kubernetes import config, client

#     # Load config from outside of k8s cluster
#     config.load_kube_config()

#     api = client.BatchV1Api()
#     job: client.V1Job = _construct_job(str(self.root_dir), self.algorithm_task)
#     job: client.V1Job = api.create_namespaced_job(namespace='default', body=job)


@celery.shared_task(base=ManagedK8sTask, bind=True)
def run_algorithm_task_k8s(self: ManagedK8sTask, *args, **kwargs):
    """
    Run an algorithm task.

    Args:
        algorithm_task_id: The ID of the algorithm task to run.s

    Returns:
        The status code returned from docker.
    """
    return self._run_algorithm_task_k8s(*args, **kwargs)
