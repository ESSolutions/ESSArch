export default class {
  constructor() {
    var vm = this;
    vm.$onInit = function() {
      vm.currentYear = new Date().getFullYear();
    };
  }
}
