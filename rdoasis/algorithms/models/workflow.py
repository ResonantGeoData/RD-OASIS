from __future__ import annotations

from typing import List, Optional, Type

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete, pre_delete
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

    This uses a closure table design, and supports graphs of connected workflow steps.
    In this model, parent points to any step that must run before the corresponding child step.
    In any given workflow, a WorkflowStep will have multiple corresponding WorkflowStepDependency
    entries pointing to it, to indicate the steps which run before and after it (e.g. where in
    the graph it resides). There is an entry in this table for any dependency, not just immediate.
    For example, if there is a workflow of the following format:

        A -> B -> C

    There are connections from A to B, A to C, and B to C. For each workflow step, there is also a
    self referencing connection (e.g. for step A, parent = A, child = A), to ensure consistency.

    NOTE: This model should not be instantiated directly, as creating objects incorrectly can cause
    inconsistencies. Rather, the provided methods in Workflow and WorkflowStep should be used.
    """

    # Give related name of child_links, because for any entry with parent=node,
    # all links from node.child_links have the form (parent=node, child=child_node)
    parent = models.ForeignKey('WorkflowStep', related_name='child_links', on_delete=models.CASCADE)

    # Give related name of parent_links, because for any entry with child=node,
    # all links from node.parent_links have the form (parent=parent_node, child=node)
    child = models.ForeignKey('WorkflowStep', related_name='parent_links', on_delete=models.CASCADE)

    # The distance between the parent and child (direct child = 1, grandchild = 2, etc.)
    distance = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['parent', 'child'], name='unique_dependency')
        ]

    @staticmethod
    @transaction.atomic
    def insert_step(
        step: WorkflowStep,
        parents: Optional[List[WorkflowStep]] = None,
        children: Optional[List[WorkflowStep]] = None,
    ):
        """
        Insert a workflow step at an arbitrary position in the workflow.

        The parents and children arguments must each consist of a list of workflow steps that are
        already present in the workflow, or None.
        """
        parent_steps = parents or []
        child_steps = children or []

        # If step already exists, ensure its parents and children are included
        # TODO: INCORRECT, FIX
        if step.pk is not None:
            parent_steps.extend(step.parents())
            child_steps.extend(step.children())

        # Find all parents and children, not just direct ones. Intentionally leave in self
        # referencing links, as they are necessary below.
        all_parent_links = list(
            WorkflowStepDependency.objects.filter(child__in=parent_steps).select_related('parent')
        )
        all_child_links = list(
            WorkflowStepDependency.objects.filter(parent__in=child_steps).select_related('child')
        )

        # Ensure no circular references before continuing
        all_parent_pks = {link.parent.pk for link in all_parent_links}
        all_children_pks = {link.child.pk for link in all_child_links}
        intersection = all_parent_pks & all_children_pks
        if intersection:
            steps_pk_str = ", ".join([str(x) for x in intersection])
            raise ValidationError(
                'Circular dependency: The following steps were found as both parents and '
                f'children: {steps_pk_str}'
            )

        # Update links where the distance has changed. Only run if both
        # lists are not empty, as otherwise the queryset is empty
        if all_parent_links and all_child_links:
            WorkflowStepDependency.objects.filter(
                parent__in=[link.parent for link in all_parent_links],
                child__in=[link.child for link in all_child_links],
            ).exclude(child=models.F('parent')).update(distance=models.F('distance') + 1)

        # Ensure step is saved, as we need it to exist for the following queries
        if step.pk is None:
            step.save()

        # Construct new links, starting with self referencing link
        new_links = [WorkflowStepDependency(parent=step, child=step, distance=0)]
        new_links.extend(
            [
                WorkflowStepDependency(parent=link.parent, child=step, distance=link.distance + 1)
                for link in all_parent_links
            ]
        )
        new_links.extend(
            [
                WorkflowStepDependency(parent=step, child=link.child, distance=link.distance + 1)
                for link in all_child_links
            ]
        )

        # Create new links
        WorkflowStepDependency.objects.bulk_create(new_links, ignore_conflicts=True)
        return step


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

    def _parent_links(self, depth: Optional[int]):
        """Return the queryset of links between this step and its parents."""
        query = (
            WorkflowStepDependency.objects.filter(child=self)
            .exclude(parent=self)
            .order_by('distance', 'modified')
            .select_related('parent')
        )

        if depth is not None:
            query = query.filter(distance__lte=depth)

        return query

    def parents(self, depth: Optional[int] = None) -> List[WorkflowStep]:
        """Return all parents of this step (all steps that run prior to this step)."""
        return [link.parent for link in self._parent_links(depth)]

    def _child_links(self, depth: Optional[int]):
        """Return the queryset of links between this step and its children."""
        query = (
            WorkflowStepDependency.objects.filter(parent=self)
            .exclude(child=self)
            .order_by('distance', 'modified')
            .select_related('child')
        )

        if depth is not None:
            query = query.filter(distance__lte=depth)

        return query

    def children(self, depth: Optional[int] = None) -> List[WorkflowStep]:
        """Return all children of this step (all steps that run after this step)."""
        return [link.child for link in self._child_links(depth)]

    def append_step(self, step: WorkflowStep):
        """Add a step to the workflow, running after this step."""
        return WorkflowStepDependency.insert_step(step, parents=[self])


@receiver(pre_delete, sender=WorkflowStep)
def workflow_step_distance_adjust(sender: Type[WorkflowStep], instance: WorkflowStep, **kwargs):
    """Update the distance of all links to this step's children."""
    # Only include links that point to children of this step
    links = WorkflowStepDependency.objects.filter(child__in=instance.children())

    # Only include indirect links
    links = links.filter(distance__gte=2)

    # Subtract 1 from all relevant links
    links.update(distance=models.F('distance') - 1)


