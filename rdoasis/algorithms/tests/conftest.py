import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from rdoasis.algorithms.models import AlgorithmTask

from .factories import (
    AlgorithmFactory,
    AlgorithmTaskFactory,
    ChecksumFileFactory,
    DockerImageFactory,
    UserFactory,
)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def algorithm_task_with_input(
    algorithm_task: AlgorithmTask, checksum_file_factory
) -> AlgorithmTask:
    files = [checksum_file_factory() for _ in range(10)]
    algorithm_task.algorithm.input_dataset.add(*files)

    return algorithm_task


register(AlgorithmFactory)
register(AlgorithmTaskFactory)
register(ChecksumFileFactory)
register(DockerImageFactory)
register(UserFactory)
