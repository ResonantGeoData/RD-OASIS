from pathlib import Path
import random

from django.contrib.auth.models import User
import factory.django
import factory.fuzzy
from faker import Faker
from rgd.models.common import ChecksumFile

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, Dataset, DockerImage

PARENT_DIR = Path(__file__).parent
DATA_DIR = PARENT_DIR / 'data'


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


def create_checksum_file_name():
    fake = Faker()
    return fake.file_path(depth=random.randint(0, 5)).lstrip('/')


class ChecksumFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChecksumFile

    file = factory.django.FileField(from_path=(DATA_DIR / 'test.txt'))
    name = factory.LazyFunction(create_checksum_file_name)


class DatasetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Dataset

    name = factory.fuzzy.FuzzyText()

    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        self.files.set([ChecksumFileFactory() for _ in range(5)])


class DockerImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DockerImage

    image_id = 'hello-world'
    image_file = None


class AlgorithmFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Algorithm

    name = factory.fuzzy.FuzzyText()
    docker_image = factory.SubFactory(DockerImageFactory)


class AlgorithmTaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlgorithmTask

    algorithm = factory.SubFactory(AlgorithmFactory)
    input_dataset = factory.SubFactory(DatasetFactory)
