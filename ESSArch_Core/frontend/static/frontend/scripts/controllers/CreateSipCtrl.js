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
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

export default class CreateSipCtrl {
  constructor($http, Profile, $log, $scope, $rootScope, $uibModal, $anchorScroll, $controller) {
    const vm = this;
    const ipSortString = ['Uploaded', 'Creating'];

    $controller('BaseCtrl', {$scope: $scope, vm: vm, ipSortString: ipSortString, params: {}});
    $scope.ipSelected = false;

    //funcitons for select view
    vm.profileModel = {};
    vm.profileFields = [];
    //Click function for profile pbject
    $scope.profileClick = function(row) {
      if ($scope.selectProfile == row && $scope.edit) {
        $scope.edit = false;
      } else {
        if (row.active) {
          Profile.get({
            id: row.active.profile,
            ip: $scope.ip.id,
          }).$promise.then(function(resource) {
            $scope.profileToSave = row.active;
            $scope.selectProfile = row;
            vm.profileModel = resource.specification_data;
            vm.profileFields = resource.template;
            vm.profileFields.forEach(function(field) {
              if (field.fieldGroup != null) {
                field.fieldGroup.forEach(function(subGroup) {
                  subGroup.fieldGroup.forEach(function(item) {
                    item.type = 'input';
                    item.templateOptions.disabled = true;
                  });
                });
              } else {
                field.type = 'input';
                field.templateOptions.disabled = true;
              }
            });
            $scope.edit = true;
            $scope.eventlog = true;
            vm.getEventlogData();
          });
        }
      }
    };

    vm.createSipModal = function(ip) {
      const ips = $scope.ips.length > 0 ? $scope.ips : null;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/create_sip_modal.html',
        scope: $scope,
        controller: 'DataModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {
            ip: ip,
            ips: ips,
            vm: vm,
          },
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.ips = [];
          $scope.ip = null;
          $rootScope.ip = null;
          $scope.getListViewData();
          vm.updateListViewConditional();
          $anchorScroll();
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
  }
}
