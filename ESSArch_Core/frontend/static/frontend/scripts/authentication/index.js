import angular from 'angular';

import loginCtrl from './controllers/LoginCtrl';
import djangoAuth from './services/djangoAuth';

export default angular
  .module('essarch.authentication', [])
  .controller('LoginCtrl', loginCtrl)
  .service('djangoAuth', djangoAuth).name;
