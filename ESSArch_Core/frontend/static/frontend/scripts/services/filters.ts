import * as angular from 'angular';
import {IFieldGroup, IFieldObject} from '../formly/types';

interface rootscope extends ng.IRootScopeService {
  auth: any;
}

export default (
  $translate: ng.translate.ITranslateService,
  $rootScope: rootscope,
  $http: ng.IHttpService,
  appConfig: any
) => {
  let policies: any = [];
  let users: any = [];
  let eventTypes: any = [];

  let getStoragePolicies = async (search: string) => {
    const response = await $http.get(appConfig.djangoUrl + 'storage-policies/', {
      params: {page: 1, page_size: 10, search},
    });
    policies = response.data;
    return response.data;
  };

  let getUsers = async (search: string) => {
    const response = await $http.get(appConfig.djangoUrl + 'users/', {params: {page: 1, page_size: 10, search}});
    users = response.data;
    return response.data;
  };

  let getEventTypes = async (search: string) => {
    const response = await $http.get(appConfig.djangoUrl + 'event-types/', {params: {page: 1, page_size: 10, search}});
    eventTypes = response.data;
    return response.data;
  };

  // Base filter fields for information package views
  let ipBaseFields: (IFieldObject | IFieldGroup)[] = [
    {
      key: 'responsible',
      type: 'checkbox',
      templateOptions: {
        label: $translate.instant('SEE_MY_IPS'),
        trueValue: $rootScope.auth.username,
        falseValue: null,
      },
    },
    {
      key: 'label',
      type: 'input',
      templateOptions: {
        label: $translate.instant('LABEL'),
      },
    },
    {
      className: 'row m-0',
      fieldGroup: [
        {
          key: 'create_date_after',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('IP_CREATE_DATE_START'),
          },
        },
        {
          key: 'create_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('IP_CREATE_DATE_END'),
          },
        },
      ],
    },
    {
      className: 'row m-0',
      fieldGroup: [
        {
          key: 'entry_date_after',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('ENTRY_DATE_START'),
          },
        },
        {
          key: 'entry_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('ENTRY_DATE_END'),
          },
        },
      ],
    },
    {
      className: 'row m-0',
      fieldGroup: [
        {
          key: 'start_date_after',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('START_DATE_START'),
          },
        },
        {
          key: 'start_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('START_DATE_END'),
          },
        },
      ],
    },
    {
      className: 'row m-0',
      fieldGroup: [
        {
          key: 'end_date_after',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('END_DATE_START'),
          },
        },
        {
          key: 'end_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('END_DATE_END'),
          },
        },
      ],
    },
    {
      key: 'responsible',
      type: 'uiselect',
      templateOptions: {
        label: $translate.instant('RESPONSIBLE'),
        labelProp: 'username',
        valueProp: 'username',
        optionsFunction: function() {
          return users;
        },
        clearEnabled: true,
        appendToBody: true,
        refresh: function(search) {
          return getUsers(search);
        },
      },
    },
  ];

  // Additional IP fields available in specific views
  const active: IFieldObject = {
    key: 'active',
    type: 'checkbox',
    templateOptions: {
      label: $translate.instant('INCLUDE_INACTIVE_IPS'),
      trueValue: null,
      falseValue: true,
    },
  };

  const archived: IFieldObject = {
    key: 'archived',
    type: 'checkbox',
    templateOptions: {
      label: $translate.instant('ARCHIVED'),
    },
  };

  const cached: IFieldObject = {
    key: 'cached',
    type: 'checkbox',
    templateOptions: {
      label: $translate.instant('CACHED'),
    },
  };

  const policy: IFieldObject = {
    key: 'policy',
    type: 'uiselect',
    templateOptions: {
      label: $translate.instant('STORAGE_POLICY'),
      labelProp: 'policy_name',
      valueProp: 'id',
      clearEnabled: true,
      optionsFunction: function() {
        return policies;
      },
      appendToBody: true,
      refresh: function(search) {
        getStoragePolicies(search);
      },
    },
  };

  const currentMedium: IFieldObject = {
    key: 'current_medium',
    type: 'input',
    templateOptions: {
      label: $translate.instant('MEDIUM'),
    },
  };

  // Returns base form field list with given special fields first
  const addSpecialFieldsBeforeBase = (list: (IFieldObject | IFieldGroup)[]): (IFieldObject | IFieldGroup)[] => {
    let extras = angular.copy(list);
    return extras.concat(ipBaseFields);
  };

  // Map states and additional IP filter fields
  const ipStateFieldMap = {
    default: ipBaseFields,
    'home.producer.prepareIp': ipBaseFields,
    'home.producer.collectContent': ipBaseFields,
    'home.producer.createSip': ipBaseFields,
    'home.producer.submitSip': ipBaseFields,
    'home.ingest.reception': ipBaseFields,
    'home.ingest.ipApproval': ipBaseFields,
    'home.access.accessIp': addSpecialFieldsBeforeBase([active, cached, archived]),
    'home.access.orders': ipBaseFields,
    'home.access.createDip': ipBaseFields,
    'home.administration.storageMigration': addSpecialFieldsBeforeBase([active, currentMedium, policy]),
    'home.administration.storageMaintenance': addSpecialFieldsBeforeBase([active, currentMedium, policy]),
  };

  // Map states and additional IP filter fields
  const ipStateModelMap = {
    default: {},
    'home.producer.prepareIp': {},
    'home.producer.collectContent': {},
    'home.producer.createSip': {},
    'home.producer.submitSip': {},
    'home.ingest.reception': {},
    'home.ingest.ipApproval': {},
    'home.access.accessIp': {archived: true, active: true},
    'home.access.orders': {},
    'home.access.createDip': {},
    'home.administration.storageMigration': {archived: true, active: true},
    'home.administration.storageMaintenance': {archived: true, active: true},
  };

  // Get ip form fields given state name
  const getIpFilterFields = (state: string): (IFieldObject | IFieldGroup)[] => {
    return ipStateFieldMap[state] || ipStateFieldMap.default;
  };

  // Get ip form model widh default values given state name
  const getIpFilterModel = (state: string) => {
    return ipStateModelMap[state] || ipStateModelMap.default;
  };

  // Events

  // Base filter fields for event views
  let eventBaseFields: (IFieldObject | IFieldGroup)[] = [
    {
      key: 'eventType',
      type: 'uiselect',
      templateOptions: {
        label: $translate.instant('EVENT.EVENTTYPE'),
        labelProp: 'eventDetail',
        valueProp: 'eventType',
        options: eventTypes,
        optionsFunction: function() {
          return eventTypes;
        },
        clearEnabled: true,
        appendToBody: true,
        refresh: function(search) {
          getEventTypes(search);
        },
      },
    },
    {
      key: 'eventOutcome',
      type: 'select',
      templateOptions: {
        label: $translate.instant('EVENTOUTCOME'),
        options: [
          {name: $translate.instant('EVENT.EVENT_SUCCESS'), id: 0},
          {name: $translate.instant('EVENT.EVENT_FAILURE'), id: 1},
        ],
        labelProp: 'name',
        valueProp: 'id',
      },
    },
    {
      className: 'row m-0',
      fieldGroup: [
        {
          key: 'eventDateTime_after',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('EVENTDATETIME_START'),
          },
        },
        {
          key: 'eventDateTime_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('EVENTDATETIME_END'),
          },
        },
      ],
    },
  ];

  // Map states and additional IP filter fields
  let eventStateFieldMap: any = {
    default: eventBaseFields,
  };

  // Map states and additional IP filter fields
  let eventStateModelMap: any = {
    default: {},
  };

  // Get event form fields given state name
  let getEventFilterFields = (state: string): (IFieldObject | IFieldGroup)[] => {
    return eventStateFieldMap[state] || eventStateFieldMap.default;
  };

  // Get event form model widh default values given state name
  let getEventFilterModel = (state: string): any => {
    return eventStateModelMap[state] || eventStateModelMap.default;
  };

  // Public service methods and properties
  let service: any = {
    getIpFilters(state: string): any {
      return {fields: getIpFilterFields(state), model: getIpFilterModel(state)};
    },
    getEventFilters(state: string): any {
      return {fields: getEventFilterFields(state), model: getEventFilterModel(state)};
    },
  };
  return service;
};
