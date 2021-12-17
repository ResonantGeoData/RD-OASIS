import os
from pathlib import Path
import time

from typing import List, Optional, Set, Tuple, Union

from django.core.files.uploadedfile import SimpleUploadedFile
from kubernetes import client, config
from rgd.models.file import ChecksumFile

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, Dataset


try:
    config.load_incluster_config()
except config.config_exception.ConfigException:
    config.load_kube_config()


coreapi = client.CoreV1Api()

InProgressStateAndLog = Tuple[Optional[client.V1ContainerStateTerminated], str]
FinalStateAndLog = Tuple[client.V1ContainerStateTerminated, str]


class KubernetesContainerMonitor:
    """
    A class that handles the setup and monitoring of a managed container.

    This class should only be instantiated within the same pod as the managed container.
    """

    @staticmethod
    def from_env():
        JOB_NAME = os.getenv('JOB_NAME', '')
        CONTAINER_NAME = os.getenv('CONTAINER_NAME', '')
        TASK_ID = os.getenv('TASK_ID', '')
        TEMP_DIR = os.getenv('TEMP_DIR', '')

        if '' in {JOB_NAME, CONTAINER_NAME, TASK_ID, TEMP_DIR}:
            raise Exception('Not all env vars specified.')

        return KubernetesContainerMonitor(
            job_name=JOB_NAME,
            container_name=CONTAINER_NAME,
            task_id=TASK_ID,
            temp_dir=TEMP_DIR,
        )

    def __init__(
        self,
        job_name: str,
        container_name: str,
        task_id: Union[str, int],
        temp_dir: str,
    ) -> None:
        self.job_name = job_name
        self.container_name = container_name
        self.task_id = task_id if isinstance(task_id, int) else int(task_id)
        self.temp_dir = Path(temp_dir)

        # Derived variables
        self.algorithm_task: AlgorithmTask = AlgorithmTask.objects.select_related(
            'algorithm', 'input_dataset', 'output_dataset'
        ).get(pk=self.task_id)
        self.algorithm: Algorithm = self.algorithm_task.algorithm

        # Fetch pod
        self.pod_name = self.get_main_pod_name()

    def ensure_directories(self):
        self.input_dir = self.temp_dir / 'input'
        self.input_dir.mkdir(parents=True, exist_ok=True)

        self.output_dir = self.temp_dir / 'output'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_input_dataset(self):
        self.ensure_directories()

        # Download dataset
        files: List[ChecksumFile] = list(self.algorithm_task.input_dataset.files.all())
        for checksum_file in files:
            checksum_file.download_to_local_path(str(self.input_dir))

    def get_main_pod_name(self) -> str:
        pods: client.V1PodList = coreapi.list_namespaced_pod(
            namespace='default', label_selector=f'job-name={self.job_name}'
        )
        pod = pods.items[0]  # type: ignore
        return pod.metadata.name

    def poll_container(self) -> InProgressStateAndLog:
        pod: client.V1Pod = coreapi.read_namespaced_pod_status(
            name=self.pod_name, namespace='default'
        )

        log = ''
        running_state = None
        termination_state = None
        try:
            container: client.V1ContainerStatus = next(
                c
                for c in pod.status.container_statuses  # type: ignore
                if c.name == self.container_name
            )

            termination_state = container.state.terminated  # type: ignore
            running_state = container.state.running  # type: ignore
            if running_state or termination_state:
                log = coreapi.read_namespaced_pod_log(
                    name=self.pod_name,
                    container=self.container_name,
                    namespace='default',
                )
        except (AttributeError, StopIteration):
            pass

        return termination_state, log

    def upload_result_files(self):
        """Upload any new files to the output dataset."""
        new_checksum_files: List[ChecksumFile] = []
        existing_filenames: Set[str] = {
            file.name for file in self.algorithm_task.input_dataset.files.all()
        }
        for path, _, files in os.walk(self.output_dir):
            fixed_filenames = {os.path.join(path, file) for file in files}
            new_filenames = fixed_filenames - existing_filenames

            for f in new_filenames:
                relative_filename = Path(f).relative_to(self.output_dir)
                checksum_file = ChecksumFile(name=relative_filename)

                with open(f, 'rb') as file_contents:
                    checksum_file.file = SimpleUploadedFile(
                        name=str(relative_filename), content=file_contents.read()
                    )

                checksum_file.save()
                new_checksum_files.append(checksum_file)
                existing_filenames.add(f)

        self.algorithm_task.output_dataset.files.add(*new_checksum_files)

    def container_result(self) -> FinalStateAndLog:
        log: str = ''
        termination_state = None
        while termination_state is None:
            termination_state, log = self.poll_container()
            if log:
                self.algorithm_task.output_log = log
                self.algorithm_task.save()

            # Wait at least 1 second
            time.sleep(1)

        return termination_state, log

    def monitor_container(self):
        termination_state, log = self.container_result()

        # Update task
        self.algorithm_task.output_log = log
        self.algorithm_task.status = (
            AlgorithmTask.Status.SUCCEEDED
            if termination_state.exit_code == 0
            else AlgorithmTask.Status.FAILED
        )
        self.algorithm_task.output_dataset = Dataset.objects.create(
            name=f'Algorithm {self.algorithm.pk}, Task {self.algorithm_task.pk} (Output)'
        )
        self.algorithm_task.save()

        # Upload results
        self.upload_result_files()
