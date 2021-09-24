# Generated by Django 3.2.7 on 2021-09-24 19:46

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('rgd_workflow', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowStepRun',
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
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('created', 'Created but not queued'),
                            ('queued', 'Queued for processing'),
                            ('running', 'Running'),
                            ('failed', 'Failed'),
                            ('success', 'Succeeded'),
                        ],
                        default='queued',
                        max_length=16,
                    ),
                ),
                ('output', models.TextField()),
                (
                    'workflow_step',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='runs',
                        to='rgd_workflow.workflowstep',
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
