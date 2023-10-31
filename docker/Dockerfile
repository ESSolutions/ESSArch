############## BUILD-FRONTEND ##############
FROM node:lts-alpine AS build-frontend

WORKDIR /code
RUN apk update && apk add g++ git make python3
COPY .git ./.git
COPY package.json yarn.lock webpack.common.babel.js webpack.dev.babel.js webpack.prod.babel.js tsconfig.json ./
COPY ESSArch_Core/frontend/static/frontend ./ESSArch_Core/frontend/static/frontend
RUN yarn install
RUN yarn build:prod
RUN rm -rf ./node_modules


############## BASE-SLIM ##############
FROM python:3.11-slim-bookworm as base-slim

RUN groupadd "arch" && \
    useradd "arch" -g "arch" -G sudo,tape -m -s /bin/bash && \
    echo "arch:arch" | chpasswd

RUN pip install --no-cache-dir --upgrade pip setuptools
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    libcairo2-dev \
    libffi-dev \
    libldap2-dev \
    libpango1.0-dev \
    libsasl2-dev \
    libssl-dev \
    netcat-openbsd \
    postgresql-client \
    python3-cffi \
    unixodbc-dev \
    git \
    vim \
    curl \
    procps \
    sudo \
    xmlsec1 \
    && rm -rf /var/lib/apt/lists/*

RUN echo "arch    ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers


############## BUILD-DOCS ##############
FROM base-slim as build-docs
WORKDIR /code/ESSArch_Core/docs

# Add source
ADD . /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /ESSArch/log

# Install docs requirements
RUN pip install --no-cache-dir -e /code[docs]

# Build docs
#ENV ESSARCH_DIR=/code
RUN mkdir -p /code/config
RUN mkdir -p /code/log
RUN essarch settings generate --debug --overwrite -p /code/config/local_essarch_settings.py
ENV PYTHONPATH=/code/config
RUN rm -rf /code/ESSArch_Core/docs/_build
RUN for lang in "en" "sv"; do make html LANGUAGE="$lang"; done


############## BUILD-SDIST ##############
FROM base-slim as build-sdist
WORKDIR /code

# Add source
ADD . /code

# Copy built frontend
COPY --from=build-frontend /code/ESSArch_Core/frontend/static/frontend/build /code/ESSArch_Core/frontend/static/frontend/build

# Copy built docs
COPY --from=build-docs /code/ESSArch_Core/docs/_build /code/ESSArch_Core/docs/_build

RUN git status
RUN git describe --tags --dirty --always --long
RUN python setup.py sdist


############## BASE ##############
FROM base-slim as base
WORKDIR /code

ENV ESSARCH_DIR=/ESSArch
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH=/ESSArch/config

# Libreoffice
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir datasette


############## PROD ##############
FROM base as prod
EXPOSE 443

ARG ESSARCH_DIR=./
ARG PYTHONPATH=./config

RUN apt-get update && apt-get install -y --no-install-recommends \
    apache2 \
    apache2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN a2enmod setenvif mime socache_shmcb ssl proxy proxy_http headers rewrite speling remoteip

# Copy built sdist
COPY --from=build-sdist /code/dist ./dist
ADD docker ./docker

RUN pip install --no-cache-dir --upgrade `ls -t dist/ESSArch-*.tar.gz | head -n1`[apache,libreoffice_file_conversion,mysql,saml2,ldap]

RUN mkdir -p ./config
RUN mkdir -p ./log
RUN essarch settings generate --debug --overwrite -p ./config/local_essarch_settings.py
RUN django-admin collectstatic --noinput
RUN rm -rf ./log
RUN rm ./config/local_essarch_settings.py

ADD docker/templates ./templates

RUN export MOD_WSGI=`python -c "import mod_wsgi as _; print(_.__path__[0])"`; cp $MOD_WSGI/server/mod_wsgi-py311.cpython-311-x86_64-linux-gnu.so ./config/essarch/mod_wsgi.so
RUN export ESSARCH=`python -c "import ESSArch_Core as _; print(_.__path__[0])"`; cp $ESSARCH/config/wsgi.py ./config/essarch/wsgi.py

# Use python version that match installed libreoffice for unoconv
RUN sed -i 's/^#!\/usr\/local\/bin\/python/#!\/usr\/bin\/python3/' /usr/local/bin/unoconv

RUN chown -R arch:arch /code
USER arch


############## DEV ##############
FROM base as dev
EXPOSE 8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    gpg \
    watchman \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
ENV NODE_MAJOR=16
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg arch=amd64] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list

RUN curl -sL https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | tee /usr/share/keyrings/yarnkey.gpg >/dev/null
RUN echo "deb [signed-by=/usr/share/keyrings/yarnkey.gpg] https://dl.yarnpkg.com/debian stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    yarn \
    && rm -rf /var/lib/apt/lists/*

# Add source
ADD . /code

# Copy built frontend
COPY --from=build-frontend /code/ESSArch_Core/frontend/static/frontend/build /code/ESSArch_Core/frontend/static/frontend/build

# Copy built docs
COPY --from=build-docs /code/ESSArch_Core/docs/_build /code/ESSArch_Core/docs/_build

RUN pip install --no-cache-dir -e .[libreoffice_file_conversion,mysql,saml2,ldap,docs,tests,dev,lint]

# RUN mkdir -p ./config/essarch

# Use python version that match installed libreoffice for unoconv
RUN sed -i 's/^#!\/usr\/local\/bin\/python/#!\/usr\/bin\/python3/' /usr/local/bin/unoconv
