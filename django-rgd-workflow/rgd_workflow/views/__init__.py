import logging

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render

logger = logging.getLogger(__name__)


def handler500(request):
    return render(request, 'errors/application-error.html', status=500)


def index(request):
    return render(request, 'index.html')


class _CustomUserTest(UserPassesTestMixin):
    """A helper to ensure that the current user is only requesting a view their own data."""

    def test_func(self):
        object = self.get_object()
        return self.request.user == object.creator
