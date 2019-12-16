# ESSArch [![Build Status](https://github.com/ESSolutions/ESSArch/workflows/Tests/badge.svg)](https://github.com/ESSolutions/ESSArch) [![codecov](https://codecov.io/gh/ESSolutions/ESSArch/branch/master/graph/badge.svg)](https://codecov.io/gh/ESSolutions/ESSArch)

# Getting started

### Using docker

#### Important

Elasticsearch requires `vm.max_map_count` to be at least 262144, see
[Install Elasticsearch with Docker](https://www.elastic.co/guide/en/elasticsearch/reference/6.5/docker.html#docker-cli-run-prod-mode) for more information

1. Enter the `docker` directory and start the services

```
$ cd docker
$ docker-compose up -d
```

2. Wait for the `essarch` service to start by examining the logs

```
$ docker-compose logs -f essarch
```

3. Finally visit `http://localhost:8000` in your browser

# Contributing

Please see `CONTRIBUTING.md` for information about contributing to the project.

### Pre-commit hooks

To keep the source code style consistent we use multiple packages to
warn about and fix any irregularities.

To automatically run these before commiting one can use pre-commit hooks.
Pre-commit hooks in ESSArch are managed using [`pre-commit`](https://pre-commit.com).

Install the application and run the following to install all hooks used in ESSArch.

```
$ pre-commit install
```

Now whenever you run `git commit`, all hooks defined in `.pre-commit-config.yaml` will verify the code.

## Resources
* [Documentation](https://docs.essarch.org/)
* [ES Solutions website](http://essolutions.se)

# Service and support

Service and support on ESSArch Core is regulated in maintenance contract with ES Solutions AB. A case is registered on the support portal http://projects.essolutions.se
