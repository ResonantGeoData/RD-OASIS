import tempfile
from typing import List

from django.core.files.uploadedfile import SimpleUploadedFile
import docker
import pytest
from rgd.models.common import ChecksumFile

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, DockerImage

# First command fails immediately, second command runs
# successfully but outputs a nonzero exit status
FAILING_COMMANDS = ['notacommand', 'exit 1']
ECHO_AND_WRITE_CMD = '/bin/sh -c "echo DATA > output/hello.txt && echo HI"'


@pytest.fixture
def saved_docker_image() -> str:
    client = docker.from_env()
    image = client.images.pull('alpine')
    with tempfile.NamedTemporaryFile(suffix='.tar') as f:
        # Save image to file
        for chunk in image.save(named=True):
            f.write(chunk)

        f.seek(0)
        yield f.name


@pytest.fixture
def docker_image_from_file(
    saved_docker_image, docker_image_factory, checksum_file_factory
) -> DockerImage:
    with open(saved_docker_image, 'rb') as f:
        file = SimpleUploadedFile(name=saved_docker_image, content=f.read())

    return docker_image_factory(
        name='test',
        image_id=None,
        image_file=checksum_file_factory(name='alpine_image', file=file),
    )


@pytest.mark.docker
@pytest.mark.django_db
def test_successful_task(algorithm_factory, docker_image_factory, dataset_factory):
    alg: Algorithm = algorithm_factory(
        name='test',
        command=ECHO_AND_WRITE_CMD,
        docker_image=docker_image_factory(name='test', image_id='alpine'),
    )

    # Run task
    task: AlgorithmTask = alg.run(dataset_id=dataset_factory().id)
    task.refresh_from_db()

    # Make assertions
    assert task.status == AlgorithmTask.Status.SUCCEEDED
    assert task.output_log == 'HI\n'

    files: List[ChecksumFile] = list(task.output_dataset.files.all())
    assert len(files) == 1
    assert files[0].name == 'hello.txt'

    file = files[0]
    assert file.file.read() == b'DATA\n'


@pytest.mark.docker
@pytest.mark.django_db
def test_successful_task_image_file(algorithm_factory, docker_image_from_file, dataset_factory):
    alg: Algorithm = algorithm_factory(
        name='test', command=ECHO_AND_WRITE_CMD, docker_image=docker_image_from_file
    )

    # Run task
    task: AlgorithmTask = alg.run(dataset_id=dataset_factory().id)
    task.refresh_from_db()

    # Make assertions
    assert task.status == AlgorithmTask.Status.SUCCEEDED
    assert task.output_log == 'HI\n'

    files: List[ChecksumFile] = list(task.output_dataset.files.all())
    assert len(files) == 1
    assert files[0].name == 'hello.txt'

    file = files[0]
    assert file.file.read() == b'DATA\n'


@pytest.mark.docker
@pytest.mark.django_db
@pytest.mark.parametrize('command', FAILING_COMMANDS)
def test_failed_task(algorithm_factory, docker_image_factory, dataset_factory, command):
    alg: Algorithm = algorithm_factory(
        name='test',
        command=command,
        docker_image=docker_image_factory(name='test', image_id='alpine'),
    )

    # Run task
    task: AlgorithmTask = alg.run(dataset_id=dataset_factory().id)
    task.refresh_from_db()

    # Make assertions
    assert task.status == AlgorithmTask.Status.FAILED
    assert task.output_dataset is None or not task.output_dataset.files.count()

    # Assert output log isn't empty
    assert task.output_log


@pytest.mark.docker
@pytest.mark.django_db
@pytest.mark.parametrize('command', FAILING_COMMANDS)
def test_failed_task_image_file(
    algorithm_factory, docker_image_from_file, dataset_factory, command
):
    alg: Algorithm = algorithm_factory(
        name='test', command=command, docker_image=docker_image_from_file
    )

    # Run task
    task: AlgorithmTask = alg.run(dataset_id=dataset_factory().id)
    task.refresh_from_db()

    # Make assertions
    assert task.status == AlgorithmTask.Status.FAILED
    assert task.output_dataset is None or not task.output_dataset.files.count()

    # Assert output log isn't empty
    assert task.output_log
