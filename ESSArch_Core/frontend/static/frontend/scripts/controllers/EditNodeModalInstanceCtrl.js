angular
  .module('essarch.controllers')
  .controller('EditNodeModalInstanceCtrl', function(
    Search,
    $translate,
    $uibModalInstance,
    djangoAuth,
    appConfig,
    $http,
    data,
    $scope,
    Notifications,
    $timeout,
    $q
  ) {
    var $ctrl = this;
    $ctrl.node = data.node;
    $ctrl.editData = {};
    $ctrl.editFields = [];
    $ctrl.editFieldsNoDelete = [];
    $ctrl.options = {};
    $ctrl.fieldOptions = {};
    $ctrl.newFieldKey = null;
    $ctrl.newFieldVal = null;
    $ctrl.updateDescendants = false;
    $ctrl.manyNodes = false;
    $ctrl.$onInit = function() {
      if (angular.isArray(data.node)) {
        $ctrl.nodeList = data.node
          .map(function(x) {
            return x._id;
          })
          .join(',');
        $ctrl.nameList = data.node
          .map(function(x) {
            return x._source.name;
          })
          .join(', ');
        $ctrl.node = data.node[0];
        $ctrl.node._source = data.node.reduce(function(result, currentObject) {
          for (var key in currentObject._source) {
            if (currentObject._source.hasOwnProperty(key)) {
              result[key] = currentObject._source[key];
            }
          }
          return result;
        }, {});
        $ctrl.manyNodes = true;
      }
      $ctrl.arrayFields = [];
      $ctrl.fieldOptions = getEditableFields($ctrl.node);
      var discludedFields = ['archive', 'current_version'];
      angular.forEach($ctrl.fieldOptions, function(value, field) {
        if (!discludedFields.includes(field)) {
          if (angular.isArray(value)) {
            $ctrl.arrayFields.push(field);
            addStandardField(field, value.join(','));
          } else {
            switch (typeof value) {
              case 'object':
                clearObject($ctrl.node._source[field]);
                addNestedField(field, value);
                break;
              default:
                addStandardField(field, value);
                break;
            }
          }
        }
      });
    };

    $ctrl.noDeleteFields = {
      component: ['name'],
      document: ['name'],
      archive: ['name'],
      information_package: ['name'],
    };

    $ctrl.fieldsToDelete = [];
    function deleteField(field) {
      var splitted = field.split('.');
      if (
        !angular.isUndefined($ctrl.node._source[field]) ||
        (splitted.length > 1 && !angular.isUndefined($ctrl.node._source[splitted[0]][splitted[1]]))
      ) {
        $ctrl.fieldsToDelete.push(field);
      }
      $ctrl.editFields.forEach(function(item, idx, list) {
        if (splitted.length > 1) {
          if (item.templateOptions.label === field) {
            list.splice(idx, 1);
          }
        } else {
          if (item.key === field) {
            list.splice(idx, 1);
          }
        }
      });
      if (splitted.length > 1) {
        delete $ctrl.editData[splitted[0]][splitted[1]];
      } else {
        delete $ctrl.editData[field];
      }
    }

    function addNestedField(field, value) {
      var model = {};
      var group = {
        templateOptions: {
          label: field,
        },
        fieldGroup: [],
      };
      angular.forEach(value, function(val, key) {
        model[key] = val;
        if ($ctrl.noDeleteFields[$ctrl.node._index].includes(field + '.' + key)) {
          $ctrl.editFieldsNoDelete.push({
            templateOptions: {
              type: 'text',
              label: field + '.' + key,
            },
            type: 'input',
            model: 'model.' + field,
            key: key,
          });
        } else {
          $ctrl.editFields.push({
            templateOptions: {
              type: 'text',
              label: field + '.' + key,
              delete: function() {
                deleteField(field + '.' + key);
              },
            },
            type: 'input',
            model: 'model.' + field,
            key: key,
          });
        }
      });
      if (!$ctrl.manyNodes) {
        $ctrl.editData[field] = model;
      } else {
        $ctrl.editData[field] = model;
      }
    }

    function clearObject(obj) {
      angular.forEach(obj, function(val, key) {
        obj[key] = null;
      });
    }

    function addStandardField(field, value) {
      if (!$ctrl.manyNodes) {
        $ctrl.editData[field] = value;
      } else {
        $ctrl.editData[field] = null;
      }
      if ($ctrl.noDeleteFields[$ctrl.node._index].includes(field)) {
        $ctrl.editFieldsNoDelete.push({
          templateOptions: {
            type: 'text',
            label: field,
          },
          type: 'input',
          key: field,
        });
      } else {
        $ctrl.editFields.push({
          templateOptions: {
            type: 'text',
            label: field,
            delete: function() {
              deleteField(field);
            },
          },
          type: 'input',
          key: field,
        });
      }
    }

    function getEditableFields(node) {
      return node._source;
    }
    $ctrl.selected = null;

    $ctrl.changed = function() {
      return !angular.equals(getEditedFields($ctrl.editData), {});
    };

    $ctrl.addNewField = function() {
      if ($ctrl.newFieldKey && $ctrl.newFieldVal) {
        var newFieldKey = angular.copy($ctrl.newFieldKey);
        var newFieldVal = angular.copy($ctrl.newFieldVal);
        var splitted = newFieldKey.split('.');
        if (
          (splitted.length > 1 && !angular.isUndefined($ctrl.editData[splitted[0]][splitted[1]])) ||
          !angular.isUndefined($ctrl.editData[newFieldKey])
        ) {
          Notifications.add($translate.instant('ACCESS.FIELD_EXISTS'), 'error');
          return;
        }
        if (splitted.length > 1) {
          $ctrl.editData[splitted[0]][splitted[1]] = newFieldVal;
        } else {
          $ctrl.editData[newFieldKey] = newFieldVal;
        }
        $ctrl.editFields.push({
          templateOptions: {
            type: 'text',
            label: newFieldKey,
            delete: function() {
              deleteField(newFieldKey);
            },
          },
          type: 'input',
          key: newFieldKey,
        });
        if ($ctrl.fieldsToDelete.includes(newFieldKey)) {
          $ctrl.fieldsToDelete.splice($ctrl.fieldsToDelete.indexOf(newFieldKey), 1);
        }
        $ctrl.newFieldKey = null;
        $ctrl.newFieldVal = null;
      }
    };

    function getEditedFields(data) {
      var edited = {};
      angular.forEach(data, function(value, key) {
        if (typeof value === 'object' && !angular.isArray(value)) {
          angular.forEach(value, function(val, k) {
            if ($ctrl.node._source[key][k] !== val) {
              if (!edited[key]) {
                edited[key] = {};
              }
              edited[key][k] = val;
            }
          });
        } else {
          if ($ctrl.node._source[key] != value) {
            edited[key] = value;
          }
        }
      });
      return edited;
    }

    $ctrl.editField = function(field, value) {
      $ctrl.editData[field] = value;
      $ctrl.editFields.push({
        templateOptions: {
          type: 'text',
          label: field,
        },
        type: 'input',
        key: field,
      });
    };

    $ctrl.updateSingleNode = function() {
      if ($ctrl.changed() || $ctrl.fieldsToDelete.length > 0) {
        $ctrl.submitting = true;
        var promises = [];
        $ctrl.fieldsToDelete.forEach(function(item) {
          promises.push(
            $http
              .post(appConfig.djangoUrl + 'search/' + $ctrl.node._id + '/delete-field/', {field: item})
              .then(function(response) {
                return response;
              })
              .catch(function(response) {
                $ctrl.submitting = false;
                return response;
              })
          );
        });
        $q.all(promises)
          .then(function(results) {
            if ($ctrl.changed()) {
              Search.updateNode($ctrl.node, getEditedFields($ctrl.editData))
                .then(function(response) {
                  $ctrl.submitting = false;
                  Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
                  $uibModalInstance.close('edited');
                })
                .catch(function(response) {
                  $ctrl.submitting = false;
                });
            } else {
              $ctrl.submitting = false;
              Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
              $uibModalInstance.close('edited');
            }
          })
          .catch(function(response) {
            $ctrl.submitting = false;
          });
      }
    };

    $ctrl.updateNodeAndDescendants = function() {
      if ($ctrl.changed() || $ctrl.fieldsToDelete.length > 0) {
        Search.updateNodeAndDescendants($ctrl.node, getEditedFields($ctrl.editData), $ctrl.fieldsToDelete.join(','))
          .then(function(response) {
            $ctrl.submitting = false;
            Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
            $uibModalInstance.close('edited');
          })
          .catch(function(response) {
            $ctrl.submitting = false;
          });
      }
    };

    $ctrl.massUpdate = function() {
      if ($ctrl.changed() || $ctrl.fieldsToDelete.length > 0) {
        Search.massUpdate($ctrl.nodeList, getEditedFields($ctrl.editData), $ctrl.fieldsToDelete.join(','))
          .then(function(response) {
            $ctrl.submitting = false;
            Notifications.add($translate.instant('ACCESS.NODE_EDITED'), 'success');
            $uibModalInstance.close('edited');
          })
          .catch(function(response) {
            $ctrl.submitting = false;
          });
      }
    };

    $ctrl.submit = function() {
      convertArrayFields();
      if ($ctrl.manyNodes) {
        $ctrl.massUpdate();
      } else if ($ctrl.updateDescendants) {
        $ctrl.updateNodeAndDescendants();
      } else {
        $ctrl.updateSingleNode();
      }
    };

    function convertArrayFields() {
      $ctrl.arrayFields.forEach(function(field) {
        if (!$ctrl.fieldsToDelete.includes(field) && $ctrl.editData[field] != $ctrl.node._source[field]) {
          $ctrl.editData[field] = $ctrl.editData[field].split(',');
        }
      });
    }

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
