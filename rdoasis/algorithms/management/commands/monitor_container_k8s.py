import os
from pathlib import Path
import time
from typing import List, Optional, Set, Tuple

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from kubernetes import client, config
from rgd.models.file import ChecksumFile

from rdoasis.algorithms.models import AlgorithmTask, Dataset


try:
    config.load_incluster_config()
except config.config_exception.ConfigException:
    config.load_kube_config()

# Load envs
JOB_NAME = os.getenv('JOB_NAME')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')
TASK_ID = os.getenv('TASK_ID')
TEMP_DIR = os.getenv('TEMP_DIR', '')
if {None, ''} & {JOB_NAME, CONTAINER_NAME, TASK_ID, TEMP_DIR}:
    raise Exception('Not all env vars specified.')


coreapi = client.CoreV1Api()


def get_pod_name() -> str:
    pods: client.V1PodList = coreapi.list_namespaced_pod(
        namespace='default', label_selector=f'job-name={JOB_NAME}'
    )
    pod = pods.items[0]  # type: ignore
    return pod.metadata.name


def poll_container(pod_name: str) -> Tuple[Optional[client.V1ContainerStateTerminated], str]:
    pod: client.V1Pod = coreapi.read_namespaced_pod_status(name=pod_name, namespace='default')

    log = ''
    running_state = None
    termination_state = None
    try:
        container: client.V1ContainerStatus = next(
            c for c in pod.status.container_statuses if c.name == CONTAINER_NAME  # type: ignore
        )

        termination_state = container.state.terminated  # type: ignore
        running_state = container.state.running  # type: ignore
        if running_state or termination_state:
            log = coreapi.read_namespaced_pod_log(
                name=pod_name, container=CONTAINER_NAME, namespace='default'
            )
    except (AttributeError, StopIteration):
        pass

    return termination_state, log


def upload_result_files(alg_task: AlgorithmTask, input_dir: Path, output_dir: Path):
    """Upload any new files to the output dataset."""
    new_checksum_files: List[ChecksumFile] = []
    existing_filenames: Set[str] = {file.name for file in alg_task.input_dataset.files.all()}
    for path, _, files in os.walk(output_dir):
        fixed_filenames = {os.path.join(path, file) for file in files}
        new_filenames = fixed_filenames - existing_filenames

        for f in new_filenames:
            relative_filename = Path(f).relative_to(output_dir)
            checksum_file = ChecksumFile(name=relative_filename)

            with open(f, 'rb') as file_contents:
                checksum_file.file = SimpleUploadedFile(
                    name=str(relative_filename), content=file_contents.read()
                )

            checksum_file.save()
            new_checksum_files.append(checksum_file)
            existing_filenames.add(f)

    alg_task.output_dataset.files.add(*new_checksum_files)


class Command(BaseCommand):
    help = 'Monitor a K8s container and return files, status, etc.'

    def handle(self, *args, **options):
        # TODO: use post_start lifecycle hook to build local image if necessary
        log: str = ''
        termination_state = None

        pod_name = get_pod_name()
        alg_task: AlgorithmTask = AlgorithmTask.objects.get(pk=TASK_ID)
        while termination_state is None:
            termination_state, log = poll_container(pod_name)
            if log:
                alg_task.output_log = log
                alg_task.save()

            # Wait at least 1 second
            time.sleep(1)

        # Main container has finished, save status, upload files, etc.
        success = termination_state.exit_code == 0
        alg_task.status = AlgorithmTask.Status.SUCCEEDED if success else AlgorithmTask.Status.FAILED
        alg_task.save()

        temp_path = Path(TEMP_DIR)
        input_path = temp_path / 'input'
        output_path = temp_path / 'output'

        alg_task.output_dataset = Dataset.objects.create(
            name=f'Algorithm {alg_task.algorithm.pk}, Task {alg_task.pk} (Output)'
        )
        upload_result_files(alg_task, input_dir=input_path, output_dir=output_path)
        alg_task.save()
