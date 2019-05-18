import essarchFooter from '../components/FooterComponent';
import sysInfoComponent from '../components/sysInfoComponent';
import UserDropdownComponent from '../components/UserDropdownComponent';
import ProfileEditorComponent from '../components/ProfileEditorComponent';
import StateTreeView from '../components/StateTreeViewComponent';

export default angular
  .module('essarch.components', ['essarch.controllers'])
  .component('essarchFooter', essarchFooter)
  .component('profileEditor', ProfileEditorComponent)
  .component('stateTreeView', StateTreeView)
  .component('sysInfoComponent', sysInfoComponent)
  .component('userDropdown', UserDropdownComponent).name;
