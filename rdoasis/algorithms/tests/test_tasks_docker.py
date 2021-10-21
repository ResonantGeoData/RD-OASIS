from typing import List

import factory.django
import pytest
from rgd.models.common import ChecksumFile

from rdoasis.algorithms.models import Algorithm, AlgorithmTask
from rdoasis.algorithms.tests.factories import DATA_DIR


@pytest.mark.docker
@pytest.mark.django_db
def test_successful_task(algorithm_factory, docker_image_factory, checksum_file_factory):
    alg: Algorithm = algorithm_factory(
        name='test',
        command='/bin/sh -c "echo DATA > output/hello.txt && echo HI"',
        docker_image=docker_image_factory(name='test', image_id='alpine'),
    )

    # Run task
    task: AlgorithmTask = alg.run()
    task.refresh_from_db()

    # Make assertions
    assert task.status == AlgorithmTask.Status.SUCCEEDED
    assert task.output_log == 'HI\n'

    files: List[ChecksumFile] = list(task.output_dataset.all())
    assert len(files) == 1
    assert files[0].name == 'hello.txt'

    file = files[0]
    assert file.file.read() == b'DATA\n'


@pytest.mark.docker
@pytest.mark.django_db
def test_failed_task(algorithm_factory, docker_image_factory, checksum_file_factory):
    alg: Algorithm = algorithm_factory(
        name='test',
        command='notacommand',
        docker_image=docker_image_factory(name='test', image_id='alpine'),
    )

    # Run task
    task: AlgorithmTask = alg.run()
    task.refresh_from_db()

    # Make assertions
    assert task.status == AlgorithmTask.Status.FAILED
    assert task.output_dataset.all().count() == 0

    # Assert output log isn't empty
    assert task.output_log
