import focused from '../directives/focused';
import ngEnter from '../directives/ngEnter';
import treednd from '../directives/dragNdropDirective';
import fileread from '../directives/fileread';

export default angular
  .module('essarch.directives', ['essarch.services'])
  .directive('fileread', [fileread])
  .directive('ngEnter', [ngEnter])
  .directive('treednd', ['myService', treednd])
  .directive('focused', ['$timeout', '$parse', focused]).name;
