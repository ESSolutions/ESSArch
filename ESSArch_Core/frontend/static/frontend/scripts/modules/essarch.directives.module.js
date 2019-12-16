import focused from '../directives/focused';
import ngEnter from '../directives/ngEnter';
import treednd from '../directives/dragNdropDirective';
import fileread from '../directives/fileread';
import sortableTab from '../directives/sortableTab';

export default angular
  .module('essarch.directives', ['essarch.services'])
  .directive('fileread', [fileread])
  .directive('ngEnter', [ngEnter])
  .directive('treednd', ['myService', treednd])
  .directive('sortableTab', ['$timeout', '$document', sortableTab])
  .directive('focused', ['$timeout', '$parse', focused]).name;
