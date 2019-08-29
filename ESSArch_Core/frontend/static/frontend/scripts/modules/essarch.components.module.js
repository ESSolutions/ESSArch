import archiveManager from '../components/ArchiveManagerComponent';
import classificationStructureEditor from '../components/ClassificationStructureEditorComponent';
import agents from '../components/AgentsComponent';
import dashboardStats from '../components/DashboardStatsComponent';
import deliveryComponent from '../components/DeliveryComponent';
import essarchFooter from '../components/FooterComponent';
import eventTable from '../components/EventTableComponent';
import exportComponent from '../components/ExportComponent';
import filebrowserComponent from '../components/FilebrowserComponent';
import formErrorComponent from '../components/FormErrorComponent';
import importComponent from '../components/ImportComponent';
import location from '../components/LocationComponent';
import locationTree from '../components/LocationTreeComponent';
import mapStructureEditor from '../components/MapStructureEditorComponent';
import sysInfoComponent from '../components/SysInfoComponent';
import UserDropdownComponent from '../components/UserDropdownComponent';
import ProfileEditorComponent from '../components/ProfileEditorComponent';
import profileMaker from '../components/ProfileMakerComponent';
import profileManager from '../components/ProfileManagerComponent';
import resultField from '../components/SearchResultFieldComponent';
import SaEditorComponent from '../components/SaEditorComponent';
import searchFilter from '../components/SearchFilterComponent';
import search from '../components/SearchComponent';
import StateTreeView from '../components/StateTreeViewComponent';

export default angular
  .module('essarch.components', ['essarch.controllers'])
  .component('agents', agents)
  .component('archiveManager', archiveManager)
  .component('classificationStructureEditor', classificationStructureEditor)
  .component('dashboardStats', dashboardStats)
  .component('deliveryPage', deliveryComponent)
  .component('essarchFooter', essarchFooter)
  .component('eventTable', eventTable)
  .component('export', exportComponent)
  .component('filebrowser', filebrowserComponent)
  .component('formErrors', formErrorComponent)
  .component('import', importComponent)
  .component('location', location)
  .component('locationTree', locationTree)
  .component('mapStructureEditor', mapStructureEditor)
  .component('profileEditor', ProfileEditorComponent)
  .component('profileMaker', profileMaker)
  .component('profileManager', profileManager)
  .component('saEditor', SaEditorComponent)
  .component('resultField', resultField)
  .component('stateTreeView', StateTreeView)
  .component('sysInfoComponent', sysInfoComponent)
  .component('search', search)
  .component('searchFilter', searchFilter)
  .component('userDropdown', UserDropdownComponent).name;
