from pathlib import Path

from setuptools import find_packages, setup

readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    with readme_file.open() as f:
        long_description = f.read()
else:
    # When this is first installed in development Docker, README.md is not available
    long_description = ''

setup(
    name='RD-OASIS',
    version='0.1.0',
    description='',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='Apache 2.0',
    author='Kitware, Inc.',
    author_email='rgd@kitware.com',
    keywords='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 3.0',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python',
    ],
    python_requires='>=3.8',
    packages=find_packages(exclude=['django-rgd-workflow']),
    include_package_data=True,
    install_requires=[
        'celery',
        'django>=4',
        'django-admin-display',
        'django-allauth',
        'django-configurations[database,email]',
        'django-cleanup',
        'django-crispy-forms',
        'django-extensions',
        'django-filter',
        'django-oauth-toolkit',
        'djangorestframework',
        'djproxy',
        'drf-extensions',
        'drf-yasg',
        'flower',
        'gputil',
        'rules',
        'zipstream==1.1.4',
        # Production-only
        'django-composed-configuration[prod]>=0.21.0',
        'django-s3-file-field[boto3]',
        'gunicorn',
        'boto3',
        # RGD
        'django-rgd[configuration]',
        'django-rgd-imagery',
    ],
    dependency_links=['https://girder.github.io/large_image_wheels'],
    extras_require={
        'dev': [
            'django-composed-configuration[dev]>=0.21.0',
            'django-debug-toolbar',
            'django-s3-file-field[minio]',
            'ipython',
            'tox',
            'boto3-stubs[eks]',
        ],
        'worker': [
            'django-rgd-imagery[worker]',
            'docker',
        ],
        'fuse': [
            'django-rgd[configuration,fuse]',
        ],
        'k8s': [
            'kubernetes',
            'awscli',
        ],
    },
)
