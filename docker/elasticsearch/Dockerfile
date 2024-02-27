ARG ELASTICSEARCH_DISTRO
ARG ELASTICSEARCH_VERSION

FROM ${ELASTICSEARCH_DISTRO}:${ELASTICSEARCH_VERSION}

# Install plugins
RUN elasticsearch-plugin install --batch ingest-attachment

## Certs
#RUN yum install -y openssl
WORKDIR /usr/share/elasticsearch/config
# Root CA
RUN openssl genrsa -out root-ess-ca-key.pem 2048
RUN openssl req -new -x509 -sha256 -key root-ess-ca-key.pem -out root-ess-ca.pem -subj '/C=SE/ST=Stockholm/O=ES Solutions AB/CN=elasticsearch'
# Admin cert
RUN openssl genrsa -out admin-ess-key-temp.pem 2048
RUN openssl pkcs8 -inform PEM -outform PEM -in admin-ess-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out admin-ess-key.pem
RUN openssl req -new -key admin-ess-key.pem -out admin-ess.csr -subj '/C=SE/ST=Stockholm/O=ES Solutions AB/CN=elasticsearch'
RUN openssl x509 -req -in admin-ess.csr -CA root-ess-ca.pem -CAkey root-ess-ca-key.pem -CAcreateserial -sha256 -out admin-ess.pem
# Node cert
RUN openssl genrsa -out node-ess-key-temp.pem 2048
RUN openssl pkcs8 -inform PEM -outform PEM -in node-ess-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out node-ess-key.pem
RUN openssl req -new -key node-ess-key.pem -out node-ess.csr -subj '/C=SE/ST=Stockholm/O=ES Solutions AB/CN=elasticsearch'
RUN openssl x509 -req -in node-ess.csr -CA root-ess-ca.pem -CAkey root-ess-ca-key.pem -CAcreateserial -sha256 -out node-ess.pem
# Cleanup
RUN rm admin-ess-key-temp.pem
RUN rm admin-ess.csr
RUN rm node-ess-key-temp.pem
RUN rm node-ess.csr