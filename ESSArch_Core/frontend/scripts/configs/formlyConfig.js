angular.module('essarch').config(function(formlyConfigProvider) {
  function _defineProperty(obj, key, value) {
    if (key in obj) {
      Object.defineProperty(obj, key, {
        value: value,
        enumerable: true,
        configurable: true,
        writable: true,
      });
    } else {
      obj[key] = value;
    }
    return obj;
  }
  formlyConfigProvider.setType({
    name: 'input',
    templateUrl: 'formly_templates/form_template_input.html',
    overwriteOk: true,
    wrapper: ['bootstrapHasError'],
    defaultOptions: function(options) {
      return {
        templateOptions: {
          validation: {
            show: true,
          },
        },
      };
    },
  });

  formlyConfigProvider.setType({
    name: 'select',
    templateUrl: 'formly_templates/form_template_select.html',
    overwriteOk: true,
    wrapper: ['bootstrapHasError'],
    defaultOptions: function defaultOptions(options) {
      var ngOptions =
        options.templateOptions.ngOptions ||
        "option[to.valueProp || 'value'] as option[to.labelProp || 'name'] group by option[to.groupProp || 'group'] for option in to.options";
      return {
        templateOptions: {
          validation: {
            show: true,
          },
        },
        ngModelAttrs: _defineProperty({}, ngOptions, {
          value: options.templateOptions.optionsAttr || 'ng-options',
        }),
      };
    },
  });

  /*
   * Custom field type for datetime-picker
   * Add appendToBody: false to templateOptions to not append
   * datetime-picker to body(In modals etc) and true to append to body.
   * True by default
   */
  formlyConfigProvider.setType({
    name: 'datepicker',
    templateUrl: 'formly_templates/datepicker_template.html',
    overwriteOk: true,
    wrapper: ['bootstrapHasError'],
    defaultOptions: function defaultOptions(options) {
      return {
        templateOptions: {
          validation: {
            show: true,
          },
        },
      };
    },
  });

  /*
   * Custom field type for ui-select
   * Add appendToBody: false to templateOptions to not append
   * options to body(In modals etc) and true to append to body.
   * False by default
   */
  formlyConfigProvider.setType({
    name: 'uiselect',
    templateUrl: 'formly_templates/ui_select_template.html',
    overwriteOk: true,
    wrapper: ['bootstrapHasError'],
    defaultOptions: function defaultOptions(options) {
      return {
        templateOptions: {
          validation: {
            show: true,
          },
        },
      };
    },
  });

  formlyConfigProvider.setType({
    name: 'select-tree-edit',
    template:
      '<select class="form-control" ng-model="model[options.key]"><option value="" disabled hidden>Choose here</option></select>',
    wrapper: ['bootstrapLabel', 'bootstrapHasError'],
    defaultOptions: function defaultOptions(options) {
      /* jshint maxlen:195 */
      var ngOptions =
        options.templateOptions.ngOptions ||
        "option[to.valueProp || 'value'] as option[to.labelProp || 'name'] group by option[to.groupProp || 'group'] for option in to.options";
      return {
        ngModelAttrs: _defineProperty({}, ngOptions, {
          value: options.templateOptions.optionsAttr || 'ng-options',
        }),
      };
    },

    apiCheck: function apiCheck(check) {
      return {
        templateOptions: {
          label: check.string.optional,
          options: check.arrayOf(check.object),
          optionsAttr: check.string.optional,
          labelProp: check.string.optional,
          valueProp: check.string.optional,
          groupProp: check.string.optional,
        },
      };
    },
  });

  formlyConfigProvider.setWrapper({
    name: 'validation',
    types: ['input', 'datepicker', 'select', 'uiselect', 'textarea'],
    templateUrl: 'formly_templates/form_error_messages.html',
  });
});
