import os
from typing import List
import celery
from pathlib import Path
import subprocess

from rgd.models import Collection
from rgd.models.common import ChecksumFile, FileSourceType

from rgd_workflow.models.workflow import Workflow, WorkflowStep, WorkflowStepRun
from .helpers import (
    get_workflow_collection_mount_point,
    minio_storage_url,
    s3_or_minio_bucket_name,
    s3_or_minio_credentials,
)


class ManagedTask(celery.Task):
    def _runnable_child_steps(self):
        """
        Return the steps which can be run next.

        For each child step, check that all parent steps have completed successfully.
        This necessarily includes a redundnat check of this step.
        """
        child_steps = self.workflow_step.children(depth=1)
        runnable_steps = [
            step
            for step in child_steps
            if all([parent.completed for parent in step.parents(depth=1)])
        ]

        return runnable_steps

    def _ensure_credentials_file(self):
        file = Path('/etc/passwd-s3fs')
        if file.exists():
            return

        # Write credentials to file
        with open(file, 'w') as out_file:
            key, secret = s3_or_minio_credentials()
            out_file.write(f'{key}:{secret}\n')

        # Update file permissions
        os.chmod(file, 0o600)

    def _mount_workflow_collection(self) -> str:
        """Mount the workflow collection and return the mount point."""
        self._ensure_credentials_file()

        workflow: Workflow = self.workflow_step.workflow
        collection: Collection = workflow.collection
        files: List[ChecksumFile] = list(ChecksumFile.objects.filter(collection=collection))

        # Ensure base mount point exists
        base_mount_point = Path(get_workflow_collection_mount_point(workflow))
        if not base_mount_point.is_dir():
            base_mount_point.mkdir()

        # Mount each file individually
        s3_files = [file for file in files if file.type == FileSourceType.FILE_FIELD]
        for file in s3_files:
            file_path = Path(file.name)
            parent_dir = file_path.parent
            parent_dir_mount_point = base_mount_point / parent_dir

            # TODO: Fix crash on call to is_dir
            # Multiple files may share this parent dir
            # parent_dir_mount_point.mkdir(parents=True, exist_ok=True)
            if not parent_dir_mount_point.exists():
                parent_dir_mount_point.mkdir(parents=True)

            # Mount parent dir, so child file is visible under it
            bucket_param = s3_or_minio_bucket_name()
            # if parent_dir_mount_point != base_mount_point / '.':
            #     bucket_param += f':/{parent_dir}'

            s3fs_commands = [
                's3fs',
                # '-o',
                # 'retries=5',
                bucket_param,
                str(parent_dir_mount_point),
                '-o',
                'passwd_file=/etc/passwd-s3fs',
                # '-o',
                # 'allow_other',
            ]

            # Handle custom URL if using MinIO
            storage_url = minio_storage_url()
            if storage_url is not None:
                s3fs_commands.extend(
                    [
                        '-o',
                        f'url={storage_url}',
                        # '-o',
                        # 'use_path_request_style',
                    ]
                )

            print('#####', s3fs_commands)

            # Run mount command
            subprocess.run(s3fs_commands, check=True)

        return base_mount_point

    def _unmount_workflow_collection(self):
        """Unmount the workflow collection from the filesystem."""
        # TODO: Implement

    def _upload_result_files(self):
        """Upload any new files to the workflow collection, and unmount."""
        # TODO: Scan mount point for files, and upload to collection

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self.workflow_step_run.status = WorkflowStepRun.Status.FAILED
        self.workflow_step_run.save()

        self._unmount_workflow_collection()

    def on_success(self, retval, task_id, args, kwargs):
        self._upload_result_files()

        # # Mark workflow step run as succeeded
        # self.workflow_step_run.status = WorkflowStepRun.Status.SUCCEEDED
        # self.workflow_step_run.save()

        next_steps = self._runnable_child_steps()
        if next_steps:
            # TODO: Call run_workflow_step on each next step
            pass
        else:
            self._unmount_workflow_collection()

    def __call__(self, *args, **kwargs):
        # Set run on task instance
        self.workflow_step_run: WorkflowStepRun = WorkflowStepRun.objects.select_related(
            'workflow_step'
        ).get(pk=kwargs['workflow_step_run_id'])

        # Set run status
        self.workflow_step_run.status = WorkflowStepRun.Status.RUNNING
        self.workflow_step_run.save()

        # Set step on task instance
        self.workflow_step: WorkflowStep = self.workflow_step_run.workflow_step

        # Mount collection
        self.mount_point = self._mount_workflow_collection()

        # Run task
        return self.run(*args, **kwargs, data_path=self.mount_point)
