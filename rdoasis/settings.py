from __future__ import annotations

from pathlib import Path

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)
from configurations import values
from rgd.configuration import ResonantGeoDataBaseMixin


class RdoasisMixin(ResonantGeoDataBaseMixin, ConfigMixin):
    WSGI_APPLICATION = 'rdoasis.wsgi.application'
    ROOT_URLCONF = 'rdoasis.urls'

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'rdoasis.core.apps.CoreConfig',
            'rdoasis.algorithms.apps.AlgorithmsConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            's3_file_field',
            'rules.apps.AutodiscoverRulesConfig',
            'django_cleanup.apps.CleanupConfig',
            'rgd',
            'rgd_imagery',
        ]

        configuration.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'].append(
            'rest_framework.authentication.BasicAuthentication'
        )

        configuration.AUTHENTICATION_BACKENDS.insert(0, 'rules.permissions.ObjectPermissionBackend')


class DevelopmentConfiguration(RdoasisMixin, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(RdoasisMixin, TestingBaseConfiguration):
    CELERY_TASK_ALWAYS_EAGER = True


class ProductionConfiguration(RdoasisMixin, ProductionBaseConfiguration):
    K8S_CLUSTER_NAME = values.Value(environ_required=True)


class HerokuProductionConfiguration(RdoasisMixin, HerokuProductionBaseConfiguration):
    K8S_CLUSTER_NAME = values.Value(environ_required=True)

    # Use different env var names (with no DJANGO_ prefix) for services that Heroku auto-injects
    DATABASES = values.DatabaseURLValue(
        environ_name='DATABASE_URL',
        environ_prefix=None,
        environ_required=True,
        engine='django.contrib.gis.db.backends.postgis',
        conn_max_age=600,
        ssl_require=True,
    )
