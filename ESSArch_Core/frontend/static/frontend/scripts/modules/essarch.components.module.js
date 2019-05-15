import essarchFooter from '../components/FooterComponent';
import sysInfoComponent from '../components/sysInfoComponent';
import UserDropdownComponent from '../components/UserDropdownComponent';

export default angular
  .module('essarch.components', ['essarch.controllers'])
  .component('essarchFooter', essarchFooter)
  .component('sysInfoComponent', sysInfoComponent)
  .component('userDropdown', UserDropdownComponent).name;
