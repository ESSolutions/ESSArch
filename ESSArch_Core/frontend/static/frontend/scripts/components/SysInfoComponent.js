import controller from '../controllers/SysInfoComponentCtrl';
import template from '../../views/sys_info_component.html';

export default {
  template,
  controller: ['$scope', controller],
  controllerAs: 'vm',
  bindings: {
    icon: '@',
    name: '@',
    version: '@',
  },
};
