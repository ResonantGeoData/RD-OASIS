# RD-OASIS

## What is OASIS?

OASIS is a Django application designed to allow users to define and run arbitrary algorithms, tracking the progress and results of such algorithms in Django.


## The Algorithm Execution Lifecycle
These are the steps that are taken by tasks to execute an algorithm. This is generalized between Kubernetes and Celery, as the steps are the same at a high level.

![lifecycle](https://user-images.githubusercontent.com/11370025/153090818-f1721c29-db2f-412d-b035-4b3581ea6cbb.png)


## Main Components

These are the main components that make up OASIS. Each of these components is a Django model, and each entry here will contain a short description, followed by the fields associated with each.

### Algorithm
Algorithms are at the core of OASIS, and contains much of the required definitions for any process you want to run.

* **Name** - The name of the Algorithm
* **Docker Image** - The docker image (documented below) that this algorithm will use.
* **Command** - The command used to invoke your algorithm
* **Entrypoint** - If necessary, override the default entrypoint of your docker image.
* **Environment** - Any environment variables that should be passed into the container when running your algorithm.
* **GPU** - Whether GPU access is required by this algorithm.


### Algorithm Task
Algorithm tasks are individual runs of an algorithm. Algorithm tasks are isolated from each other, only sharing the underlying algorithm itself.

  * **Algorithm** - The algorithm which this task belongs to.
  * **Status** - The current status of this task (its progress in the task lifecycle). One of:
    * Created
    * Queued
    * Running
    * Failed
    * Succeeded
  * **Output Log** - The output (stdout) of the algorithm, stored as a text field.
  * **Input Dataset** - The dataset containing the input, to be mounted to and copied into the `/<working_dir>/input` directory.
  * **Output Dataset** - The dataset containing any files produced by the algorithm (any files placed into the `/<working_dir>/output` directory).


### Docker Image
This is the defintion of the image to be used when running your algorithm. This docker/container image contains the necessary environment to run your algorithm. Generally, any necessary files, libraries, packages, etc. that are required by your algorithm to run, are included in this image.

* **Name** - The name of the image
* **Image ID** - The id of this image on [Docker Hub](https://hub.docker.com/).
* **Image File** - If this image is uploaded directly to the API, instead of on docker hub, then this field points to the file which contains it.

### Dataset
A Dataset is a container of files to be used by algorithms. This is used to facilitate both input to and output from an algorithm task.

  * **Name** - The name of the dataset.
  * **Files** - The files contained within this dataset.
  * **Size** - The size (in bytes) of this dataset.
