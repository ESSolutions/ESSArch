FROM python:3.6

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH=$PYTHONPATH:/ESSArch/config

COPY . /code
WORKDIR /code

RUN apt-get update && apt-get install apt-transport-https

RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update && \
    apt-get install -y python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info git nodejs yarn postgresql-client

RUN python3.6 -m pip install --upgrade pip setuptools
RUN python3.6 -m pip install -e .[postgres]

RUN mkdir -p /ESSArch/data/etp/reception
RUN mkdir -p /ESSArch/data/etp/prepare
RUN mkdir -p /ESSArch/data/eta/reception

WORKDIR /code/ESSArch_Core/frontend/static/frontend
RUN yarn && yarn build:dev

WORKDIR /code/ESSArch_Core

EXPOSE 8000
