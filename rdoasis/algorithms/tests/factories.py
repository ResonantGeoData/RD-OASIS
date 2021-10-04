from pathlib import Path

from django.contrib.auth.models import User
import factory.django
import factory.fuzzy
from rgd.models.common import ChecksumFile

from rdoasis.algorithms.models import Algorithm, AlgorithmTask, DockerImage

PARENT_DIR = Path(__file__).parent
DATA_DIR = PARENT_DIR / 'data'


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class ChecksumFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChecksumFile

    file = factory.django.FileField(from_path=(DATA_DIR / 'test.txt'))
    name = factory.LazyAttribute(lambda obj: obj.file.name)


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
