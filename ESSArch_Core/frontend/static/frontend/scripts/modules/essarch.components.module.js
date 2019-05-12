import UserDropdownComponent from '../components/UserDropdownComponent';

export default angular
  .module('essarch.components', ['essarch.controllers'])
  .component('userDropdown', UserDropdownComponent).name;
