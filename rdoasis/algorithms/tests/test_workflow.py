from typing import List

from django.core.exceptions import ValidationError
from django.db import models
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
@pytest.mark.parametrize(
    'parent_indexes, children_indexes',
    [
        ([0], [5]),
        ([2], [5]),
        ([3, 4, 5], []),
        ([2, 3], []),
    ],
)
def test_workflow_insert_step_graph(
    workflow_graph_steps: Workflow, workflow_step_factory, parent_indexes, children_indexes
):
    steps = workflow_graph_steps.steps()
    parents = [steps[i] for i in parent_indexes]
    children = [steps[i] for i in children_indexes]

    # Collect links that will have an updated distance after insertion
    affected_links: List[WorkflowStepDependency] = list(
        WorkflowStepDependency.objects.filter(parent__in=parents, child__in=children)
    )

    new_step: WorkflowStep = workflow_step_factory(workflow=workflow_graph_steps)
    workflow_graph_steps.insert_step(new_step, parents=parents, children=children)

    for parent in parents:
        assert new_step in parent.children()
        assert parent in new_step.parents()

    for child in children:
        assert new_step in child.parents()
        assert child in new_step.children()

    for link in affected_links:
        assert WorkflowStepDependency.objects.get(pk=link.pk).distance == link.distance + 1


@pytest.mark.django_db
def test_workflow_insert_step_linear(workflow_with_steps: Workflow, workflow_step_factory):
    steps = workflow_with_steps.steps()
    step_1, step_2, step_3 = steps

    # Observe links before insertion
    step_1_step_2_link = WorkflowStepDependency.objects.get(parent=step_1, child=step_2)
    step_1_step_3_link = WorkflowStepDependency.objects.get(parent=step_1, child=step_3)
    step_2_step_3_link = WorkflowStepDependency.objects.get(parent=step_2, child=step_3)

    assert step_1_step_2_link.distance == 1
    assert step_1_step_3_link.distance == 2
    assert step_2_step_3_link.distance == 1

    # Insert step between step 1 and step 2
    step_4 = workflow_step_factory(workflow=workflow_with_steps)
    workflow_with_steps.insert_step(step_4, parents=[step_1], children=[step_2])

    # Assert order
    assert workflow_with_steps.steps() == [step_1, step_4, step_2, step_3]

    assert step_1.children() == [step_4, step_2, step_3]
    assert step_1.parents() == []

    assert step_4.children() == [step_2, step_3]
    assert step_4.parents() == [step_1]

    assert step_2.children() == [step_3]
    assert step_2.parents() == [step_4, step_1]

    assert step_3.children() == []
    assert step_3.parents() == [step_2, step_4, step_1]

    # Observe links after insertion
    new_step_1_step_2_link = WorkflowStepDependency.objects.get(parent=step_1, child=step_2)
    new_step_1_step_3_link = WorkflowStepDependency.objects.get(parent=step_1, child=step_3)
    new_step_2_step_3_link = WorkflowStepDependency.objects.get(parent=step_2, child=step_3)

    assert new_step_1_step_2_link.distance == step_1_step_2_link.distance + 1
    assert new_step_1_step_3_link.distance == step_1_step_3_link.distance + 1
    assert new_step_2_step_3_link.distance == step_2_step_3_link.distance

    # Observe new links
    step_1_step_4_link = WorkflowStepDependency.objects.get(parent=step_1, child=step_4)
    step_4_step_2_link = WorkflowStepDependency.objects.get(parent=step_4, child=step_2)
    step_4_step_3_link = WorkflowStepDependency.objects.get(parent=step_4, child=step_3)

    assert step_1_step_4_link.distance == 1
    assert step_4_step_2_link.distance == 1
    assert step_4_step_3_link.distance == 2


# @pytest.mark.django_db
# def test_workflow_insert_step_existing(workflow_graph_steps: Workflow):
#     step_1, _, _, _, step_5, step_6 = workflow_graph_steps.steps()

#     # Ensure inserting an existing workflow step fails
#     with pytest.raises(ValidationError):
#         workflow_graph_steps.insert_step(step_5, parents=[step_1], children=[step_6])


@pytest.mark.django_db
def test_workflow_insert_step_circular(workflow_graph_steps: Workflow, workflow_step_factory):
    """Test that inserting a step in a circularly dependent way fails."""
    step_1, step_2, step_4, step_3, step_5, step_6 = workflow_graph_steps.steps()

    # Ensure inserting an existing workflow step fails
    new_step = workflow_step_factory(workflow=workflow_graph_steps)
    with pytest.raises(ValidationError):
        workflow_graph_steps.insert_step(new_step, parents=[step_6], children=[step_4])


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
@pytest.mark.parametrize('step_index', [0, 1, 2])
def test_workflow_step_delete(workflow_with_steps: Workflow, step_index: int):
    """Test that step deletion functions correctly."""
    steps = workflow_with_steps.steps()

    # Delete the appropriate step
    deleted_step = steps.pop(step_index)
    deleted_step.delete()

    # Assert child/parent relationship
    step_a, step_b = steps
    assert step_a.children() == [step_b]
    assert step_b.parents() == [step_a]

    # Assert distances have been updated correctly
    assert WorkflowStepDependency.objects.get(parent=step_a, child=step_b).distance == 1

    # Assert that no more links referencing step 3 exist
    assert not WorkflowStepDependency.objects.filter(
        models.Q(parent=deleted_step) | models.Q(child=deleted_step)
    ).exists()


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
def test_workflow_steps_depth(workflow_graph_steps: Workflow, workflow_step_factory):
    step_1, step_2, step_4, step_3, step_5, step_6 = workflow_graph_steps.steps()
    assert workflow_graph_steps.steps(depth=0) == [step_1]
    assert workflow_graph_steps.steps(depth=1) == [step_1, step_2, step_4]
    assert workflow_graph_steps.steps(depth=2) == [step_1, step_2, step_4, step_3, step_5, step_6]


@pytest.mark.django_db
def test_workflow_no_circular_steps(workflow_graph_steps: Workflow):
    step_1, step_2, step_4, step_3, step_5, step_6 = workflow_graph_steps.steps()
    with pytest.raises(ValidationError):
        step_6.append_step(step_1)


@pytest.mark.django_db
def test_workflow_root_steps(workflow_graph_steps: Workflow, workflow_step_factory):
    step_1, step_2, step_4, step_3, step_5, step_6 = workflow_graph_steps.steps()
    assert workflow_graph_steps.root_steps() == [step_1]

    # Add another root step
    step_7 = workflow_step_factory(workflow=workflow_graph_steps)
    workflow_graph_steps.add_root_step(step_7)
    assert workflow_graph_steps.root_steps() == [step_1, step_7]


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
