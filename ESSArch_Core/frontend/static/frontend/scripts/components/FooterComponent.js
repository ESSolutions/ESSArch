import controller from '../controllers/FooterCtrl';
import template from '../../views/footer.html';

export default {
  template,
  controller,
  controllerAs: 'vm',
  bindings: {
    title: '@',
  },
};
