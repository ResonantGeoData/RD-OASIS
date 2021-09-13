import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from rdoasis.algorithms.models.workflow import WorkflowStep

from .factories import DockerImageFactory, WorkflowFactory, WorkflowStepFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def workflow_with_steps(workflow, workflow_step_factory):
    step_1: WorkflowStep = workflow_step_factory(workflow=workflow)
    step_2: WorkflowStep = workflow_step_factory(workflow=workflow)
    step_3: WorkflowStep = workflow_step_factory(workflow=workflow)

    workflow.add_root_step(step_1)
    step_1.append_step(step_2)
    step_2.append_step(step_3)

    return workflow


@pytest.fixture
def workflow_graph_steps(workflow_with_steps, workflow_step_factory):
    """
    Create a graph with the following structure

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

    return workflow_with_steps


register(DockerImageFactory)
register(WorkflowFactory)
register(WorkflowStepFactory)
