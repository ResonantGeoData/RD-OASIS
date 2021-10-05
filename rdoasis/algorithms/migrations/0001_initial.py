# Generated by Django 3.2.7 on 2021-10-05 20:31

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('rgd', '0004_alter_checksumfile_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Algorithm',
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
                ('command', models.CharField(blank=True, default=None, max_length=1000, null=True)),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
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
                ('image_id', models.CharField(blank=True, max_length=255, null=True)),
                (
                    'image_file',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='docker_images',
                        to='rgd.checksumfile',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='AlgorithmTask',
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
                ('output_log', models.TextField(blank=True, null=True)),
                (
                    'algorithm',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tasks',
                        to='algorithms.algorithm',
                    ),
                ),
                (
                    'output_dataset',
                    models.ManyToManyField(
                        blank=True, related_name='algorithm_tasks', to='rgd.ChecksumFile'
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='algorithm',
            name='docker_image',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='workflow_steps',
                to='algorithms.dockerimage',
            ),
        ),
        migrations.AddField(
            model_name='algorithm',
            name='input_dataset',
            field=models.ManyToManyField(
                blank=True, related_name='algorithms', to='rgd.ChecksumFile'
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
