import * as angular from 'angular';

import FormlyConfig from '../configs/formlyConfig';
import HttpInterceptor from '../configs/httpInterceptor';
import PreventTemplateCache from '../configs/preventTemplateCache';
import UiSelectConfig from '../configs/uiSelectConfig';
import PropsFilter from '../filters/propsFilter';

export default angular
  .module('essarch.configs', ['pascalprecht.translate'])
  .config(FormlyConfig)
  .config(HttpInterceptor)
  .config(PreventTemplateCache)
  .config(UiSelectConfig)
  .filter('propsFilter', PropsFilter).name;
