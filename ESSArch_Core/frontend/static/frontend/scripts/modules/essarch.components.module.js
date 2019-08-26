import archiveManager from '../components/ArchiveManagerComponent';
import classificationStructureEditor from '../components/ClassificationStructureEditorComponent';
import agents from '../components/AgentsComponent';
import dashboardStats from '../components/DashboardStatsComponent';
import deliveryComponent from '../components/DeliveryComponent';
import essarchFooter from '../components/FooterComponent';
import eventTable from '../components/EventTableComponent';
import exportComponent from '../components/ExportComponent';
import filebrowserComponent from '../components/FilebrowserComponent';
import importComponent from '../components/ImportComponent';
import location from '../components/LocationComponent';
import locationTree from '../components/LocationTreeComponent';
import sysInfoComponent from '../components/SysInfoComponent';
import UserDropdownComponent from '../components/UserDropdownComponent';
import ProfileEditorComponent from '../components/ProfileEditorComponent';
import SaEditorComponent from '../components/SaEditorComponent';
import searchFilter from '../components/SearchFilterComponent';
import StateTreeView from '../components/StateTreeViewComponent';

export default angular
  .module('essarch.components', ['essarch.controllers'])
  .component('agents', agents)
  .component('archiveManager', archiveManager)
  .component('classificationStructureEditor', classificationStructureEditor)
  .component('dashboardStats', dashboardStats)
  .component('deliveryComponent', deliveryComponent)
  .component('essarchFooter', essarchFooter)
  .component('eventTable', eventTable)
  .component('export', exportComponent)
  .component('filebrowser', filebrowserComponent)
  .component('import', importComponent)
  .component('location', location)
  .component('locationTree', locationTree)
  .component('profileEditor', ProfileEditorComponent)
  .component('saEditor', SaEditorComponent)
  .component('stateTreeView', StateTreeView)
  .component('sysInfoComponent', sysInfoComponent)
  .component('searchFilter', searchFilter)
  .component('userDropdown', UserDropdownComponent).name;
