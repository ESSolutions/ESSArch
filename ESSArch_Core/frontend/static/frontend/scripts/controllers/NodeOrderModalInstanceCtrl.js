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
export default class NodeOrderModalInstanceCtrl {
  constructor(data, $uibModalInstance, $translate, $http, appConfig) {
    const $ctrl = this;
    $ctrl.data = data;
    $ctrl.adding = false;
    $ctrl.model = {};
    $ctrl.fields = [];
    $ctrl.options = {order: []};
    $ctrl.data = data;
    $ctrl.$onInit = function() {
      $ctrl.buildForm();
    };

    $ctrl.getOrders = search => {
      return $http.get(appConfig.djangoUrl + 'orders/', {params: {page: 1, page_size: 10, search}}).then(response => {
        $ctrl.options.order = response.data;
        return response.data;
      });
    };

    $ctrl.buildForm = () => {
      $ctrl.fields = [
        {
          type: 'uiselect',
          key: 'order',
          templateOptions: {
            options: function() {
              return $ctrl.options.order;
            },
            valueProp: 'id',
            labelProp: 'label',
            label: $translate.instant('ORDER'),
            appendToBody: false,
            optionsFunction: function(search) {
              return $ctrl.options.order;
            },
            refresh: function(search) {
              return $ctrl.getOrders(search).then(function() {
                this.options = $ctrl.options.order;
                return $ctrl.options.order;
              });
            },
            defaultValue: $ctrl.options.order.length > 0 ? $ctrl.options.order[0].id : null,
            required: true,
          },
        },
      ];
    };

    $ctrl.add = function() {
      if ($ctrl.form.$invalid) {
        $ctrl.form.$setSubmitted();
        return;
      }
      $http({
        method: 'POST',
        url: appConfig.djangoUrl + 'orders/' + $ctrl.model.order + '/',
        data: {
          tags: data.nodes.map(x => {
            return x._id;
          }),
        },
      }).then(response => {
        $uibModalInstance.close(response.data);
      });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  }
}
