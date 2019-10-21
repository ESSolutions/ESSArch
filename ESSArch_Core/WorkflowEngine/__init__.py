"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import logging

import celery

default_app_config = 'ESSArch_Core.WorkflowEngine.apps.WorkflowEngineConfig'
logger = logging.getLogger('essarch.workflowengine')


def get_workers(rabbitmq):
    if rabbitmq.get('error'):
        logger.error("RabbitMQ seems down. Wont get stats of celery workers.")
        return None

    try:
        return celery.current_app.control.inspect().stats()
    except Exception:
        logger.exception("Error when checking stats of celery workers.")
        return None
