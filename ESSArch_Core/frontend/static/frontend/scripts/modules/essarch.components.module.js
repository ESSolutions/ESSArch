import archiveManager from '../components/ArchiveManagerComponent';
import classificationStructureEditor from '../components/ClassificationStructureEditorComponent';
import dashboardStats from '../components/DashboardStatsComponent';
import essarchFooter from '../components/FooterComponent';
import eventTable from '../components/EventTableComponent';
import exportComponent from '../components/ExportComponent';
import filebrowserComponent from '../components/FilebrowserComponent';
import importComponent from '../components/ImportComponent';
import sysInfoComponent from '../components/SysInfoComponent';
import UserDropdownComponent from '../components/UserDropdownComponent';
import ProfileEditorComponent from '../components/ProfileEditorComponent';
import SaEditorComponent from '../components/SaEditorComponent';
import StateTreeView from '../components/StateTreeViewComponent';

export default angular
  .module('essarch.components', ['essarch.controllers'])
  .component('archiveManager', archiveManager)
  .component('classificationStructureEditor', classificationStructureEditor)
  .component('dashboardStats', dashboardStats)
  .component('essarchFooter', essarchFooter)
  .component('eventTable', eventTable)
  .component('export', exportComponent)
  .component('filebrowser', filebrowserComponent)
  .component('import', importComponent)
  .component('profileEditor', ProfileEditorComponent)
  .component('saEditor', SaEditorComponent)
  .component('stateTreeView', StateTreeView)
  .component('sysInfoComponent', sysInfoComponent)
  .component('userDropdown', UserDropdownComponent).name;
