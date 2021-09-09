from __future__ import annotations

from typing import List, Type

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.aggregates import Count
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
from rgd.models import ChecksumFile, Collection

__all__ = ['DockerImage', 'WorkflowStepDependency', 'WorkflowStep', 'Workflow']


def create_default_workflow_collection():
    return Collection.objects.create(name='Collection Workflow')


class DockerImage(TimeStampedModel):
    # Optional name
    name = models.CharField(null=True, max_length=255)

    # The image id to pull down
    image_id = models.CharField(null=True, max_length=255)

    # If the docker image was provided as a file
    image_file = models.ForeignKey(
        ChecksumFile, related_name='docker_images', null=True, on_delete=models.CASCADE
    )

    # TODO: Add field for registry, for other images
    # registry = models.URLField(null=True)

    class Meta:
        constraints = [
            # Ensure that only one of these fields can be set at a time
            models.CheckConstraint(
                check=(
                    models.Q(image_id__isnull=False, image_file__isnull=True)
                    | models.Q(image_id__isnull=True, image_file__isnull=False)
                ),
                name='single_image_source',
            )
        ]


class WorkflowStepDependency(TimeStampedModel):
    """
    A dependency relation between two workflow steps.

    This uses a closure table design, and supports trees of connected workflow steps.
    In this model, parent points to any step that must run before the corresponding child step.
    In any given workflow, a WorkflowStep will have multiple corresponding WorkflowStepDependency
    entries pointing to it, to indicate the steps which run before and after it (e.g. where on
    the tree it resides). There is an entry in this table for any dependency, not just immediate.
    For example, if there is a workflow of the following format:

        A -> B -> C

    There are connections from A to B, A to C, and B to C. For each workflow step, there is also a
    self referencing connection (e.g. for step A, parent = A, child = A), to ensure consistency.

    NOTE: This model should not be instantiated directly, as creating objects incorrectly can cause
    inconsistencies. Rather, the provided methods in Workflow and WorkflowStep should be used.
    """

    parent = models.ForeignKey(
        'WorkflowStep', related_name='workflow_step_parents', on_delete=models.CASCADE
    )
    child = models.ForeignKey(
        'WorkflowStep', related_name='workflow_step_children', on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent', 'child'], name='unique_dependency')
        ]


class WorkflowStep(TimeStampedModel):
    """An algorithm to run in a workflow."""

    name = models.CharField(max_length=255)

    # The docker image to use
    docker_image = models.ForeignKey(
        DockerImage, related_name='workflow_steps', on_delete=models.CASCADE
    )

    # The command to run the image with, as an array of strings
    command = ArrayField(models.CharField(max_length=255))

    # The workflow this step is attached to
    workflow = models.ForeignKey(
        'Workflow', related_name='workflow_steps', on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['workflow', 'name'], name='unique_workflow_step')
        ]

    def parents(self) -> List[WorkflowStep]:
        """Return all parents of this step (all steps that run prior to this step)."""
        return [
            relation.parent
            for relation in WorkflowStepDependency.objects.filter(child=self)
            .exclude(parent=self)
            .select_related('parent')
        ]

    def children(self) -> List[WorkflowStep]:
        """Return all children of this step (all steps that run after this step)."""
        return [
            relation.child
            for relation in WorkflowStepDependency.objects.filter(parent=self)
            .exclude(child=self)
            .select_related('parent')
        ]

    def append_step(self, step: WorkflowStep):
        """Add a step to the workflow, running after this step."""
        # Ensure that step is saved
        step.save()

        # Create dependencies between this step's parents and the new step
        dependencies = [WorkflowStepDependency(parent=a, child=step) for a in self.parents()]

        # Create a dependency between this step and the new step
        dependencies.append(WorkflowStepDependency(parent=self, child=step))

        # Add self reference dependency
        dependencies.append(WorkflowStepDependency(parent=step, child=step))

        # Save dependencies
        WorkflowStepDependency.objects.bulk_create(dependencies)

        # Return added step
        return step


class Workflow(TimeStampedModel):
    """A model for organizing the running of workflow steps."""

    name = models.CharField(max_length=255, unique=True)
    collection = models.OneToOneField(
        Collection, on_delete=models.PROTECT, default=create_default_workflow_collection
    )

    def steps(self) -> List[WorkflowStep]:
        """
        Return all workflow steps, ordered from first to last.

        This function returns the steps in Bread First Search (BFS) ordering.
        """
        # Get all steps, ordering from most to least parent dependencies (first run to last run)
        all_steps = (
            WorkflowStep.objects.filter(workflow=self)
            .annotate(count=Count('workflow_step_parents'))
            .order_by('-count')
        )

        return list(all_steps)

    def add_root_step(self, workflow_step: WorkflowStep) -> WorkflowStep:
        """
        Add a step to run at the beginning of a workflow.

        Note: There is not necessarily a single root step, and as such multiple steps
        can run at the beginning of a workflow.
        """
        # Ensure step is saved
        workflow_step.save()

        # Add self referencing step
        WorkflowStepDependency.objects.create(parent=workflow_step, child=workflow_step)

        # Return added_step
        return workflow_step


@receiver(post_delete, sender=Workflow)
def workflow_collection_delete(sender: Type[Workflow], instance: Workflow, **kwargs):
    collection: Collection = instance.collection
    collection.delete()
