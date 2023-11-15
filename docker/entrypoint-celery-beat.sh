#!/bin/bash

# safety switch, exit script if there's error. Full command of shortcut `set -e`
set -o errexit
# safety switch, uninitialized variables will stop script. Full command of shortcut `set -u`
set -o nounset

CELERY_BIN=${CELERY_BIN="/usr/local/bin/celery"}
CELERY_APP=${CELERY_APP="ESSArch_Core.config"}
CELERYBEAT_CHDIR=${CELERYBEAT_CHDIR="${ESSARCH_DIR}"}
CELERYBEAT_OPTS=${CELERYBEAT_OPTS="--schedule=${ESSARCH_DIR}/config/essarch/celerybeat-schedule"}
CELERYBEAT_LOG_LEVEL=${CELERYBEAT_LOG_LEVEL=INFO}
CELERYBEAT_LOG_FILE=${CELERYBEAT_LOG_FILE="${ESSARCH_DIR}/log/celery_beat.log"}
CELERYBEAT_PID_FILE=${CELERYBEAT_PID_FILE="${ESSARCH_DIR}/log/proc/celery_beat.pid"}
CELERYBEAT_USER=${CELERYBEAT_USER="arch"}
CELERYBEAT_GROUP=${CELERYBEAT_GROUP="arch"}

# tear down function
teardown()
{
    echo " Signal caught..."
    echo "Stopping celery beat ..."
    kill -s TERM "$child" 2> /dev/null
    echo "Stopped process. Exiting..."
    exit 1
}

# start celery worker via `celery multi` with declared logfile for `tail -f`
rm -f ${ESSARCH_DIR}/log/proc/celery_beat.pid
${CELERY_BIN} -A ${CELERY_APP} beat \
  --pidfile=${CELERYBEAT_PID_FILE} \
  --logfile=${CELERYBEAT_LOG_FILE} --loglevel=${CELERYBEAT_LOG_LEVEL} ${CELERYBEAT_OPTS} &

# start trapping signals (docker sends `SIGTERM` for shudown)
trap "teardown" SIGTERM SIGINT SIGQUIT SIGHUP ERR

# tail all the logs continuously to console for `docker logs` to see
tail -f ${ESSARCH_DIR}/log/celery_beat.log &

# capture process id of `tail` for tear down
child=$!

# waits for `tail -f` indefinitely and allows external signals,
# including docker stop signals, to be captured by `trap`
wait "$child"