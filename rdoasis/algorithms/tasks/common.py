from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile
from typing import List, Set

from billiard.einfo import ExceptionInfo
import celery
from django.core.files.uploadedfile import SimpleUploadedFile
from rgd.models.common import ChecksumFile

from rdoasis.algorithms.models import Algorithm, AlgorithmTask


@dataclass
class AlgorithmTaskData:
    algorithm: Algorithm
    algorithm_task: AlgorithmTask
    output_dir: str
    input_dataset_root_dir: str
    input_dataset_paths: List[str]


class ManagedTask(celery.Task):
    def _upload_result_files(self):
        """Upload any new files to the output dataset."""
        new_checksum_files: List[ChecksumFile] = []
        existing_filenames: Set[str] = {file.name for file in self.algorithm.input_dataset.all()}
        for path, _, files in os.walk(self.output_dir):
            fixed_filenames = {os.path.join(path, file) for file in files}
            new_filenames = fixed_filenames - existing_filenames

            for f in new_filenames:
                relative_filename = Path(f).relative_to(self.output_dir)
                checksum_file = ChecksumFile(name=relative_filename)

                with open(f, 'rb') as file_contents:
                    checksum_file.file = SimpleUploadedFile(
                        name=relative_filename, content=file_contents.read()
                    )

                checksum_file.save()
                new_checksum_files.append(checksum_file)

            existing_filenames.update(new_filenames)

        self.algorithm_task.output_dataset.add(*new_checksum_files)

    def _download_input_dataset(self):
        """Download the input dataset."""
        self.input_dataset_paths = []
        self.input_dataset_root_dir = tempfile.mkdtemp()

        files: List[ChecksumFile] = list(self.algorithm.input_dataset.all())
        for checksum_file in files:
            fd, path = tempfile.mkstemp(dir=self.input_dataset_root_dir)
            self.input_dataset_paths.append(path)

            with os.fdopen(fd, 'wb') as file_in:
                shutil.copyfileobj(checksum_file.file, file_in)
                file_in.flush()

    def _cleanup(self):
        """Perform any necessary cleanup."""
        # Remove dirs
        shutil.rmtree(self.output_dir, ignore_errors=True)
        shutil.rmtree(self.input_dataset_root_dir, ignore_errors=True)

        # TODO: Remove any individual files if necessary

    def on_failure(self, exc, task_id, args, kwargs, einfo: ExceptionInfo):
        self.algorithm_task.status = AlgorithmTask.Status.FAILED
        self.algorithm_task.output_log = einfo.traceback
        self.algorithm_task.save()

        self._cleanup()

    def on_success(self, retval, task_id, args, kwargs):
        self._upload_result_files()

        # Mark algorithm task as succeeded and save logs
        self.algorithm_task.status = AlgorithmTask.Status.SUCCEEDED
        self.algorithm_task.output_log = retval
        self.algorithm_task.save()

        # Cleanup
        self._cleanup()

    def __call__(self, **kwargs):
        # Set algorithm and task on task instance
        self.algorithm_task: AlgorithmTask = AlgorithmTask.objects.select_related('algorithm').get(
            pk=kwargs['algorithm_task_id']
        )
        self.algorithm: Algorithm = self.algorithm_task.algorithm

        # Set run status
        self.algorithm_task.status = AlgorithmTask.Status.RUNNING
        self.algorithm_task.save()

        # Ensure necessary files and directories exist
        self.output_dir = Path(tempfile.mkdtemp())
        self._download_input_dataset()

        # Construct data
        data = AlgorithmTaskData(
            algorithm=self.algorithm,
            algorithm_task=self.algorithm_task,
            output_dir=self.output_dir,
            input_dataset_root_dir=self.input_dataset_root_dir,
            input_dataset_paths=self.input_dataset_paths,
        )

        # Run task
        return self.run(data=data, **kwargs)
