FROM python:3.6 AS watchman_builder

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
 && ./configure \
 && make \
 && make install \
 && cd $HOME \
 && rm -rf /tmp/*

FROM python:3.6-slim

WORKDIR /code/ESSArch_Core
EXPOSE 8000

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH=$PYTHONPATH:/ESSArch/config

RUN apt-get update && apt-get install -y apt-transport-https
RUN apt-get install -y curl

RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" > /etc/apt/sources.list.d/yarn.list

RUN apt-get update \
    && mkdir -p /usr/share/man/man1 \
    && mkdir -p /usr/share/man/man7 \
    && apt-get install -y --no-install-recommends \
        python3-cffi \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        nodejs \
        yarn \
        postgresql-client \
        netcat \
        gcc \
        libpq-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libxslt-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Fetch python dependencies
ADD setup.py /code/setup.py
ADD versioneer.py /code/versioneer.py
ADD README.md /code/README.md
RUN cd /code && \
    python3.6 -m pip install --upgrade pip setuptools pywatchman && \
    python3.6 -m pip install -e .[postgres,tests]

RUN apt-get purge -y --auto-remove gcc

# Fetch yarn dependencies
ADD ./ESSArch_Core/frontend/static/frontend/yarn.lock /code/ESSArch_Core/frontend/static/frontend/yarn.lock
ADD ./ESSArch_Core/frontend/static/frontend/package.json /code/ESSArch_Core/frontend/static/frontend/package.json
RUN cd /code/ESSArch_Core/frontend/static/frontend && yarn

# Copy compiled executable and runtime directories for watchman:
COPY --from=watchman_builder /usr/local/bin/watchman* /usr/local/bin/
COPY --from=watchman_builder /usr/local/var/run/watchman /usr/local/var/run/watchman

# Add the rest and build the frontend
ADD . /code

RUN cd /code/ESSArch_Core/frontend/static/frontend && \
        yarn build:dev && \
        rm -rf /code/ESSArch_Core/frontend/static/frontend/node_modules
