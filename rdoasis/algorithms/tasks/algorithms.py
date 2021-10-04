import celery

from rdoasis.algorithms.tasks.common import ManagedTask


@celery.shared_task(base=ManagedTask, bind=True)
def run_algorithm(self, *args, **kwargs):
    # Import docker here to django can import task without docker
    import docker
    from docker.types import DeviceRequest, Mount

    # Construct container arguments
    paths_to_mount = (self.output_dir, self.input_dataset_root_dir)
    mounts = [Mount(target=str(path), source=str(path), type='bind') for path in paths_to_mount]
    device_requests = [DeviceRequest(count=-1, capabilities=[['gpu']])]

    # TODO: Handle case when docker_image is uploaded (uses image_file field)
    # Instantiate docker client
    client = docker.from_env()
    output = client.containers.run(
        self.algorithm.docker_image.image_id,
        command=self.algorithm.command,
        mounts=mounts,
        device_requests=device_requests,
    )

    return output.decode('utf-8')
