ARG ELK_VERSION

FROM docker.elastic.co/elasticsearch/elasticsearch-oss:${ELK_VERSION}

# Install plugins
RUN elasticsearch-plugin install --batch ingest-attachment
