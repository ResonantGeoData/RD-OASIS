import os
from pathlib import Path
from typing import List

from django.core.management.base import BaseCommand

# from kubernetes import client, config
from rgd.models.file import ChecksumFile

from rdoasis.algorithms.models import AlgorithmTask


# try:
#     config.load_incluster_config()
# except config.config_exception.ConfigException:
#     config.load_kube_config()

# Load envs
JOB_NAME = os.getenv('JOB_NAME')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')
TASK_ID = os.getenv('TASK_ID')
TEMP_DIR = os.getenv('TEMP_DIR', '')
if {None, ''} & {JOB_NAME, CONTAINER_NAME, TASK_ID, TEMP_DIR}:
    raise Exception('Not all env vars specified.')


class Command(BaseCommand):
    help = 'Monitor a K8s container and return files, status, etc.'

    def handle(self, *args, **options):
        alg_task: AlgorithmTask = AlgorithmTask.objects.get(pk=TASK_ID)

        # Already exists
        root_dir = Path(TEMP_DIR)
        # root_dir.mkdir()

        # Create input dir
        input_dir = root_dir / 'input'
        input_dir.mkdir()

        # Create output dir
        output_dir = root_dir / 'output'
        output_dir.mkdir()

        files: List[ChecksumFile] = list(alg_task.input_dataset.files.all())
        for checksum_file in files:
            checksum_file.download_to_local_path(str(input_dir))
