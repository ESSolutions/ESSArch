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

FROM python:3.6-slim AS base

WORKDIR /code

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH={$PYTHONPATH}:/ESSArch/config

# TODO: Install deps for all db backends, or atleast give a user the option to, especially needed for prod

RUN apt-get update \
    && mkdir -p /usr/share/man/man1 \
    && mkdir -p /usr/share/man/man7 \
    && apt-get install -y --no-install-recommends \
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
        shared-mime-info

RUN pip install --upgrade pip setuptools

FROM base AS docsbuilder
WORKDIR /docs

RUN apt-get install -y build-essential

ADD requirements/docs.txt /deps.txt
RUN pip install -r /deps.txt

ADD ESSArch_Core/docs /docs
RUN make html

FROM base AS wheelbuilder

RUN apt-get install -y build-essential \
    # mysql/mariadb
    default-libmysqlclient-dev \
    # odbc
    unixodbc \
    unixodbc-dev \
    # ldap
    libsasl2-dev \
    libldap2-dev \
    libssl-dev

RUN pip install --upgrade wheel

ADD requirements/base.txt /deps.txt
RUN pip wheel -w /wheels -r /deps.txt

# Add source
ADD . /code
RUN pip wheel -w /wheels .[s3,ldap,saml2,libreoffice_file_conversion,mssql,mysql,postgres,logstash]

RUN pip install --no-index -f /wheels ESSArch


RUN mkdir -p /ESSArch/config /ESSArch/log
RUN essarch settings generate -q --no-overwrite

# TODO: Add built docs to wheel or have it at separate path and routed to by webserver?

# TODO: Add built static to wheel or have it at separate path and routed to by webserver?
RUN django-admin collectstatic -i node_modules --noinput

FROM base AS prod

EXPOSE 8000

# Copy built frontend
COPY --from=build-frontend /code/build /code/ESSArch_Core/frontend/static/frontend/build

# Copy built wheels
COPY --from=wheelbuilder /wheels /wheels

RUN pip install --no-index -f /wheels ESSArch
RUN rm -r /wheels

FROM base AS dev

EXPOSE 8000

# install yarn
RUN apt-get update && apt-get install -y build-essential curl apt-transport-https

RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update \
    && apt-get install -y --no-install-recommends yarn


# Copy built wheels
COPY --from=wheelbuilder /wheels /wheels

RUN pip install -f /wheels -e .

# Copy compiled executable and runtime directories for watchman
COPY --from=watchman_builder /usr/local/bin/watchman* /usr/local/bin/
COPY --from=watchman_builder /usr/local/var/run/watchman /usr/local/var/run/watchman

RUN pip install --upgrade pywatchman

# Copy built frontend
COPY --from=build-frontend /code/build /code/ESSArch_Core/frontend/static/frontend/build

# TODO: Copy built docs

# Add source
ADD . /code
