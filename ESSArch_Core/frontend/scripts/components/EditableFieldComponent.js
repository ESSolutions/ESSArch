angular.module('essarch.components').component('editableField', {
  templateUrl: 'editable_field.html',
  controller: 'EditableFieldCtrl',
  controllerAs: 'vm',
  bindings: {
    value: '=', // Value, on regular text field this is the only required data
    value2: '=', // In case 2 values has to be entered for field
    text: '<', // If the non editable view should show something other than value property
    type: '<', // type of field, defaults to input.
    type2: '<', // type of field2, defaults to input.
    edit: '<', // Decides if edit view is displayed
    textClass: '@', // Class for text
    inputClass: '@', // For custom input class, default is form-control
    options: '<', // Options for select field, only used when type = 'select'
    options2: '<', // Options for select field2, only used when type2 = 'select'
    placeholder: '<', // Placeholder for value
    placeholder2: '<', // placeholder for value2
    tooltip: '@', // Tooltip for value
    tooltip2: '@', // Tooltip for value2
  },
});
