from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_extensions.routers import ExtendedSimpleRouter

from rdoasis.algorithms.views.algorithms import (
    AlgorithmTaskViewSet,
    AlgorithmViewSet,
    DatasetViewSet,
    DockerImageViewSet,
)

# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='RD-OASIS', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


router = ExtendedSimpleRouter()
router.register('docker_images', DockerImageViewSet)
router.register('datasets', DatasetViewSet, basename='dataset')
router.register('algorithms', AlgorithmViewSet)
router.register('algorithm_tasks', AlgorithmTaskViewSet, basename='task')

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('admin/', admin.site.urls),
    path('api/s3-upload/', include('s3_file_field.urls')),
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
    path('', include('rgd.urls')),
    path('', include('rgd_imagery.urls')),
    path('api/', include(router.urls)),
    # Redirect homepage to RGD core app homepage
    path(r'', RedirectView.as_view(url='rgd', permanent=False), name='index'),
]

schema_view = get_schema_view(
    openapi.Info(
        title='ResonantGeoData OASIS API',
        default_version='v1',
        description='ResonantGeoData OASIS',
        # terms_of_service='https://www.google.com/policies/terms/',
        contact=openapi.Contact(email='rgd@kitare.com'),
        license=openapi.License(name='Apache 2.0'),
    ),
    public=False,
    permission_classes=(permissions.AllowAny,),
    patterns=urlpatterns,
)

urlpatterns += [
    re_path(
        r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json',
    ),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
