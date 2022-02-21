import logging
import os

from django.conf import settings
import djclick as click
import pooch
from rgd.models import Collection
from rgd.models.utils import get_or_create_checksumfile

from rdoasis.algorithms.models import Dataset

logger = logging.getLogger(__name__)

# https://data.kitware.com/#user/5edea5859014a6d84eabf0f0/folder/620dd1394acac99f42e7a7c7
registry = {
    'ASO_800M_SWE_USCOBR_20190419.csv': '4f1166f7d92365be4eae2ee6ec8935042bf5abb6a872bb2a6fe01d4bb848973f3f8898dab171a2fd4d440c3b9ea36a2752ccb1d7c013f56d50445f9e2f77c4e9',  # noqa
    'ASO_800M_SWE_USCOBR_20190624.csv': '200c16c6421657aadfc058cc35a157e46a23eebd07b88d7e76cc3307a1f5ee59d82eae7e937f19ee650826182e92eefcc56661faf7b9db4879bf32c5a48f6606',  # noqa
    'ASO_800M_SWE_USCOCB_20160404.csv': 'a0f3bf07e294e8a5c905a0cb67d03d175a51ce40b1ff479d64ef7465d71cf6ca52de56120bee657f971515c99c0122127c401fb1c9fd2da2e4dc6eee06b01955',  # noqa
    'ASO_800M_SWE_USCOCM_20190407.csv': '6d4dec639e0c9ab55c0cfb33873e83edc227b47c9fdb610def5e8e16bf1cc433fde9fb35b178deaf15f7a1eb50dcdf78fbf6879dcbd2ea543d28a7cd97707daa',  # noqa
    'ASO_800M_SWE_USCOCM_20190610.csv': '3051a2eefdb10c5a05bf4bc9e599f1aaa89bfd94fd984fded2a5328316510622d57567fcac770333eaa9f5479aba085ab2f82555cbe05ac249274e1529f2187f',  # noqa
    'ASO_800M_SWE_USCOGE_20180331.csv': '971d7571508afce8617132eb79d124edca02ff8ebd90e27d604b8a363ece471c33380be40c2397b3c04b790429b815b1633d9ade0467b4944c95688c9c1459b3',  # noqa
    'ASO_800M_SWE_USCOGE_20180524.csv': 'd4f44389537e1f3de4c27c09b7d94c2eac5448354590094351df03f6891acded938bebef0d8b7872f8b9145388d1a6b05dfd2ad7787cfa9c43cf358aea204d4f',  # noqa
    'ASO_800M_SWE_USCOGE_20190407.csv': '2b4ae7af08b4bb718c209b975c9cf6a59b17ce3f213600809ca3b23862cc7dfe62429003060a62596d381482ec9384062475ed2c60ebc2c0cf74d634f7869a7d',  # noqa
    'ASO_800M_SWE_USCOGE_20190610.csv': '94d087d7f411e764a1a3bebc1218a35e4009383e1c1d7cf216e7c1681aac66e5e0e347e646bf7a21a7fc84f4916d97d6fb83794c801a6ac75dec061f2593345e',  # noqa
    'ASO_800M_SWE_USCOGT_20180330.csv': '577b33f5a7aba379595dc905447a352978bb2de954ddd1398e4ce4dfa536738810206d6e36c9a2c3c532af54f0554a4288cc028fbf547ccaf1ac601e8d012d45',  # noqa
    'ASO_800M_SWE_USCOGT_20190408.csv': '222ae78fd86554c27ae1a705879073d3120b1d1252457fc990170441641284f30ffbb7f1dae45065ff86c899e8c9d5130978d65aeaac834f8382d51d218280be',  # noqa
    'ASO_800M_SWE_USCOGT_20190609.csv': '68008e4cdc9337f77d52e5c341ac931152c75241105613c16c3ace639af0e6a4f67c303d939100c51d7a6cb22ee981a6105eb419ae53c215ff2ce7cb903391c8',  # noqa
}


class DKCPooch(pooch.Pooch):
    def get_url(self, fname):
        self._assert_file_in_registry(fname)
        hashvalue = self.registry[fname]
        return self.base_url.format(algo='sha512', hashvalue=hashvalue)


# path = pooch.cache_location(pooch.os_cache('geodata'), None, None)
datastore = DKCPooch(
    path=pooch.utils.cache_location(
        os.path.join(os.environ.get('TOX_WORK_DIR', pooch.utils.os_cache('pooch')), 'rgd_datastore')
    ),
    base_url='https://data.kitware.com/api/v1/file/hashsum/{algo}/{hashvalue}/download',
    registry=registry,
)


@click.command()
def ingest() -> None:

    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    collection, _ = Collection.objects.get_or_create(name='LBNL OASIS Example')

    def make_file(url, name):
        f, _ = get_or_create_checksumfile(
            url=url,
            name=name,
            collection=collection,
        )
        return f

    for i, key in enumerate(registry.keys()):
        url = datastore.get_url(key)
        logger.info(f'{i}/{len(registry)}: {url}')
        f = make_file(url, key)
        d = Dataset()
        d.name = key
        d.save()
        d.files.add(f)
