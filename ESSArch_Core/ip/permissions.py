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

from rest_framework import permissions


class IsOrderResponsibleOrAdmin(permissions.IsAuthenticated):
    message = "You are not responsible for this order"

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or obj.responsible == request.user

class IsResponsibleOrReadOnly(permissions.IsAuthenticated):
    message = "You are not responsible for this IP"

    def is_responsible(self, request, obj):
        return obj.Responsible == request.user

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return self.is_responsible(request, obj)


class CanDeleteIP(IsResponsibleOrReadOnly):
    message = "You are not allowed to delete this IP"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.delete_informationpackage')

        return responsible or has_perm


class CanUpload(IsResponsibleOrReadOnly):
    message = "You are not allowed to set this IP as uploaded"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.can_upload')

        return responsible or has_perm


class CanSetUploaded(IsResponsibleOrReadOnly):
    message = "You are not allowed to set this IP as uploaded"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.set_uploaded')

        return responsible or has_perm


class CanCreateSIP(IsResponsibleOrReadOnly):
    message = "You are not allowed to create this SIP"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.create_sip')

        return responsible or has_perm


class CanSubmitSIP(IsResponsibleOrReadOnly):
    message = "You are not allowed to submit this SIP"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.submit_sip')

        return responsible or has_perm


class CanTransferSIP(permissions.IsAuthenticated):
    message = "You are not allowed to transfer this SIP"

    def has_object_permission(self, request, view, obj):
        has_perm = request.user.has_perm('ip.transfer_sip')

        return has_perm


class CanChangeSA(IsResponsibleOrReadOnly):
    message = "You are not allowed to choose SA connected to this IP"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.change_sa')

        return responsible or has_perm


class CanLockSA(IsResponsibleOrReadOnly):
    message = "You are not allowed to lock a SA to this IP"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.lock_sa')

        return responsible or has_perm


class CanUnlockProfile(IsResponsibleOrReadOnly):
    message = "You are not allowed to unlock a profile connected to this IP"

    def has_object_permission(self, request, view, obj):
        responsible = self.is_responsible(request, obj)
        has_perm = request.user.has_perm('ip.unlock_profile')

        return responsible or has_perm
