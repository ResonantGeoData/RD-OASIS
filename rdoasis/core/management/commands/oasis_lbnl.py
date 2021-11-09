from datetime import datetime
from glob import glob
import logging
import os

from django.conf import settings
import djclick as click
from rgd.models import Collection
from rgd.models.utils import get_or_create_checksumfile
from rgd_imagery.models import get_or_create_image_set, Image, Raster

logger = logging.getLogger(__name__)


def _make_raster_from_files(checksumfiles):
    images = [Image.objects.get_or_create(file=f)[0] for f in checksumfiles]
    image_set, _ = get_or_create_image_set([im.pk for im in images])
    r, _ = Raster.objects.get_or_create(image_set=image_set)
    return r.rastermeta


def _get_datetime_from_filename(filename):
    # Format is *_YYYYMMDD.tif
    date_str = filename.split('_')[-1][:-4]
    try:
        return datetime.strptime(date_str,'%Y%m%d')
    except:
        return None


@click.command()
@click.option('-p', '--root_path', help='The root directory of the example data files as mounted.')
def ingest_s3(
    root_path: str
) -> None:

    logger.info(os.listdir(root_path))

    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    assert os.path.exists(root_path)
    collection, _ = Collection.objects.get_or_create(name='LBNL OASIS Example')

    def make_file(handle):
        f, _ = get_or_create_checksumfile(
            file=handle,
            name=path.replace(root_path, '').lstrip('/'),
            collection=collection,
        )
        return f

    def make_raster(handle):
        f = make_file(handle)
        meta = _make_raster_from_files([f, ])
        d = _get_datetime_from_filename(path)
        if d:
            meta.acquisition_date = d
            meta.save(update_fields=['acquisition_date', ])
        return meta

    filelist = glob(f'{root_path}/**/*.tif', recursive=True)
    for path in filelist:
        with open(path, 'rb') as handle:
            make_raster(handle)
