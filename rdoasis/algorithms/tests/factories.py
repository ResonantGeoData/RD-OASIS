import factory.django

from rdoasis.algorithms import models


class WorkflowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Workflow


class DockerImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DockerImage

    image_id = 'hello-world'
    image_file = None


class WorkflowStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.WorkflowStep

    command = factory.LazyAttribute(lambda _: list())
    docker_image = factory.SubFactory(DockerImageFactory)
    workflow = factory.SubFactory(WorkflowFactory)
    name = factory.Faker('pystr')
