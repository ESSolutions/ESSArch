# ESSArch [![Build Status](https://travis-ci.org/ESSolutions/ESSArch.svg?branch=master)](https://travis-ci.org/ESSolutions/ESSArch)  [![codecov](https://codecov.io/gh/ESSolutions/ESSArch/branch/master/graph/badge.svg)](https://codecov.io/gh/ESSolutions/ESSArch)

# Getting started

### Using docker

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

#### Important
Elasticsearch requires `vm.max_map_count` to be at least 262144, see
[Install Elasticsearch with Docker](https://www.elastic.co/guide/en/elasticsearch/reference/6.5/docker.html#docker-cli-run-prod-mode) for more information

# Contributing

Please see `CONTRIBUTING.md` for information about contributing to the project.

# Service and support

Service and support on ESSArch Core is regulated in maintenance contract with ES Solutions AB. A case is registered on the support portal http://projects.essolutions.se
