#!/bin/bash

set -e

if hostname -f > /dev/null 2>&1; then
    FQDN="`hostname -f`"
else
    FQDN="`hostname`"
fi
SiteName_essarch="essarch"
ServerName_essarch="$SiteName_essarch.$FQDN"

echo "ESSARCH_DIR = $ESSARCH_DIR"
if [ ! -f $ESSARCH_DIR/config/local_essarch_settings.py ]; then
    echo "Generate settings"
    essarch settings generate -q --no-overwrite
    echo "Generate mimetypes"
    essarch mimetypes generate -q --no-overwrite
    echo "Running essarch install -q "
    essarch install -q
    ESSARCH=`python -c "import ESSArch_Core as _; print(_.__path__[0])"`
    echo "Found ESSArch in path: $ESSARCH"    
    echo "Installing SE profiles"
    python $ESSARCH/install/install_sa_profiles.py se
    #echo "Installing NO profiles"
    #python $ESSARCH/install/install_sa_profiles.py no
    echo "Installing EARK profiles"
    python $ESSARCH/install/install_sa_profiles.py eark
else
    echo "Check if any new db migrations to apply"
    django-admin migrate
fi

if [ ! -f $ESSARCH_DIR/config/httpd.conf ]; then
    echo "Configure apache http"
    cp /code/docker/templates/config/file_formats.xml $ESSARCH_DIR/config/file_formats.xml
    cp /code/docker/templates/config/httpd_mime.types $ESSARCH_DIR/config/httpd_mime.types
    cp /code/docker/templates/config/httpd.conf $ESSARCH_DIR/config/httpd.conf
    cp /code/docker/templates/config/httpd-essarch.conf $ESSARCH_DIR/config/httpd-essarch.conf
    cp /code/docker/templates/config/httpd-schema.conf $ESSARCH_DIR/config/httpd-schema.conf
    sudo ln -fs $ESSARCH_DIR/config/httpd.conf /etc/apache2/sites-enabled/httpd.conf
    sed -i "s;\(ServerName \)[^\]*;\1${ServerName_essarch};" $ESSARCH_DIR/config/httpd-essarch.conf
    sed -i "s;\(Redirect / https://\)[^\]*;\1${ServerName_essarch};" $ESSARCH_DIR/config/httpd-essarch.conf
    if [ ! -f $ESSARCH_DIR/config/certs/server_essarch.crt ]; then
        mkdir -p $ESSARCH_DIR/config/certs
        cd $ESSARCH_DIR/config/certs; openssl req -x509 -sha256 -days 3652 -newkey rsa:2048 -subj "/C=SE/ST=Stockholm/O=ES Solutions AB/CN=${ServerName_essarch}" -keyout server_essarch.key -out server_essarch.crt -nodes
    fi
fi

if [ ! -f $ESSARCH_DIR/config/certs/saml2_essarch.crt ]; then
    # SAML2 Certs
    mkdir -p $ESSARCH_DIR/config/certs
    cd $ESSARCH_DIR/config/certs; openssl req -x509 -sha256 -days 3652 -newkey rsa:2048 -subj '/C=SE/ST=Stockholm/O=ES Solutions AB/CN=${ServerName_essarch}' -keyout saml2_essarch.key -out saml2_essarch.crt -nodes
    #sudo -u arch bash -c "cd $ESSARCH_DIR/config/certs; wget --no-check-certificate https://fs.essarch.org/federationmetadata/2007-06/federationmetadata.xml -O idp_federation_metadata.xml || true"
fi

if [ /var/run/apache2/apache2.pid ]; then
    sudo rm -f /var/run/apache2/apache2.pid
fi

echo "Starting server"
#ENV="env -i $(grep -v '^#' /code/docker/templates/config/essarch_env | xargs) /bin/sh -l -c"
#ENV="env $(grep -v '^#' /code/docker/templates/config/essarch_env | xargs) /bin/sh -l -c"
#$ENV "apache2ctl -D FOREGROUND"
#sudo -E $ENV "apache2ctl -D FOREGROUND"
sudo -E PYTHONPATH=$PYTHONPATH apache2ctl -D FOREGROUND
#$ENV "${apachectl} -f ${apacheconfig} -D FOREGROUND"
#$ENV "/usr/sbin/apache2ctl -f /ESSArch/config/httpd.conf -D FOREGROUND"
