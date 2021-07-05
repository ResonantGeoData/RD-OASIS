from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'rdoasis.algorithms'

    def ready(self):
        import rdoasis.algorithms.signals  # noqa: F401
