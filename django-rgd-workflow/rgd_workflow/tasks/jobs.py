from typing import List

import os
from celery import shared_task

from rgd_workflow.models.workflow import WorkflowStep, WorkflowStepRun

from .common import ManagedTask
from .helpers import workflow_step_needs_to_run, workflow_step_ready_to_run

# @shared_task(time_limit=86400)
# def run_algorithm(algorithm_job_id, dry_run=False):
#     from .helpers import _run_algorithm

#     algorithm_job = AlgorithmJob.objects.get(pk=algorithm_job_id)
#     if not dry_run:
#         algorithm_job.status = AlgorithmJob.Status.RUNNING
#         algorithm_job.save(update_fields=['status'])
#     algorithm_job = _run_algorithm(algorithm_job)
#     if not dry_run:
#         algorithm_job.save()
#         # Notify


@shared_task(base=ManagedTask, time_limit=86400)
def run_workflow_step(workflow_step_run_id, **kwargs):
    data_path = kwargs['data_path']
    print('---', data_path)

    run: WorkflowStepRun = WorkflowStepRun.objects.select_related('workflow_step').get(
        pk=workflow_step_run_id
    )

    # TODO: Replace with implementation
    print(f'--------- RUN STEP {run.workflow_step.name} ---------')

    files = os.walk(data_path)
    print(files)


@shared_task(time_limit=86400)
def run_workflow(workflow_id: int):
    # Find all steps which have not run yet (have no successful runs)
    steps: List[WorkflowStep] = list(WorkflowStep.objects.filter(workflow__pk=workflow_id))
    required_steps = filter(workflow_step_needs_to_run, steps)
    ready_steps = filter(workflow_step_ready_to_run, required_steps)

    # Kick off all steps
    for step in ready_steps:
        new_run: WorkflowStepRun = WorkflowStepRun.objects.create(workflow_step=step)
        run_workflow_step.delay(workflow_step_run_id=new_run.pk)
