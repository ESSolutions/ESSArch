FROM node:lts-alpine AS build-frontend

WORKDIR /code
RUN apk update && apk add python
COPY package.json yarn.lock webpack.config.babel.js tsconfig.json ./
RUN yarn
COPY ESSArch_Core/frontend/static/frontend /code/ESSArch_Core/frontend/static/frontend
RUN yarn build:prod

FROM python:3.7-buster as base

RUN pip install --no-cache-dir --upgrade pip setuptools
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libffi-dev \
        libgdk-pixbuf2.0-0 \
        libmagickwand-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpq-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libxslt-dev \
        netcat \
        pkg-config \
        postgresql-client \
        python3-cffi \
        shared-mime-info \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

ADD requirements /code/requirements
ADD setup.py /code/setup.py
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
RUN essarch settings generate -p /code/local_essarch_settings.py
RUN for lang in "en" "sv"; do make html LANGUAGE="$lang"; done

WORKDIR /code

FROM base

WORKDIR /code
EXPOSE 8000

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH={$PYTHONPATH}:/ESSArch/config

RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update && apt-get install -y \
    curl \
    gettext \
    git \
    vim \
    yarn

ADD requirements/tests.txt /code/requirements/tests.txt
RUN pip install --no-cache-dir -r /code/requirements/tests.txt
RUN pip install --no-cache-dir -e .[mysql,postgres]

# Copy built frontend
COPY --from=build-frontend /code/ESSArch_Core/frontend/static/frontend/build /code/ESSArch_Core/frontend/static/frontend/build

# Copy built docs
COPY --from=build-docs /code/ESSArch_Core/docs/_build /code/ESSArch_Core/docs/_build

# Add source
ADD . /code
