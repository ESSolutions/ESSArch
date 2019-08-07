import HttpInterceptor from '../configs/httpInterceptor';
import UiSelectConfig from '../configs/uiSelectConfig';
import PropsFilter from '../filters/propsfilter';

export default angular
  .module('essarch.configs', ['pascalprecht.translate'])
  .config(HttpInterceptor)
  .config(UiSelectConfig)
  .filter('propsFilter', PropsFilter).name;
