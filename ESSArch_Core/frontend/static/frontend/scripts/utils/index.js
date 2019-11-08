import angular from 'angular';

import infiniteScroll from './directives/infiniteScroll';

export default angular.module('essarch.utils', []).directive('onScroll', infiniteScroll).name;
