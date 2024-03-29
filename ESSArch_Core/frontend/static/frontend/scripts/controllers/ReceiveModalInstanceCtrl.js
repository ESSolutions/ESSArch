export default class ReceiveModalInstanceCtrl {
  constructor($uibModalInstance, $scope, data, $translate, $http, appConfig, $q, EditMode, IPReception) {
    const $ctrl = this;
    $scope.angular = angular;
    $scope.saAlert = null;
    $scope.alerts = {
      receiveError: {type: 'danger', msg: $translate.instant('CANNOT_RECEIVE_ERROR')},
    };

    $ctrl.receiving = false;

    $ctrl.$onInit = () => {
      $ctrl.ips = data.ips.map((ip) => {
        ip.id = ip.object_identifier_value;
        return ip;
      });
      $ctrl.checkInitialSas($ctrl.ips);
      EditMode.enable();
    };

    $ctrl.options = {
      sas: [],
    };

    $ctrl.getIpById = (ips, id) => {
      let ip = null;
      for (let i = 0; i < ips.length; i++) {
        if (ips[i].id === id) {
          ip = ips[i];
          break;
        }
      }
      return ip;
    };

    $ctrl.checkInitialSas = (ips) => {
      let ipSaMap = {};
      ips.forEach((ip) => {
        if (ip.altrecordids && ip.altrecordids.SUBMISSIONAGREEMENT && ip.altrecordids.SUBMISSIONAGREEMENT.length > 0) {
          if (ipSaMap[ip.altrecordids.SUBMISSIONAGREEMENT[0]]) {
            ipSaMap[ip.altrecordids.SUBMISSIONAGREEMENT[0]].push(ip.id);
          } else {
            ipSaMap[ip.altrecordids.SUBMISSIONAGREEMENT[0]] = [ip.id];
          }
          ip.saLoading = true;
        } else if (ip.submission_agreement) {
          if (ipSaMap[ip.submission_agreement]) {
            ipSaMap[ip.submission_agreement].push(ip.id);
          } else {
            ipSaMap[ip.submission_agreement] = [ip.id];
          }
          ip.saLoading = true;
        } else {
          ip.saLoading = false;
        }
      });
      Object.keys(ipSaMap).forEach((key) => {
        $http
          .get(appConfig.djangoUrl + 'submission-agreements/' + key + '/')
          .then((response) => {
            ipSaMap[key].forEach((x) => {
              let ip = $ctrl.getIpById(ips, x);
              ip.sa = response.data;
              ip.saLoading = false;
              ip.hasValidSa = true;
            });
            return response.data;
          })
          .catch((error) => {
            if (error.status === 404) {
              ipSaMap[key].forEach((x) => {
                let ip = $ctrl.getIpById(ips, x);
                //ip.sa = null;
                ip.saLoading = false;
                //ip.hasValidSa = false;
              });
            }
          });
      });
    };

    $ctrl.unidentifiedIpSas = {};

    $ctrl.getSas = function (search) {
      return $http({
        url: appConfig.djangoUrl + 'submission-agreements/',
        mathod: 'GET',
        params: {page: 1, page_size: 10, search: search, published: true},
      }).then(function (response) {
        $ctrl.options.sas = response.data;
        return $ctrl.options.sas;
      });
    };

    $ctrl.saSelect = [
      {
        type: 'uiselect',
        key: 'submission_agreement',
        templateOptions: {
          options: function () {
            return $ctrl.options.sas;
          },
          valueProp: 'id',
          labelProp: 'name',
          multiple: false,
          placeholder: $translate.instant('SUBMISSION_AGREEMENT'),
          appendToBody: true,
          refresh: function (search) {
            if ($ctrl.initSaSearch && (angular.isUndefined(search) || search === null || search === '')) {
              search = angular.copy($ctrl.initSaSearch);
              $ctrl.initSaSearch = null;
            }
            return $ctrl.getSas(search);
          },
        },
        defaultValue: null,
      },
    ];

    $ctrl.hasSelectedSa = (list) => {
      let allHasSa = true;
      list.forEach((x) => {
        if (!x.sa) {
          if (
            !($ctrl.unidentifiedIpSas[x.id] && $ctrl.unidentifiedIpSas[x.id].submission_agreement) ||
            (x.hasValidSa === false && x.sa === null) ||
            x.saLoading
          ) {
            allHasSa = false;
          }
        }
      });
      return allHasSa;
    };

    $ctrl.receive = (ips) => {
      $ctrl.receiving = true;
      const promises = [];
      ips.forEach((ip) => {
        ip.receiving = true;
        let data = {id: ip.id};
        if ($ctrl.unidentifiedIpSas[ip.id]) {
          data.submission_agreement = $ctrl.unidentifiedIpSas[ip.id].submission_agreement;
        }
        promises.push(
          IPReception.receive(data)
            .$promise.then((response) => {
              ip.receiving = false;
              ip.received = true;
              return response;
            })
            .catch((response) => {
              ip.receiving = false;
              ip.received = false;
              if (response.data) {
                ip.error = response.data.detail;
              }
              return $q.reject(response);
            })
        );
        $q.all(promises)
          .then((responses) => {
            $ctrl.receiving = false;
            EditMode.disable();
            $uibModalInstance.close();
          })
          .catch((e) => {
            $ctrl.receiving = false;
          });
      });
    };

    $ctrl.cancel = () => {
      EditMode.disable();
      $uibModalInstance.dismiss('cancel');
    };

    $scope.$on('modal.closing', function (event, reason, closed) {
      if (
        (data.allow_close === null || angular.isUndefined(data.allow_close) || data.allow_close !== true) &&
        (reason === 'cancel' || reason === 'backdrop click' || reason === 'escape key press')
      ) {
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
