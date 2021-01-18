## itinerum-dashboard-api

*This is a working document.*

This repository contains the Flask-Restful API for the ReactJS web dashboard. The API handles survey creation/monitoring, management of web users, and data export, and the accompanying Dockerfile/Gitlab-CI config files.

##### Development Guide

The most important guideline is the `master` branch should always contain a working version of the application with appropriate unit tests. New features should be developed in a branch of the master named  as `feature-name-action`, for example: `survey-wizard-upsert-dropdown-options`.

Committing code should happen in the following order:

- Feature is developed or updated within its own named branch
- After all tests pass, feature is merged to `master` branch
- `master` branch is merged to `testing`, which tests and builds the Docker container on the CI server
- `testing` branch is merged to `staging` to deploy the image to AWS ECR
- Developer either checks out their feature branch to continue work, or returns to step 1 and creates a new branch

### Getting Started

It is recommended to create a single shared virtualenv for the Itinerum APIs with [virtualenv-wrapper](http://virtualenvwrapper.readthedocs.io), which makes virtualenvs friendlier to user. In the examples that follow, a virtualenv name of `itapi` will be used.

#### Dependencies

Itinerum currently only supports Python 2.7 and is not fully tested with Python 3. Necessary system packages include PostgreSQL and gcc, others should be resolved as prompted.

Python dependencies can be installed with one command:

```bash
(itapi) $ pip install -r requirements.txt
```

#### Database

###### Setup

First, create the development PostgreSQL database named `itinerum_dev` with:

```bash
$ createdb itinerum_dev
```

The database schemas are handled by Alembic via flask-migrate with its configuration found in the `migrations` directory. After creating the database needed for development (`itinerum_dev`), testing (`itinerum_test`) , or production (`itinerum`), apply the current migration version:

```bash
$ (itapi) python manage.py db upgrade
```

###### Changes

When the database schema is updated, a new migration version must be generated and applied with:

```bash
(itapi) $ python manage.py db migrate
(itapi) $ python manage.py db upgrade
```

This repository can then be pulled to the database managing servers for updating remote databases.

#### Development 

The server looks for an environment variable named `CONFIG` to determine whether to run as development, production or testing. Set this variable as `CONFIG=debug` in `~/.bash_profile`, `~/.profile`, or through Windows depending on the system. The development server with auto-reload can be then run with:

```bash
(itapi) $ python manage.py runserver
```

The development server is run in conjunction with the ReactJS [itinerum-dashboard](https://gitlab.com/itinerum/itinerum-dashboard) project to view changes in real-time. Whenever new functionality is added, a new test must be added to the `./dashboard/tests/` directory to be tested during the Gitlab-CI workflow. 

###### Creating a Survey

In order to create a survey, a new active survey token must be generated through the [admin interface](https://gitlab.com/itinerum/itinerum-admin). A new survey can be created at the hidden URL: [http://\<development-ip-or-localhost>:8080/new](http://\<development-ip-or-localhost>:8080/new). An active survey token and unique email is necessary for each new survey.

###### Adding Tests

New tests should be added for each feature added within the the `./dashboard/tests/` directory. Tests can be run manually by running:

```bash
(itapi) $ python manage.py test
```

###### Docker

For local testing of the Docker stages, the project can be built with:

```bash
$ docker build -t itinerum-dashboard-api:latest .
```

Edit `./conf/dev_env` as need and run the compiled Docker environment with:

```bash
$ docker run -d -p 9000:9000 --env-file=conf/development_docker --privileged itinerum-dashboard-api:latest
```

where *dev_env* is a file containing your local environment variables. The portal can then be reached at: **http://\<docker-machine-address>:9000/dashboard/v1/**

*Note*: It can be tricky to get the Docker version of the application communicate to the PostgreSQL database on the host system. Be sure that the `dev_env` file reflects the LAN address of the Host system and an existing database. It is useful to watch for events in the `postgresql.log` file to diagnose issues here.

###### Using the development database

A database is accessible on the TRIP Lab build server for development purposes. To access, the development containers SSH must be added to create a tunnel for remote forwarding of the PostgreSQL port:

```bash
$ ssh -L 54320:localhost:54320 trip
```

On Docker for OS X, the `./conf/dev_env` should then specify the following:

```
CONFIG=debug
IT_DASHBOARD_PORT=5000
IT_SECRET_KEY=changeme
IT_POSTGRES_URI=postgresql://user:password@docker.for.mac.localhost:54320/itinerum_dev
REDIS_SERVER=redis://localhost:6379
```

with the appropriate database username and password. The `docker.for.windows.localhost` should work in-place for Windows environments.

#### Deployment

The `master` branch contains the latest version of the tested dashboard. When new contributions are ready to go live, the `master` branch is merged into the `testing` branch. The *testing* Gitlab-CI routine will build the Docker image and run the full suite of unittests. In the case of the web dashboard, a development version will be deployed to: [https://api.testing.itinerum.ca/dashboard/v1/](https://api.testing.itinerum.ca/dashboard/v1/). When all tests pass, the `master` branch can then pulled to the `production` branch.

