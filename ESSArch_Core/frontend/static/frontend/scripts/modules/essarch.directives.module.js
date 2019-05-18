import focused from '../directives/focused';

export default angular
  .module('essarch.directives', ['essarch.services'])
  .directive('focused', ['$timeout', '$parse', focused]).name;
