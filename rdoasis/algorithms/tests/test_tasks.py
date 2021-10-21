import pathlib
from typing import List

import celery
from faker import Faker
import pytest
from rgd.models.common import ChecksumFile

from rdoasis.algorithms.models import AlgorithmTask
from rdoasis.algorithms.tasks.common import ManagedTask


def write_to_test_file(path: str):
    fake = Faker()
    with open(path, 'w') as outfile:
        outfile.write(fake.paragraph())


@celery.shared_task(base=ManagedTask, bind=True)
def succeeding_task(self, *args, **kwargs):
    output_dir = self.output_dir
    test_file = pathlib.Path(f'{output_dir}/test.txt')
    test_file.touch()

    with open(test_file, 'w') as outfile:
        outfile.write('Test Output')

    # Test that on_success saves this
    self.algorithm_task.output_log = 'OUTPUT!'


@celery.shared_task(base=ManagedTask, bind=True)
def succeeding_task_complex_files(self, *args, **kwargs):
    output_dir: pathlib.Path = self.output_dir

    file_1 = output_dir / 'test.txt'
    write_to_test_file(file_1)

    dir_1 = output_dir / 'foo'
    dir_1.mkdir()
    file_2 = dir_1 / 'bar.txt'
    file_3 = dir_1 / 'bar2.txt'
    write_to_test_file(file_2)
    write_to_test_file(file_3)

    dir_2 = dir_1 / 'bar'
    dir_2.mkdir()
    file_4 = dir_2 / 'baz.txt'
    write_to_test_file(file_4)

    return 'DONE!'


@celery.shared_task(base=ManagedTask, bind=True)
def failing_task(self, *args, **kwargs):
    raise Exception('Task failed')


@pytest.mark.django_db
def test_successful_task(algorithm_task: AlgorithmTask):
    succeeding_task.delay(algorithm_task_id=algorithm_task.pk)
    algorithm_task.refresh_from_db()

    assert algorithm_task.status == AlgorithmTask.Status.SUCCEEDED
    assert algorithm_task.output_log == 'OUTPUT!'

    files: List[ChecksumFile] = list(algorithm_task.output_dataset.all())
    assert len(files) == 1
    assert files[0].name == 'test.txt'

    file = files[0]
    assert file.file.read() == b'Test Output'


@pytest.mark.django_db
def test_sucessful_task_complex_files(algorithm_task_with_input: AlgorithmTask):
    """Test that no input files are duplicated in output, and that all output is present."""
    succeeding_task_complex_files.delay(algorithm_task_id=algorithm_task_with_input.pk)
    algorithm_task_with_input.refresh_from_db()

    # Assert output file length
    output_files = list(algorithm_task_with_input.output_dataset.all())
    assert len(output_files) == 4

    # Assert output file structure
    output_filenames = {f.name for f in output_files}
    assert output_filenames == {
        'test.txt',
        'foo/bar.txt',
        'foo/bar2.txt',
        'foo/bar/baz.txt',
    }

    # Assert no overlap in file names (could collide if randomly generated)
    input_files = list(algorithm_task_with_input.algorithm.input_dataset.all())
    output_filenames = [f.name for f in output_files]
    assert not any([f.name in output_filenames for f in input_files])


@pytest.mark.django_db
def test_failed_task(algorithm_task: AlgorithmTask):
    failing_task.delay(algorithm_task_id=algorithm_task.pk)
    algorithm_task.refresh_from_db()

    # Assert that status is failed, and exception was caught as output
    assert algorithm_task.status == AlgorithmTask.Status.FAILED
    assert algorithm_task.output_log != ''

    files: List[ChecksumFile] = list(algorithm_task.output_dataset.all())
    assert len(files) == 0


@pytest.mark.django_db
def test_managed_task_setup(algorithm_task_with_input: AlgorithmTask):
    base_task = ManagedTask()
    base_task._setup(algorithm_task_id=algorithm_task_with_input.pk)

    # Assert values set
    assert base_task.algorithm_task == algorithm_task_with_input
    assert base_task.algorithm == algorithm_task_with_input.algorithm
    assert base_task.output_dir.is_dir()

    algorithm_task_with_input.refresh_from_db()
    assert algorithm_task_with_input.status == AlgorithmTask.Status.RUNNING

    # Assert downloaded files
    input_dataset = list(algorithm_task_with_input.algorithm.input_dataset.all())

    assert len(input_dataset) == len(base_task.input_dataset_paths)
    assert all([p.exists() for p in base_task.input_dataset_paths])
    assert all([base_task.input_dir in p.parents for p in base_task.input_dataset_paths])

    # Cleanup, not tested here
    base_task._cleanup()


@pytest.mark.django_db
def test_managed_task_cleanup(algorithm_task_with_input: AlgorithmTask):
    base_task = ManagedTask()
    base_task._setup(algorithm_task_id=algorithm_task_with_input.pk)

    # Paths to check for later
    input_dataset_paths = base_task.input_dataset_paths
    output_dir = base_task.output_dir

    # Cleanup, not tested here
    base_task._cleanup()

    # Assert cleanup succeeded
    assert not any([p.exists() for p in input_dataset_paths])
    assert not output_dir.is_dir()
