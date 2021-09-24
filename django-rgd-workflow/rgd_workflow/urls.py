from django.contrib import admin
from django.urls import include, path
from djproxy.urls import generate_routes
from rest_framework_extensions.routers import ExtendedSimpleRouter

from . import views
from .views.workflow import WorkflowStepViewSet, WorkflowViewSet

router = ExtendedSimpleRouter()
workflow_routes = router.register('api/workflow', WorkflowViewSet)
workflow_routes.register(
    'steps',
    WorkflowStepViewSet,
    basename='step',
    parents_query_lookups=[f'workflow__{WorkflowViewSet.lookup_field}'],
)

admin.site.index_template = 'admin/add_links.html'
urlpatterns = [
    path('core', views.index, name='core'),
    path('', include(router.urls)),
] + generate_routes({'flower-proxy': {'base_url': 'http://flower:5555/', 'prefix': '/flower/'}})

handler500 = views.handler500
