ARG ELK_VERSION

FROM docker.elastic.co/elasticsearch/elasticsearch-oss:7.6.1

# Install plugins
RUN elasticsearch-plugin install --batch ingest-attachment
