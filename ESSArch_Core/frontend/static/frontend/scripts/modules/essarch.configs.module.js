import FormlyConfig from '../configs/formlyConfig';
import HttpInterceptor from '../configs/httpInterceptor';
import UiSelectConfig from '../configs/uiSelectConfig';
import PropsFilter from '../filters/propsFilter';

export default angular
  .module('essarch.configs', ['pascalprecht.translate'])
  .config(FormlyConfig)
  .config(HttpInterceptor)
  .config(UiSelectConfig)
  .filter('propsFilter', PropsFilter).name;
