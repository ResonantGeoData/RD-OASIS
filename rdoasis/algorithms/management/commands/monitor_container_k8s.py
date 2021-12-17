from django.core.management.base import BaseCommand
from rdoasis.algorithms.management.utils.k8s import KubernetesContainerMonitor


class Command(BaseCommand):
    help = 'Monitor a K8s container and return files, status, etc.'

    def handle(self, *args, **options):
        # TODO: use post_start lifecycle hook to build local image if necessary
        KubernetesContainerMonitor.from_env().monitor_container()
