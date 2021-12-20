#!/bin/bash

celery --app rdoasis.celery worker --loglevel INFO --without-heartbeat
