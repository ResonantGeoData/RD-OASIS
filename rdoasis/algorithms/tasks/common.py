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
                existing_filenames.add(f)

        self.algorithm_task.output_dataset.add(*new_checksum_files)

    def _download_input_dataset(self):
        """Download the input dataset."""
        self.input_dataset_paths: List[Path] = []
        self.input_dataset_root_dir = Path(tempfile.mkdtemp())

        files: List[ChecksumFile] = list(self.algorithm.input_dataset.all())
        for checksum_file in files:
            self.input_dataset_paths.append(
                checksum_file.download_to_local_path(self.input_dataset_root_dir)
            )

    def _setup(self, **kwargs):
        # Set algorithm task and update status
        self.algorithm_task: AlgorithmTask = AlgorithmTask.objects.select_related('algorithm').get(
            pk=kwargs['algorithm_task_id']
        )
        self.algorithm_task.status = AlgorithmTask.Status.RUNNING
        self.algorithm_task.save()

        # Set algorithm
        self.algorithm: Algorithm = self.algorithm_task.algorithm

        # Ensure necessary files and directories exist
        self.output_dir = Path(tempfile.mkdtemp())
        self._download_input_dataset()

    def _cleanup(self):
        """Perform any necessary cleanup."""
        # Remove dirs
        shutil.rmtree(self.output_dir, ignore_errors=True)
        shutil.rmtree(self.input_dataset_root_dir, ignore_errors=True)

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

        self._cleanup()

    def __call__(self, **kwargs):
        self._setup(**kwargs)

        # Run task
        return self.run(**kwargs)
