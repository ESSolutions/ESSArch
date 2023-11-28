#!/bin/bash

# safety switch, exit script if there's error. Full command of shortcut `set -e`
set -o errexit
# safety switch, uninitialized variables will stop script. Full command of shortcut `set -u`
set -o nounset

CELERYD_NODES=${CELERYD_NODES="worker_celery worker_validation worker_file_operation worker_io_disk worker_io_tape"}
CELERY_BIN=${CELERY_BIN="/usr/local/bin/celery"}
CELERY_APP=${CELERY_APP="ESSArch_Core.config"}
CELERYD_CHDIR=${CELERYD_CHDIR="${ESSARCH_DIR}"}
CELERYD_OPTS=${CELERYD_OPTS="-Q:worker_celery celery -c:worker_celery 1 -Q:worker_validation validation -c:worker_validation 4 -Q:worker_file_operation file_operation -c:worker_file_operation 4 -Q:worker_io_disk io_disk -c:worker_io_disk 4 -Q:worker_io_tape io_tape -c:worker_io_tape 4 -Ofair"}
CELERYD_LOG_LEVEL=${CELERYD_LOG_LEVEL=INFO}
CELERYD_LOG_FILE=${CELERYD_LOG_FILE="${ESSARCH_DIR}/log/celery_%N.log"}
CELERYD_PID_FILE=${CELERYD_PID_FILE="${ESSARCH_DIR}/log/proc/celery_%N.pid"}
CELERYD_USER=${CELERYD_USER="arch"}
CELERYD_GROUP=${CELERYD_GROUP="arch"}

# tear down function
teardown()
{
    echo " Signal caught..."
    echo "Stopping celery multi gracefully..."
    
    # send shutdown signal to celery workser via `celery multi`
    # command must mirror some of `celery multi start` arguments
    ${CELERY_BIN} -A ${CELERY_APP} multi stopwait ${CELERYD_NODES} \
      --pidfile=${CELERYD_PID_FILE} \
      --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}
    
    echo "Stopped celery multi..."
    echo "Stopping last waited process"
    kill -s TERM "$child" 2> /dev/null
    echo "Stopped last waited process. Exiting..."
    exit 1
}

# start celery worker via `celery multi` with declared logfile for `tail -f`
rm -f ${ESSARCH_DIR}/log/proc/celery_*.pid
${CELERY_BIN} -A ${CELERY_APP} multi start ${CELERYD_NODES} \
  --pidfile=${CELERYD_PID_FILE} \
  --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}

# start trapping signals (docker sends `SIGTERM` for shudown)
trap "teardown" SIGTERM SIGINT SIGQUIT SIGHUP ERR

# tail all the logs continuously to console for `docker logs` to see
tail -f $(for i in $CELERYD_NODES; do echo ${ESSARCH_DIR}/log/celery_${i}.log; done) &

# capture process id of `tail` for tear down
child=$!

# waits for `tail -f` indefinitely and allows external signals,
# including docker stop signals, to be captured by `trap`
wait "$child"