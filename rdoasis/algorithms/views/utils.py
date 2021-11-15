from functools import wraps
from typing import Iterable, Union

from django.db.models.query import QuerySet
from rest_framework.response import Response
from rest_framework.serializers import Serializer


def paginate_action(serializer_cls: Serializer):
    def decorator(view_method):
        @wraps(view_method)
        def wrapped(self, *args, **kwargs):
            queryset: Union[QuerySet, Iterable] = view_method(self, *args, **kwargs)

            # Paginate
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = serializer_cls(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = serializer_cls(queryset, many=True)
            return Response(serializer.data)

        return wrapped

    return decorator
