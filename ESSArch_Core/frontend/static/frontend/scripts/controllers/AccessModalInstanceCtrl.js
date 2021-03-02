export default class AccessModalInstanceCtrl {
  constructor($uibModalInstance, data, Requests, $q) {
    const $ctrl = this;
    $ctrl.angular = angular;
    $ctrl.data = data;
    $ctrl.requestTypes = data.types;
    $ctrl.request = data.request;
    $ctrl.accessing = false;

    $ctrl.$onInit = function () {
      if ($ctrl.data.ips == null) {
        $ctrl.data.ips = [$ctrl.data.ip];
      }
    };
    $ctrl.ok = function () {
      $uibModalInstance.close();
    };
    $ctrl.cancel = function () {
      $uibModalInstance.dismiss('cancel');
    };
    $ctrl.accessTitle = function (type) {
      switch (type) {
        case 'get':
          return 'GET';
        case 'get_tar':
          return 'GET_AS_CONTAINER';
        case 'get_as_new':
          return 'GET_AS_NEW_GENERATION';
        case 'edit':
          return 'GET_AS_EDITABLE';
        default:
          return 'GET';
      }
    };
    // Preserve IP
    $ctrl.access = function () {
      $ctrl.accessing = true;
      const data = {
        purpose: $ctrl.data.request.purpose,
        tar: $ctrl.data.request.type === 'get_tar',
        extracted: $ctrl.data.request.type === 'get',
        new: $ctrl.data.request.type === 'get_as_new',
<<<<<<< HEAD
        edit: $ctrl.data.request.type === 'edit',
=======
        edit:$ctrl.data.request.type === 'edit',
>>>>>>> bb808207c32912d106cd303bfc47d56f0f3d8ea5
        package_xml: $ctrl.data.request.package_xml,
        aic_xml: $ctrl.data.request.aic_xml,
      };
      const promises = [];
      $ctrl.data.ips.forEach(function (ip) {
        promises.push(
          Requests.access(ip, data).then(function (response) {
            return response;
          })
        );
      });
      $q.all(promises)
        .then(function (data) {
          $uibModalInstance.close(data);
          $ctrl.accessing = false;
        })
        .catch(() => {
          $ctrl.accessing = false;
        });
    };
  }
}
