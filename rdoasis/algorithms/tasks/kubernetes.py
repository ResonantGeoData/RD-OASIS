import celery
from celery.utils.log import get_task_logger
from rdoasis.algorithms.models import Algorithm, AlgorithmTask


from rdoasis.algorithms.tasks.common import ManagedTask

logger = get_task_logger(__name__)


class ManagedK8sTask(ManagedTask):
    def create_k8s_volume(self):
        """Create a volume before directories are created."""
        from kubernetes import config, client

        # Load config from within k8s cluster
        config.load_incluster_config()

        coreapi = client.CoreV1Api()
        coreapi.create_persistent_volume(
            client.V1PersistentVolume(
                spec=client.V1PersistentVolumeSpec(
                    host_path=client.V1HostPathVolumeSource(
                        path=str(self.root_dir), type='DirectoryOrCreate'
                    ),
                    access_modes=['ReadWriteOnce'],
                    capacity={'storage': '5Gi'},
                ),
                metadata=client.V1ObjectMeta(name='volume'),
            )
        )

    def delete_k8s_volume(self):
        """Delete a volume after job is finished."""
        from kubernetes import config, client

        # Load config from within k8s cluster
        config.load_incluster_config()

        coreapi = client.CoreV1Api()
        coreapi.delete_persistent_volume(name='volume')

    def _setup(self, **kwargs):
        # Set algorithm task and update status
        self.algorithm_task: AlgorithmTask = AlgorithmTask.objects.select_related(
            'algorithm', 'input_dataset', 'output_dataset'
        ).get(pk=kwargs['algorithm_task_id'])
        self.algorithm_task.status = AlgorithmTask.Status.RUNNING
        self.algorithm_task.save()

        # Set algorithm
        self.algorithm: Algorithm = self.algorithm_task.algorithm

        # Ensure necessary files and directories exist
        self._create_directories()

        # Create volume at self.root_dir
        self.create_k8s_volume()

        # Download input
        self._download_input_dataset()

    def on_failure(self, *args, **kwargs):
        res = super().on_failure(*args, **kwargs)

        self.delete_k8s_volume()
        return res

    def on_success(self, *args, **kwargs):
        res = super().on_success(*args, **kwargs)

        self.delete_k8s_volume()
        return res


def _construct_job(temp_path: str):
    from kubernetes import client

    # Define volume
    volume = client.V1Volume(
        name='task-data',
        host_path=client.V1HostPathVolumeSource(path=temp_path, type='DirectoryOrCreate'),
    )

    # Define container with volume mount
    container = client.V1Container(
        name="busybox",
        image="busybox",
        args=["ls", temp_path],
        volume_mounts=[client.V1VolumeMount(name='task-data', mount_path=temp_path)],
    )

    # Define job template
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"name": "test"}),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=[volume],
        ),
    )

    # Define the job
    spec = client.V1JobSpec(template=template, ttl_seconds_after_finished=10)

    # Instantiate and return the job object
    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name="test"),
        spec=spec,
    )


def _run_algorithm_task_k8s(self: ManagedK8sTask, *args, **kwargs):
    # Import kubernetes here so django can import task
    from kubernetes import config, client

    # Load config from within k8s cluster
    config.load_incluster_config()

    # Below shows how you might access the pod this is running from, to run another container
    # within this pod
    # from kubernetes.client.models.v1_pod import V1Pod
    # this_pod: V1Pod = client.CoreV1Api().read_namespaced_pod(
    #     name='oasis-worker',
    #     namespace='default',
    # )

    api = client.BatchV1Api()
    job: client.V1Job = _construct_job(str(self.root_dir))
    job: client.V1Job = api.create_namespaced_job(namespace='default', body=job)

    while not job.status.active:
        job: client.V1Job = api.read_namespaced_job_status(name='test', namespace='default')

    # device_requests = []
    # if self.algorithm.gpu:
    #     device_requests.append(DeviceRequest(count=-1, capabilities=[['gpu']]))

    # # Instantiate docker client
    # client = docker.from_env()

    # Get or pull image
    # image_id = self.docker_image_file_id or self.algorithm.docker_image.image_id
    # try:
    #     image = client.images.get(image_id)
    # except ImageNotFound:
    #     logger.info(f'Pulling {image_id}. This may take a while...')
    #     image = client.images.pull(image_id)

    # Run container
    # try:
    #     container: Container = client.containers.run(
    #         image,
    #         command=self.algorithm.command,
    #         entrypoint=self.algorithm.entrypoint,
    #         environment=self.algorithm.environment,
    #         mounts=mounts,
    #         device_requests=device_requests,
    #         working_dir=str(self.root_dir),
    #         detach=True,
    #     )
    # except DockerException as e:
    #     # Replace null characters with �
    #     self.algorithm_task.output_log = str(e).replace('\x00', '\uFFFD')
    #     self.algorithm_task.save()
    #     return e.status_code

    # Capture live logs
    # self.algorithm_task.output_log = ''
    # output_generator = container.logs(stream=True)
    # for log in output_generator:
    #     # TODO: Probably inefficient, fix

    #     # Replace null characters with �
    #     self.algorithm_task.output_log += log.decode('utf-8').replace('\x00', '\uFFFD')
    #     self.algorithm_task.save(update_fields=['output_log'])

    # # Wait for container to exit and remove
    # res = container.wait()
    # container.remove()

    # # Return status code
    # return res['StatusCode']


@celery.shared_task(base=ManagedK8sTask, bind=True)
def run_algorithm_task_k8s(self: ManagedK8sTask, *args, **kwargs):
    """
    Run an algorithm task.

    Args:
        algorithm_task_id: The ID of the algorithm task to run.s

    Returns:
        The status code returned from docker.
    """
    return _run_algorithm_task_k8s(self, *args, **kwargs)
