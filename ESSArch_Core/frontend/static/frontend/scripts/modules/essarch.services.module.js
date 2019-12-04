import agentName from '../services/agentName';
import myService from '../services/myService';
import appraisal from '../services/appraisal';
import storagePolicy from '../services/storagePolicy';
import contextMenuBase from '../services/ContextMenuBase';
import conversion from '../services/conversion';
import filters from '../services/filters';
import validate from '../services/validate';
import messenger from '../services/messenger';
import event from '../services/event';
import contentTabs from '../services/ContentTabs';
import eventType from '../services/eventType';
import EditMode from '../services/EditMode';
import ioQueue from '../services/ioQueue';
import ip from '../services/ip';
import ipReception from '../services/ipReception';
import listViewService from '../services/listViewService';
import order from '../services/order';
import {profile, profileIp, profileIpData} from '../services/profile';
import profileMakerTemplate from '../services/profileMaker';
import profileMakerExtension from '../services/profileMakerExtension';
import requests from '../services/requests';
import resource from '../services/resource';
import robot from '../services/robot';
import robotQueue from '../services/robotQueue';
import {sa, saIpData} from '../services/sa';
import search from '../services/search';
import selectedIPUpdater from '../services/SelectedIPUpdater';
import stateTree from '../services/StateTree';
import step from '../services/step';
import storage from '../services/storage';
import storageMedium from '../services/storageMedium';
import storageObject from '../services/storageObject';
import structure from '../services/structure';
import structureName from '../services/structureName';
import structureUnitRelation from '../services/structureUnitRelation';
import sysinfo from '../services/sysinfo';
import tag from '../services/tag';
import tapeDrive from '../services/tapeDrive';
import tapeSlot from '../services/tapeSlot';
import task from '../services/task';
import utils from '../services/Utils';
import {me, user} from '../services/user';
import {workarea, workareaFiles} from '../services/workarea';

export default angular
  .module('essarch.services', [])
  .factory('AgentName', ['$filter', agentName])
  .factory('myService', ['PermPermissionStore', 'djangoAuth', myService])
  .factory('Appraisal', ['$http', 'appConfig', appraisal])
  .factory('Filters', ['$translate', '$rootScope', '$http', 'appConfig', 'Notifications', filters])
  .factory('StoragePolicy', ['$resource', 'appConfig', storagePolicy])
  .factory('ContentTabs', contentTabs)
  .factory('ContextMenuBase', ['$translate', contextMenuBase])
  .factory('Conversion', ['$http', 'appConfig', conversion])
  .factory('EditMode', [EditMode])
  .factory('Event', ['$resource', 'appConfig', event])
  .factory('EventType', ['$resource', 'appConfig', eventType])
  .factory('IOQueue', ['$resource', 'appConfig', ioQueue])
  .factory('IP', ['$resource', 'appConfig', 'Event', 'Step', 'Task', ip])
  .factory('IPReception', ['$resource', 'appConfig', ipReception])
  .factory('listViewService', [
    'Tag',
    'Profile',
    'IP',
    'Workarea',
    'WorkareaFiles',
    'Order',
    'IPReception',
    'Event',
    'EventType',
    'SA',
    '$q',
    '$http',
    '$state',
    'appConfig',
    '$rootScope',
    listViewService,
  ])
  .factory('Me', ['$resource', 'appConfig', me])
  .factory('Messenger', ['$window', messenger])
  .factory('Order', ['$resource', 'appConfig', order])
  .factory('Profile', ['$resource', 'appConfig', profile])
  .factory('ProfileIp', ['$resource', 'appConfig', profileIp])
  .factory('ProfileIpData', ['$resource', 'appConfig', profileIpData])
  .factory('ProfileMakerTemplate', ['$resource', 'appConfig', profileMakerTemplate])
  .factory('ProfileMakerExtension', ['$resource', 'appConfig', profileMakerExtension])
  .factory('Requests', ['Notifications', 'IP', 'Workarea', '$state', requests])
  .factory('Resource', ['listViewService', 'Storage', '$rootScope', resource])
  .factory('Robot', ['$resource', 'appConfig', robot])
  .factory('RobotQueue', ['$resource', 'appConfig', robotQueue])
  .factory('SA', ['$resource', 'appConfig', sa])
  .factory('SaIpData', ['$resource', 'appConfig', saIpData])
  .factory('Search', ['$http', '$sce', 'appConfig', search])
  .factory('SelectedIPUpdater', selectedIPUpdater)
  .factory('StateTree', ['IP', 'Step', '$filter', 'linkHeaderParser', 'Workarea', '$state', stateTree])
  .factory('Step', ['$resource', 'appConfig', 'Task', step])
  .factory('Storage', [
    'StorageMedium',
    'StorageObject',
    'Robot',
    'RobotQueue',
    'IOQueue',
    'TapeSlot',
    'TapeDrive',
    storage,
  ])
  .factory('StorageMedium', ['$resource', 'appConfig', storageMedium])
  .factory('StorageObject', ['$resource', 'appConfig', storageObject])
  .factory('Structure', ['$resource', 'appConfig', structure])
  .factory('StructureName', ['$filter', '$translate', structureName])
  .factory('StructureUnitRelation', [structureUnitRelation])
  .factory('Sysinfo', ['$resource', 'appConfig', sysinfo])
  .factory('Tag', ['IP', '$resource', 'appConfig', tag])
  .factory('TapeDrive', ['$resource', 'appConfig', tapeDrive])
  .factory('TapeSlot', ['$resource', 'appConfig', tapeSlot])
  .factory('Task', ['$resource', 'appConfig', task])
  .factory('Utils', [utils])
  .factory('User', ['$resource', 'appConfig', user])
  .factory('Workarea', ['$resource', 'appConfig', 'Task', 'Step', 'Event', workarea])
  .factory('WorkareaFiles', ['$resource', 'appConfig', workareaFiles])
  .service('Validate', validate).name;
