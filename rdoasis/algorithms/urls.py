import inspect

from django.contrib import admin
from django.urls import include, path
from django_filters.rest_framework import DjangoFilterBackend
from djproxy.urls import generate_routes
from rest_framework import viewsets
from rest_framework.routers import SimpleRouter
from rgd import utility

from . import serializers, views

router = SimpleRouter()
for _, ser in inspect.getmembers(serializers):
    if inspect.isclass(ser):
        model = ser.Meta.model
        model_name = model.__name__
        viewset_class = type(
            model_name + 'ViewSet',
            (viewsets.ModelViewSet,),
            {
                'parser_classes': (utility.MultiPartJsonParser,),
                'queryset': model.objects.all(),
                'serializer_class': ser,
                'filter_backends': [DjangoFilterBackend],
                'filterset_fields': utility.get_filter_fields(model),
            },
        )
        viewset_class.__doc__ = model.__doc__
        router.register('api/%s' % (model_name.lower()), viewset_class)

admin.site.index_template = 'admin/add_links.html'
urlpatterns = [
    path('core', views.index, name='core'),
    path('', include(router.urls)),
] + generate_routes({'flower-proxy': {'base_url': 'http://flower:5555/', 'prefix': '/flower/'}})

handler500 = views.handler500
