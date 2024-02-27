export default class MyPageCtrl {
  constructor($scope, $translate) {
    const vm = this;
    vm.lang = $translate.use();
  }
}
