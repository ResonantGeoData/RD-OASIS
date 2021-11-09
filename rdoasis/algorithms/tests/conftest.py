import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from .factories import (
    AlgorithmFactory,
    AlgorithmTaskFactory,
    ChecksumFileFactory,
    DatasetFactory,
    DockerImageFactory,
    UserFactory,
)

# For some reason, these need to be declared first
register(AlgorithmFactory)
register(AlgorithmTaskFactory)
register(ChecksumFileFactory)
register(DatasetFactory)
register(DockerImageFactory)
register(UserFactory)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client
