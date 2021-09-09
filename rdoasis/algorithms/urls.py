from django.contrib import admin
from django.urls import include, path
from djproxy.urls import generate_routes
from rest_framework_extensions.routers import ExtendedSimpleRouter

from . import views
from .views.workflow import WorkflowViewSet

router = ExtendedSimpleRouter()
workflow_routes = router.register('workflow', WorkflowViewSet)

admin.site.index_template = 'admin/add_links.html'
urlpatterns = [
    path('core', views.index, name='core'),
    path('', include(router.urls)),
] + generate_routes({'flower-proxy': {'base_url': 'http://flower:5555/', 'prefix': '/flower/'}})

handler500 = views.handler500