class Workflow(TimeStampedModel):
    """A model for organizing the running of workflow steps."""

    name = models.CharField(max_length=255, unique=True)
    collection = models.OneToOneField(
        Collection, on_delete=models.PROTECT, default=create_default_workflow_collection
    )

    def _steps_queryset(self, depth: Optional[int]):
        """
        Return all workflow steps, ordered from first to last.

        This function returns the steps in Bread First Search (BFS) ordering.
        """
        # Get all steps, ordered by the longest parent distance it has
        query = (
            WorkflowStep.objects.filter(workflow=self)
            .annotate(max_parent_depth=models.Max('parent_links__distance'))
            .exclude(max_parent_depth=None)  # exclude any un-linked steps
            .select_related('workflow')
            .order_by('max_parent_depth', 'modified')
        )

        if depth is not None:
            query = query.filter(max_parent_depth__lte=depth)

        return query

    def steps(self, depth: Optional[int] = None) -> List[WorkflowStep]:
        """Get all steps, ordering from most to least parent dependencies (first to last run)."""
        return list(self._steps_queryset(depth))

    def root_steps(self) -> List[WorkflowStep]:
        """Get the root steps of a workflow."""
        # Only return steps with zero parents (root steps)
        return list(self._steps_queryset(depth=0))

    def add_root_step(self, workflow_step: WorkflowStep) -> WorkflowStep:
        """
        Add a step to run at the beginning of a workflow.

        Note: There is not necessarily a single root step, and as such multiple steps
        can run at the beginning of a workflow.
        """
        # Ensure step is saved
        workflow_step.save()

        # Add self referencing step
        WorkflowStepDependency.objects.create(parent=workflow_step, child=workflow_step, distance=0)

        # Return added_step
        return workflow_step

    def insert_step(
        self,
        step: WorkflowStep,
        parents: Optional[List[WorkflowStep]] = None,
        children: Optional[List[WorkflowStep]] = None,
    ):
        """
        Insert a workflow step at an arbitrary position in the workflow.

        The parents and children arguments must each consist of a list of workflow steps that are
        already present in the workflow, or None.
        """

        # Ensure step isn't already present in the workflow
        # if step in self.steps():
        # raise ValidationError('Step already exists in this workflow.')

        return WorkflowStepDependency.insert_step(step, parents=parents, children=children)


@receiver(post_delete, sender=Workflow)
def workflow_collection_delete(sender: Type[Workflow], instance: Workflow, **kwargs):
    collection: Collection = instance.collection
    collection.delete()
