FROM node:lts-alpine AS build-frontend

WORKDIR /code
RUN apk update && apk add g++ git make python3
COPY package.json yarn.lock webpack.common.babel.js webpack.dev.babel.js tsconfig.json ./
RUN yarn
COPY ESSArch_Core/frontend/static/frontend /code/ESSArch_Core/frontend/static/frontend
COPY ./.git .git
RUN yarn build:dev

FROM python:3.9-bullseye as base

RUN pip install --no-cache-dir --upgrade pip setuptools
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    libcairo2-dev \
    libffi-dev \
    libldap2-dev \
    libpango1.0-dev \
    libsasl2-dev \
    libssl-dev \
    netcat \
    postgresql-client \
    python3-cffi \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Libreoffice
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice

ADD requirements /code/requirements
ADD setup.py /code/setup.py
ADD setup.cfg /code/setup.cfg
ADD versioneer.py /code/versioneer.py
ADD README.md /code/README.md

RUN pip install --no-cache-dir -e /code

FROM base as build-docs

WORKDIR /code/ESSArch_Core/docs
RUN mkdir -p /ESSArch/log

# Install docs requirements
ADD requirements/docs.txt /code/requirements/docs.txt
RUN pip install -r /code/requirements/docs.txt

# Add source
ADD . /code

# Build docs
RUN mkdir -p /code/config
RUN mkdir -p /code/log
RUN essarch settings generate --debug --overwrite -p /code/config/local_essarch_settings.py
ENV PYTHONPATH=/code/config
RUN for lang in "en" "sv"; do make html LANGUAGE="$lang"; done

WORKDIR /code

FROM base

WORKDIR /code
EXPOSE 8000

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH=/ESSArch/config:/ESSArch/plugins

RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -

RUN apt-get update && apt-get install -y \
    curl \
    gettext \
    git \
    vim \
    nodejs \
    yarn

ADD requirements/optional.txt /code/requirements/optional.txt
ADD requirements/tests.txt /code/requirements/tests.txt
RUN pip install --no-cache-dir -r /code/requirements/optional.txt
RUN pip install --no-cache-dir -r /code/requirements/tests.txt
RUN pip install --no-cache-dir -e .[mysql,postgres,logstash]
RUN pip install --no-cache-dir sentry-sdk
RUN pip install --no-cache-dir django-sslserver
RUN pip install --no-cache-dir datasette

# Copy built frontend
COPY --from=build-frontend /code/ESSArch_Core/frontend/static/frontend/build /code/ESSArch_Core/frontend/static/frontend/build

# Copy built docs
COPY --from=build-docs /code/ESSArch_Core/docs/_build /code/ESSArch_Core/docs/_build

# Use python version that match installed libreoffice for unoconv
RUN sed -i 's/^#!\/usr\/local\/bin\/python/#!\/usr\/bin\/python3/' /usr/local/bin/unoconv

# Add source
ADD . /code
