import myService from '../services/myService';
import archivePolicy from '../services/archivePolicy';
import contextMenuBase from '../services/ContextMenuBase';
import validate from '../services/validate';
import messenger from '../services/messenger';
import event from '../services/event';
import contentTabs from '../services/contentTabs';
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
import step from '../services/step';
import storage from '../services/storage';
import storageMedium from '../services/storageMedium';
import storageObject from '../services/storageObject';
import tag from '../services/tag';
import tapeDrive from '../services/tapeDrive';
import tapeSlot from '../services/tapeSlot';
import task from '../services/task';
import {workarea, workareaFiles} from '../services/workarea';

export default angular
  .module('essarch.services', [])
  .factory('myService', myService)
  .factory('ArchivePolicy', archivePolicy)
  .factory('ContentTabs', contentTabs)
  .factory('ContextMenuBase', contextMenuBase)
  .factory('Event', event)
  .factory('EventType', eventType)
  .factory('IOQueue', ioQueue)
  .factory('IP', ip)
  .factory('IPReception', ipReception)
  .factory('listViewService', listViewService)
  .factory('Messenger', messenger)
  .factory('Order', order)
  .factory('Profile', profile)
  .factory('ProfileIp', profileIp)
  .factory('ProfileIpData', profileIpData)
  .factory('Requests', requests)
  .factory('Resource', resource)
  .factory('Robot', robot)
  .factory('RobotQueue', robotQueue)
  .factory('SA', sa)
  .factory('Search', search)
  .factory('SelectedIPUpdater', selectedIPUpdater)
  .factory('Step', step)
  .factory('Storage', storage)
  .factory('StorageMedium', storageMedium)
  .factory('StorageObject', storageObject)
  .factory('Tag', tag)
  .factory('TapeDrive', tapeDrive)
  .factory('TapeSlot', tapeSlot)
  .factory('Task', task)
  .factory('Workarea', workarea)
  .factory('WorkareaFiles', workareaFiles)
  .service('Validate', validate).name;
