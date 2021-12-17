from django.core.management.base import BaseCommand

from rdoasis.algorithms.management.utils.k8s import KubernetesContainerMonitor


class Command(BaseCommand):
    help = 'Monitor a K8s container and return files, status, etc.'

    def handle(self, *args, **options):
        KubernetesContainerMonitor.from_env().download_input_dataset()
