import Controller from '../controllers/FormErrorsCtrl';

export default {
  templateUrl: 'static/frontend/views/form_errors.html',
  controller: Controller,
  controllerAs: 'vm',
  bindings: {
    errors: '=',
  },
};
