from typing import List

import pytest

from rdoasis.algorithms.models import Workflow, WorkflowStep
from rdoasis.algorithms.models.workflow import WorkflowStepDependency


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
def test_workflow_step_distance(workflow_with_steps: Workflow):
    """Test that WorkflowDependency.distance is used correctly."""

    step_1, step_2, step_3 = workflow_with_steps.steps()

    # The distances between each step
    step_distances = [
        (step_1, step_1, 0),
        (step_1, step_2, 1),
        (step_2, step_2, 0),
        (step_1, step_3, 2),
        (step_2, step_3, 1),
        (step_3, step_3, 0),
    ]

    # Make implicit assertions by attempting to retrieve each link
    for parent, child, distance in step_distances:
        WorkflowStepDependency.objects.get(parent=parent, child=child, distance=distance)


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
def test_workflow_step_children_depth(workflow_with_steps: Workflow):
    step_1, step_2, step_3 = workflow_with_steps.steps()
    step_children_pairs = [
        (step_1, None, [step_2, step_3]),
        (step_1, 2, [step_2, step_3]),
        (step_1, 1, [step_2]),
        (step_1, 0, []),
        (step_2, None, [step_3]),
        (step_2, 1, [step_3]),
        (step_2, 0, []),
        (step_3, None, []),
        (step_3, 0, []),
    ]

    for step, depth, children in step_children_pairs:
        assert step.children(depth) == children


@pytest.mark.django_db
def test_workflow_step_parents(workflow_with_steps: Workflow):
    step_1, step_2, step_3 = workflow_with_steps.steps()
    step_parents_pairs = [
        (step_1, []),
        (step_2, [step_1]),
        (step_3, [step_2, step_1]),
    ]

    for step, children in step_parents_pairs:
        assert step.parents() == children


@pytest.mark.django_db
def test_workflow_step_parents_depth(workflow_with_steps: Workflow):
    step_1, step_2, step_3 = workflow_with_steps.steps()
    step_parents_pairs = [
        (step_1, None, []),
        (step_1, 0, []),
        (step_2, None, [step_1]),
        (step_2, 1, [step_1]),
        (step_2, 0, []),
        (step_3, None, [step_2, step_1]),
        (step_3, 2, [step_2, step_1]),
        (step_3, 1, [step_2]),
        (step_3, 0, []),
    ]

    for step, depth, children in step_parents_pairs:
        assert step.parents(depth) == children


@pytest.mark.django_db
def test_workflow_step_graph_ordering(workflow_with_steps: Workflow, workflow_step_factory):
    """
    Test that organizing a workflow as a graph behaves as we expect.

    The graph being tested has the following structure:

                 1
                / \
               2   4
              / \ / \   # noqa
             3   5   6
    """
    step_1, step_2, step_3 = workflow_with_steps.steps()
    step_4: WorkflowStep = workflow_step_factory(workflow=workflow_with_steps)
    step_5: WorkflowStep = workflow_step_factory(workflow=workflow_with_steps)
    step_6: WorkflowStep = workflow_step_factory(workflow=workflow_with_steps)

    step_1.append_step(step_4)
    step_2.append_step(step_5)
    step_4.append_step(step_5)
    step_4.append_step(step_6)

    #####################################
    # Assert step ordering (BFS ordering)
    #####################################
    all_steps: List[WorkflowStep] = workflow_with_steps.steps()

    # Assert first "row" is just step 1
    assert all_steps[0] == step_1

    # Assert second "row" contains steps 2 and 4 (ignoring order)
    assert all_steps[1:3] == [step_2, step_4]

    # Assert third "row" contains steps 3, 5 and 6 (ignoring order)
    assert all_steps[3:] == [step_3, step_5, step_6]


@pytest.mark.django_db
def test_workflow_graph_children(workflow_graph_steps: Workflow):
    step_1, step_2, step_4, step_3, step_5, step_6 = workflow_graph_steps.steps()
    step_1_children = step_1.children()

    # Assert step 1 children (by row)
    assert step_1_children[:2] == [step_2, step_4]
    assert step_1_children[2:] == [step_3, step_5, step_6]

    # Assert step 2 and 4 children
    assert step_2.children() == [step_3, step_5]
    assert step_4.children() == [step_5, step_6]

    # Assert step 3, 5 and 6 children
    leaf_child_sets = [step_3.children(), step_5.children(), step_6.children()]
    assert all(children == [] for children in leaf_child_sets)


@pytest.mark.django_db
def test_workflow_graph_parents(workflow_graph_steps: Workflow):
    step_1, step_2, step_4, step_3, step_5, step_6 = workflow_graph_steps.steps()

    # Assert leaf node parents
    assert step_6.parents() == [step_4, step_1]
    assert step_5.parents() == [step_2, step_4, step_1]
    assert step_3.parents() == [step_2, step_1]

    # Assert internal node parents
    assert step_2.parents() == [step_1]
    assert step_4.parents() == [step_1]

    # Assert root step parents
    assert step_1.parents() == []
