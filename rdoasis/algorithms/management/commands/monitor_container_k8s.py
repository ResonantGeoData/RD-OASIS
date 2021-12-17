import os
import time
from typing import Optional, Tuple

from django.core.management.base import BaseCommand
from kubernetes import client, config


try:
    config.load_incluster_config()
except config.config_exception.ConfigException:
    config.load_kube_config()

# Load envs
JOB_NAME = os.getenv('JOB_NAME')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')
TASK_ID = os.getenv('TASK_ID')
if {None, '_'} & {JOB_NAME, CONTAINER_NAME, TASK_ID}:
    raise Exception('Not all env vars specified.')


coreapi = client.CoreV1Api()
batchapi = client.BatchV1Api


def get_pod_name() -> str:
    pods: client.V1PodList = coreapi.list_namespaced_pod(
        namespace='default', label_selector=f'job-name={JOB_NAME}'
    )
    pod = pods.items[0]  # type: ignore
    return pod.metadata.name


def poll_container(pod_name: str) -> Tuple[Optional[client.V1ContainerStateTerminated], str]:
    pod: client.V1Pod = coreapi.read_namespaced_pod_status(name=pod_name, namespace='default')

    log = ''
    termination_state = None
    try:
        container: client.V1ContainerStatus = next(
            c for c in pod.status.container_statuses if c.name == CONTAINER_NAME  # type: ignore
        )
        termination_state = container.state.terminated  # type: ignore
    except (AttributeError, StopIteration):
        pass

    log = coreapi.read_namespaced_pod_log(
        name=pod_name, container=CONTAINER_NAME, namespace='default'
    )
    return termination_state, log


class Command(BaseCommand):
    help = 'Monitor a K8s container and return files, status, etc.'

    def handle(self, *args, **options):
        log: str = ''
        termination_state = None

        pod_name = get_pod_name()
        while termination_state is None:
            termination_state, log = poll_container(pod_name)
            time.sleep(1)

        # TODO: Write log to task
        # TODO: Read return code from state.terminated
        print(log)
