import celery
from celery.utils.log import get_task_logger

from rdoasis.algorithms.tasks.common import ManagedTask

logger = get_task_logger(__name__)


@celery.shared_task(base=ManagedTask, bind=True)
def run_algorithm_task(self: ManagedTask, *args, **kwargs):
    """
    Run an algorithm task.

    Args:
        algorithm_task_id: The ID of the algorithm task to run.s

    Returns:
        The status code returned from docker.
    """
    # Import docker here to django can import task without docker
    import docker
    from docker.errors import DockerException, ImageNotFound
    from docker.models.containers import Container
    from docker.types import DeviceRequest, Mount

    # Construct container arguments
    paths_to_mount = (self.input_dir, self.output_dir)
    mounts = [Mount(target=str(path), source=str(path), type='bind') for path in paths_to_mount]

    device_requests = []
    if self.algorithm.gpu:
        device_requests.append(DeviceRequest(count=-1, capabilities=[['gpu']]))

    # Instantiate docker client
    client = docker.from_env()

    # Get or pull image
    image_id = self.algorithm.docker_image.image_id
    try:
        image = client.images.get(image_id)
    except ImageNotFound:
        logger.info(f'Pulling {image_id}. This may take a while...')
        image = client.images.pull(image_id)

    # Run container
    try:
        container: Container = client.containers.run(
            image,
            command=self.algorithm.command,
            entrypoint=self.algorithm.entrypoint,
            environment=self.algorithm.environment,
            mounts=mounts,
            device_requests=device_requests,
            working_dir=str(self.root_dir),
            detach=True,
        )
    except DockerException as e:
        # Replace null characters with �
        self.algorithm_task.output_log = str(e).replace('\x00', '\uFFFD')
        self.algorithm_task.save()
        return e.status_code

    # Capture live logs
    self.algorithm_task.output_log = ''
    output_generator = container.logs(stream=True)
    for log in output_generator:
        # TODO: Probably inefficient, fix

        # Replace null characters with �
        self.algorithm_task.output_log += log.decode('utf-8').replace('\x00', '\uFFFD')
        self.algorithm_task.save(update_fields=['output_log'])

    # Wait for container to exit and remove
    res = container.wait()
    container.remove()

    # Return status code
    return res['StatusCode']
