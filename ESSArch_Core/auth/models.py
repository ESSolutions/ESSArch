"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import logging

from django.contrib.auth.models import User
from django.db import models

from picklefield.fields import PickledObjectField


class UserProfile(models.Model):
    DEFAULT_IP_LIST_COLUMNS = [
        'label', 'object_identifier_value', 'responsible', 'create_date',
        'state', 'step_state', 'events', 'status', 'delete',
    ]

    AIC = 'aic'
    IP = 'ip'
    IP_LIST_VIEW_CHOICES = (
        (AIC, 'AIC'),
        (IP, 'IP'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')
    ip_list_columns = PickledObjectField(default=DEFAULT_IP_LIST_COLUMNS,)
    ip_list_view_type = models.CharField(max_length=10, choices=IP_LIST_VIEW_CHOICES, default=AIC,)


class Notification(models.Model):
    LEVEL_CHOICES = (
        (logging.DEBUG, 'debug'),
        (logging.INFO, 'info'),
        (logging.WARNING, 'warning'),
        (logging.ERROR, 'error'),
        (logging.CRITICAL, 'critical'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    level = models.IntegerField(choices=LEVEL_CHOICES)
    message = models.CharField(max_length=255)
    time_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-time_created']
        get_latest_by = "time_created"
