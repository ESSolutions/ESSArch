/*
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
*/

export default class PrepareIpModalInstanceCtrl {
  constructor($uibModalInstance, data, IP, EditMode, $scope, $translate) {
    const $ctrl = this;

    $ctrl.$onInit = () => {
      EditMode.enable();
    };
    $ctrl.ipData = {
      package_type: 0,
    };

    $ctrl.labelField = [
      {
        type: 'input',
        key: 'label',
        templateOptions: {
          label: $translate.instant('LABEL'),
          required: true,
          focus: true,
        },
      },
    ];

    $ctrl.identifierField = [
      {
        type: 'input',
        key: 'object_identifier_value',
        validators: {
          coordinate: {
            expression: function(viewValue, modelValue) {
              const value = modelValue || viewValue;
              return (
                /^[^/|\\|\||*|>|<|:|"|?]*$/.test(value) || value === '' || angular.isUndefined(value) || value === null
              );
            },
            message: '("IDENTIFICATION_CAN_NOT_CONTAIN_DESC" | translate)',
          },
        },
        templateOptions: {
          type: 'text',
          label: $translate.instant('CUSTOM_IDENTIFICATION'),
        },
      },
    ];

    $ctrl.prepare = () => {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }

      $ctrl.preparing = true;
      return IP.prepare($ctrl.ipData)
        .$promise.then(function(resource) {
          $ctrl.preparing = false;
          EditMode.disable();
          return $uibModalInstance.close($ctrl.data);
        })
        .catch(function(response) {
          $ctrl.preparing = false;
        });
    };

    $ctrl.cancel = function() {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };

    $scope.$on('modal.closing', function(event, reason, closed) {
      if (reason === 'cancel' || reason === 'backdrop click' || reason === 'escape key press') {
        const message = $translate.instant('UNSAVED_DATA_WARNING');
        if (!confirm(message)) {
          event.preventDefault();
        } else {
          EditMode.disable();
        }
      }
    });
  }
}
