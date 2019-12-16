import ValidationCtrl from '../controllers/ValidationCtrl';

export default {
  templateUrl: 'static/frontend/views/validation_view.html',
  controller: ['$scope', '$rootScope', 'appConfig', '$translate', '$http', '$timeout', '$uibModal', ValidationCtrl],
  controllerAs: 'vm',
  bindings: {
    ip: '<',
  },
};
