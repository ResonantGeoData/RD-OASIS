import os
import time
from typing import Optional, Tuple

from django.core.management.base import BaseCommand
from kubernetes import client, config


config.load_incluster_config()

# Load envs
POD_NAME = os.getenv('POD_NAME')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')
TASK_ID = os.getenv('TASK_ID')
if {None, '_'} & {POD_NAME, CONTAINER_NAME, TASK_ID}:
    raise Exception('Not all env vars specified.')


coreapi = client.CoreV1Api()


def poll_container() -> Tuple[Optional[client.V1ContainerStateTerminated], str]:
    pod: client.V1Pod = coreapi.read_namespaced_pod_status(name=POD_NAME, namespace='default')

    log = ''
    termination_state = None
    try:
        container: client.V1ContainerStatus = next(
            c for c in pod.status.container_statuses if c.name == CONTAINER_NAME  # type: ignore
        )
        termination_state = container.state.terminated  # type: ignore
    except (AttributeError, StopIteration):
        pass

    log = coreapi.read_namespaced_pod_log(name=POD_NAME, namespace='default')
    return termination_state, log


class Command(BaseCommand):
    help = 'Monitor a K8s container and return files, status, etc.'

    def handle(self, *args, **options):
        log: str = ''
        termination_state = None
        while termination_state is None:
            termination_state, log = poll_container()
            time.sleep(1)

        # TODO: Write log to task
        # TODO: Read return code from state.terminated
        print(log)
