import pytest

from rdoasis.algorithms.models import Workflow, WorkflowStep


@pytest.mark.django_db
def test_workflow_add_root_step(workflow: Workflow, workflow_step_factory):
    # Create step
    workflow_step: WorkflowStep = workflow_step_factory(workflow=workflow)

    # Add step to workflow
    workflow.add_root_step(workflow_step)

    # Implicitly assert that this step exists
    WorkflowStep.objects.get(name=workflow_step.name, workflow=workflow)

    # Assert new step is in list of steps
    assert workflow.steps() == [workflow_step]


@pytest.mark.django_db
def test_workflow_step_append(workflow_step_factory, workflow):
    # Create steps
    step_1: WorkflowStep = workflow_step_factory(workflow=workflow)
    step_2: WorkflowStep = workflow_step_factory(workflow=workflow)
    step_3: WorkflowStep = workflow_step_factory(workflow=workflow)

    # Add steps to workflow
    workflow.add_root_step(step_1)
    step_1.append_step(step_2)
    step_2.append_step(step_3)

    # Make Assertions
    steps = workflow.steps()
    assert [step_1.pk, step_2.pk, step_3.pk] == [step.pk for step in steps]


@pytest.mark.django_db
def test_workflow_step_children(workflow_with_steps: Workflow):
    step_1, step_2, step_3 = workflow_with_steps.steps()
    step_children_pairs = [
        (step_1, [step_2, step_3]),
        (step_2, [step_3]),
        (step_3, []),
    ]

    for step, children in step_children_pairs:
        assert step.children() == children


@pytest.mark.django_db
def test_workflow_step_parents(workflow_with_steps: Workflow):
    step_1, step_2, step_3 = workflow_with_steps.steps()
    step_parents_pairs = [
        (step_1, []),
        (step_2, [step_1]),
        (step_3, [step_1, step_2]),
    ]

    for step, children in step_parents_pairs:
        assert step.parents() == children
