import myService from '../services/myService';
import appraisal from '../services/appraisal';
import storagePolicy from '../services/storagePolicy';
import contextMenuBase from '../services/ContextMenuBase';
import conversion from '../services/conversion';
import validate from '../services/validate';
import messenger from '../services/messenger';
import event from '../services/event';
import contentTabs from '../services/ContentTabs';
import eventType from '../services/eventType';
import ioQueue from '../services/ioQueue';
import ip from '../services/ip';
import ipReception from '../services/ipReception';
import listViewService from '../services/listViewService';
import order from '../services/order';
import {profile, profileIp, profileIpData} from '../services/profile';
import requests from '../services/requests';
import resource from '../services/resource';
import robot from '../services/robot';
import robotQueue from '../services/robotQueue';
import sa from '../services/sa';
import search from '../services/search';
import selectedIPUpdater from '../services/SelectedIPUpdater';
import stateTree from '../services/StateTree';
import step from '../services/step';
import storage from '../services/storage';
import storageMedium from '../services/storageMedium';
import storageObject from '../services/storageObject';
import sysinfo from '../services/sysinfo';
import tag from '../services/tag';
import tapeDrive from '../services/tapeDrive';
import tapeSlot from '../services/tapeSlot';
import task from '../services/task';
import {me, user} from '../services/user';
import {workarea, workareaFiles} from '../services/workarea';

export default angular
  .module('essarch.services', [])
  .factory('myService', ['PermPermissionStore', 'djangoAuth', myService])
  .factory('Appraisal', ['$http', 'appConfig', appraisal])
  .factory('StoragePolicy', ['$resource', 'appConfig', storagePolicy])
  .factory('ContentTabs', contentTabs)
  .factory('ContextMenuBase', ['$translate', contextMenuBase])
  .factory('Conversion', ['$http', 'appConfig', conversion])
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
  .factory('Requests', ['Notifications', 'IP', requests])
  .factory('Resource', ['listViewService', 'Storage', '$rootScope', resource])
  .factory('Robot', ['$resource', 'appConfig', robot])
  .factory('RobotQueue', ['$resource', 'appConfig', robotQueue])
  .factory('SA', ['$resource', 'appConfig', sa])
  .factory('Search', ['$http', '$sce', 'appConfig', search])
  .factory('SelectedIPUpdater', selectedIPUpdater)
  .factory('StateTree', ['IP', 'Step', '$filter', 'linkHeaderParser', stateTree])
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
  .factory('Sysinfo', ['$resource', 'appConfig', sysinfo])
  .factory('Tag', ['IP', '$resource', 'appConfig', tag])
  .factory('TapeDrive', ['$resource', 'appConfig', tapeDrive])
  .factory('TapeSlot', ['$resource', 'appConfig', tapeSlot])
  .factory('Task', ['$resource', 'appConfig', task])
  .factory('User', ['$resource', 'appConfig', user])
  .factory('Workarea', ['$resource', 'appConfig', workarea])
  .factory('WorkareaFiles', ['$resource', 'appConfig', workareaFiles])
  .service('Validate', validate).name;
