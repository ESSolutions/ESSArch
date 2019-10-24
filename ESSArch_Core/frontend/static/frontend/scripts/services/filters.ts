import * as angular from 'angular';

interface rootscope extends ng.IRootScopeService {
  auth: any;
}

interface templateOptions {
  label: string;
  options?: any[] | Function;
  optionsFunction?: Function;
  valueProp?: string;
  labelProp?: string;
  trueValue?: any;
  falseValue?: any;
  appendToBody?: boolean;
  refresh?: Function;
  clearEnabled?: boolean;
}

interface formlyField {
  key: string;
  type: string;
  templateOptions: templateOptions;
  defaultValue?: any;
}

interface formGroup {
  fieldGroup: formlyField[];
  className?: string;
}

export default (
  $translate: ng.translate.ITranslateService,
  $rootScope: rootscope,
  $http: ng.IHttpService,
  appConfig: any
) => {
  let policies: any = [];
  let users: any = [];

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

  // Base filter fields for information package views
  let ipBaseFields: (formlyField | formGroup)[] = [
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
          key: 'create_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('IP_CREATE_DATE_START'),
          },
        },
        {
          key: 'create_date_after',
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
          key: 'entry_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('ENTRY_DATE_START'),
          },
        },
        {
          key: 'entry_date_after',
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
          key: 'start_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('START_DATE_START'),
          },
        },
        {
          key: 'start_date_after',
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
          key: 'end_date_before',
          type: 'datepicker',
          templateOptions: {
            label: $translate.instant('END_DATE_START'),
          },
        },
        {
          key: 'end_date_after',
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
        options: function() {
          return users;
        },
        optionsFunction: function() {
          return users;
        },
        clearEnabled: true,
        appendToBody: true,
        refresh: function(search) {
          getUsers(search);
        },
      },
    },
  ];

  // Additional IP fields available in specific views
  let active: formlyField = {
    key: 'active',
    type: 'checkbox',
    templateOptions: {
      label: $translate.instant('INCLUDE_INACTIVE_IPS'),
      trueValue: null,
      falseValue: true,
    },
  };

  let archived: formlyField = {
    key: 'archived',
    type: 'checkbox',
    templateOptions: {
      label: $translate.instant('ARCHIVED'),
    },
  };

  let cached: formlyField = {
    key: 'cached',
    type: 'checkbox',
    templateOptions: {
      label: $translate.instant('CACHED'),
    },
  };

  let policy: formlyField = {
    key: 'policy',
    type: 'uiselect',
    templateOptions: {
      label: $translate.instant('STORAGE_POLICY'),
      labelProp: 'policy_name',
      valueProp: 'id',
      options: function() {
        return policies;
      },
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

  let currentMedium: formlyField = {
    key: 'current_medium',
    type: 'input',
    templateOptions: {
      label: $translate.instant('MEDIUM'),
    },
  };

  // Returns base form field list with given special fields first
  let addSpecialFieldsBeforeBase = (list: (formlyField | formGroup)[]): (formlyField | formGroup)[] => {
    let extras = angular.copy(list);
    return extras.concat(ipBaseFields);
  };

  // Map states and additional IP filter fields
  let ipStateFieldMap: any = {
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
  let ipStateModelMap: any = {
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

  // Get form fields given state name
  let getIpFilterFields = (state: string): (formlyField | formGroup)[] => {
    return ipStateFieldMap[state] || ipStateFieldMap.default;
  };

  // Get form model widh default values given state name
  let getIpFilterModel = (state: string): any => {
    return ipStateModelMap[state] || ipStateModelMap['default'];
  };

  // Public service methods and properties
  let service: any = {
    getIpFilters(state: string): any {
      return {fields: getIpFilterFields(state), model: getIpFilterModel(state)};
    },
  };
  return service;
};
