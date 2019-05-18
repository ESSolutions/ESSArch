/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch Preservation Platform (EPP)
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
*/

export default class ModalInstanceCtrl {
  constructor($uibModalInstance, djangoAuth, data, $http, Notifications, IP, appConfig, listViewService, $translate) {
    var $ctrl = this;
    if (data) {
      $ctrl.data = data;
    }
    if (data && data.ip) {
      $ctrl.ip = data.ip;
    }
    if (data && data.field) {
      $ctrl.field = data.field;
    }
    $ctrl.editMode = false;
    $ctrl.error_messages_old = [];
    $ctrl.error_messages_pw1 = [];
    $ctrl.error_messages_pw2 = [];
    $ctrl.tracebackCopied = false;
    $ctrl.copied = function() {
      $ctrl.tracebackCopied = true;
    };
    $ctrl.idCopied = false;
    $ctrl.idCopyDone = function() {
      $ctrl.idCopied = true;
    };
    $ctrl.objectIdentifierValue = '';
    $ctrl.orders = [];
    $ctrl.label = '';
    $ctrl.dir_name = '';
    $ctrl.email = {
      subject: '',
      body: '',
    };
    $ctrl.updateField = function() {
      $uibModalInstance.close($ctrl.field);
    };
    $ctrl.save = function() {
      $ctrl.data = {
        name: $ctrl.profileName,
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.saveDir = function() {
      $ctrl.data = {
        dir_name: $ctrl.dir_name,
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.saveTag = function() {
      $ctrl.data = {
        name: $ctrl.name,
        desc: $ctrl.desc,
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.prepare = () => {
      $ctrl.data = {
        label: $ctrl.label,
        objectIdentifierValue: $ctrl.objectIdentifierValue,
      };
      $ctrl.preparing = true;
      return IP.prepare({
        label: $ctrl.data.label,
        object_identifier_value: $ctrl.data.objectIdentifierValue,
      })
        .$promise.then(function(resource) {
          $ctrl.preparing = false;
          return $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.preparing = false;
        });
    };
    $ctrl.prepareDip = function(label, objectIdentifierValue, orders) {
      $ctrl.preparing = true;
      listViewService
        .prepareDip(label, objectIdentifierValue, orders)
        .then(function(response) {
          $ctrl.preparing = false;
          $uibModalInstance.close();
        })
        .catch(function(response) {
          $ctrl.preparing = false;
        });
    };

    $ctrl.addTag = function() {
      $ctrl.data = {
        name: $ctrl.name,
        desc: $ctrl.desc,
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.lock = function() {
      $ctrl.data = {
        status: 'locked',
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.lockSa = function() {
      $ctrl.data = {
        status: 'locked',
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.remove = function(ipObject) {
      $ctrl.removing = true;
      if (data.workarea) {
        if (ipObject.package_type == 1) {
          ipObject.information_packages.forEach(function(ip) {
            $ctrl.remove(ip, true);
          });
        } else {
          $http
            .delete(appConfig.djangoUrl + 'workarea-entries/' + ipObject.workarea[0].id + '/')
            .then(function(response) {
              $ctrl.removing = false;
              $uibModalInstance.close();
            })
            .catch(function(response) {
              $ctrl.removing = false;
            });
        }
      } else {
        IP.delete({
          id: ipObject.id,
        })
          .$promise.then(function() {
            $ctrl.removing = false;
            Notifications.add($translate.instant('IP_REMOVED', {label: ipObject.label}), 'success');
            $uibModalInstance.close();
          })
          .catch(function(response) {
            $ctrl.removing = false;
          });
      }
    };
    $ctrl.submit = function() {
      $ctrl.data = {
        email: $ctrl.email,
        status: 'submitting',
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.overwrite = function() {
      $ctrl.data = {
        status: 'overwritten',
      };
      $uibModalInstance.close($ctrl.data);
    };
    $ctrl.changePassword = function() {
      djangoAuth.changePassword($ctrl.pw1, $ctrl.pw2, $ctrl.oldPw).then(
        function(response) {
          $uibModalInstance.close($ctrl.data);
        },
        function(error) {
          $ctrl.error_messages_old = error.old_password || [];
          $ctrl.error_messages_pw1 = error.new_password1 || [];
          $ctrl.error_messages_pw2 = error.new_password2 || [];
        }
      );
    };
    $ctrl.ok = function() {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
