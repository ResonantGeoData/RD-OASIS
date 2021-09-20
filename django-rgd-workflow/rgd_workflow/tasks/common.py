import celery

from rgd_workflow.models.workflow import WorkflowStep, WorkflowStepRun


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

    def _mount_workflow_collection(self) -> str:
        """Mount the workflow collection and return the mount point."""
        # TODO: Implement
        return ''

    def _unmount_workflow_collection(self):
        """Unmount the workflow collection from the filesystem."""
        # TODO: Implement

    def _upload_result_files(self):
        """Upload any new files to the workflow collection, and unmount."""
        # TODO: Scan mount point for files, and upload to collection

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # TODO: Mark workflow step run as failed
        self._unmount_workflow_collection()
        return super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        self._upload_result_files()

        # TODO: Mark workflow step run as succeeded
        next_steps = self._runnable_child_steps()
        if next_steps:
            # TODO: Call run_workflow_step on each next step
            pass
        else:
            self._unmount_workflow_collection()

        return super().on_success(retval, task_id, args, kwargs)

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
