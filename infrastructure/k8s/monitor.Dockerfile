FROM python:3.8-slim
# Install system librarires for Python packages:
# * psycopg2
# * python-magic
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
        libpq-dev \
        gcc \
        libc6-dev \
        libmagic1 \
        fuse \
        docker.io \
        && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./setup.py ./manage.py /opt/django-project/
COPY rdoasis /opt/django-project/rdoasis

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project
RUN pip install \
    --find-links https://girder.github.io/large_image_wheels \
    -e .[dev,worker,fuse,k8s]

CMD ["/opt/django-project/manage.py", "monitor_container_k8s"]
