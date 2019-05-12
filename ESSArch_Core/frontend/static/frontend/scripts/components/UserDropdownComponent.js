import controller from '../controllers/UserDropdownCtrl';
import template from '../../views/user_dropdown.html';

export default {
  template,
  controller,
  controllerAs: 'vm',
  bindings: {
    auth: '=',
  },
};
