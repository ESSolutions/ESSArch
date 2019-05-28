FROM python:3.6

WORKDIR /code/ESSArch_Core
EXPOSE 8000

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE ESSArch_Core.config.settings
ENV PYTHONPATH=$PYTHONPATH:/ESSArch/config

RUN apt-get update && apt-get install -y apt-transport-https

RUN curl -sL https://deb.nodesource.com/setup_10.x | bash -
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" > /etc/apt/sources.list.d/yarn.list

RUN apt-get update && \
    apt-get install -y python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info git nodejs yarn postgresql-client netcat

# Fetch python dependencies
ADD setup.py /code/setup.py
ADD versioneer.py /code/versioneer.py
ADD README.md /code/README.md
RUN cd /code && \
    python3.6 -m pip install --upgrade pip setuptools && \
    python3.6 -m pip install -e .[postgres]

# Fetch yarn dependencies
ADD ./ESSArch_Core/frontend/static/frontend/yarn.lock /code/ESSArch_Core/frontend/static/frontend/yarn.lock
ADD ./ESSArch_Core/frontend/static/frontend/package.json /code/ESSArch_Core/frontend/static/frontend/package.json
RUN cd /code/ESSArch_Core/frontend/static/frontend && yarn

# Add the rest and build the frontend
ADD . /code
RUN cd /code/ESSArch_Core/frontend/static/frontend && yarn build:dev
