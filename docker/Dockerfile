FROM python:3.7 AS watchman_builder

# Install build dependencies
RUN apt-get update && apt-get install -y apt-transport-https wget

# Set environment variables
ENV WATCHMAN_VERSION=4.9.0

# Download watchman source code
RUN cd /tmp \
 && wget -O watchman.tar.gz "https://github.com/facebook/watchman/archive/v${WATCHMAN_VERSION}.tar.gz" \
 && tar -xz -f watchman.tar.gz -C /tmp/ \
 && rm -rf watchman.tar.gz

# Build watchman from source
RUN cd /tmp/watchman-${WATCHMAN_VERSION} \
 && ./autogen.sh \
 && ./configure --enable-lenient \
 && make \
 && make install \
 && cd $HOME \
 && rm -rf /tmp/*

FROM node:alpine AS build-frontend

WORKDIR /code
COPY ESSArch_Core/frontend/static/frontend/package.json ESSArch_Core/frontend/static/frontend/yarn.lock ./
RUN yarn
COPY ESSArch_Core/frontend/static/frontend ./
RUN yarn build:prod

FROM python:3.7-slim

WORKDIR /code
EXPOSE 8000

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH={$PYTHONPATH}:/ESSArch/config

ADD setup.py /code/setup.py
ADD versioneer.py /code/versioneer.py
ADD README.md /code/README.md

RUN apt-get update \
    && mkdir -p /usr/share/man/man1 \
    && mkdir -p /usr/share/man/man7 \
    && apt-get install -y --no-install-recommends \
        gcc \
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
    && pip install --no-cache-dir --upgrade pip setuptools pywatchman \
    && pip install --no-cache-dir -e .[mysql,postgres,s3,tests] \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove gcc

# Copy compiled executable and runtime directories for watchman
COPY --from=watchman_builder /usr/local/bin/watchman* /usr/local/bin/
COPY --from=watchman_builder /usr/local/var/run/watchman /usr/local/var/run/watchman

# Copy built frontend
COPY --from=build-frontend /code/build /code/ESSArch_Core/frontend/static/frontend/build

# Add source
ADD . /code

