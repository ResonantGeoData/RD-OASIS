# Generated by Django 3.2.7 on 2021-09-24 19:21

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import rgd_workflow.models.workflow


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('rgd', '0003_checksumfile_created_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='DockerImage',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(max_length=255, null=True)),
                ('image_id', models.CharField(max_length=255, null=True)),
                (
                    'image_file',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='docker_images',
                        to='rgd.checksumfile',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='Workflow',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(max_length=255, unique=True)),
                (
                    'collection',
                    models.OneToOneField(
                        default=rgd_workflow.models.workflow.create_default_workflow_collection,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='rgd.collection',
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='WorkflowStep',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                (
                    'command',
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=255), size=None
                    ),
                ),
                (
                    'docker_image',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='workflow_steps',
                        to='rgd_workflow.dockerimage',
                    ),
                ),
                (
                    'workflow',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='workflow_steps',
                        to='rgd_workflow.workflow',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='WorkflowStepDependency',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                ('distance', models.PositiveIntegerField()),
                (
                    'child',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='parent_links',
                        to='rgd_workflow.workflowstep',
                    ),
                ),
                (
                    'parent',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='child_links',
                        to='rgd_workflow.workflowstep',
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name='workflowstepdependency',
            constraint=models.UniqueConstraint(
                fields=('parent', 'child'), name='unique_dependency'
            ),
        ),
        migrations.AddConstraint(
            model_name='workflowstep',
            constraint=models.UniqueConstraint(
                fields=('workflow', 'name'), name='unique_workflow_step'
            ),
        ),
        migrations.AddConstraint(
            model_name='dockerimage',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(('image_file__isnull', True), ('image_id__isnull', False)),
                    models.Q(('image_file__isnull', False), ('image_id__isnull', True)),
                    _connector='OR',
                ),
                name='single_image_source',
            ),
        ),
    ]
