export default class {
  constructor() {
    const vm = this;
    vm.$onInit = function() {
      vm.currentYear = new Date().getFullYear();
    };
  }
}
