import pathlib
from typing import List

import celery
import pytest
from rgd.models.common import ChecksumFile

from rdoasis.algorithms.models import AlgorithmTask
from rdoasis.algorithms.tasks.common import ManagedTask


@celery.shared_task(base=ManagedTask, bind=True)
def succeeding_task(self, *args, **kwargs):
    output_dir = self.output_dir
    test_file = pathlib.Path(f'{output_dir}/test.txt')
    test_file.touch()

    with open(test_file, 'w') as outfile:
        outfile.write('Test Output')

    return 'OUTPUT!'


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
def test_failed_task(algorithm_task: AlgorithmTask):
    failing_task.delay(algorithm_task_id=algorithm_task.pk)
    algorithm_task.refresh_from_db()

    # Assert that status is failed, and exception was caught as output
    assert algorithm_task.status == AlgorithmTask.Status.FAILED
    assert algorithm_task.output_log != ''

    files: List[ChecksumFile] = list(algorithm_task.output_dataset.all())
    assert len(files) == 0


# TODO: Add task that tests docker run
