// var json = require('./data.json');

(function() {


    'use strict';

    angular
        .module('formlyApp')
        .controller('MainController', MainController);


    function MainController($scope, $http) {

        $http.get('/template/struct/' + templateName).then(function(res) {
            $scope.treeElements = [];
            console.log(res.data)
            $scope.treeElements.push(vm.buildTree('root', res.data));
            vm.existingElements = res.data;
            console.log(res.data)
            $http.get('/template/struct/elements/' + templateName).then(function(res) {
              vm.allElements = res.data;
              $scope.showSelected($scope.treeElements[0]['key'], false);
            });
        });


        var vm = this;
        vm.title = 'title'; // placeholder only
        vm.countAll = {};
        vm.anyAttribute = false;
        vm.anyElement = false;
        vm.possibleChildren = [];
        vm.existingChildren = [];
        vm.existingElements = {};
        vm.choiseCount = 0;
        vm.containsFilesText = false;
        vm.choiseCount = 0

        vm.buildTree = function(uuid, data) {
          var element = data[uuid];
          var result = {}
          result['name'] = element['name'];
          result['key'] = uuid;
          var children = [];

          for (var index in element['children']) {
            var child = element['children'][index];
            children.push(vm.buildTree(child['uuid'], data));
          }
          result['children'] = children;
          return result;
        };

        // tree values
        $scope.treeOptions = {
            nodeChildren: "children",
            dirSelectable: true,
            injectClasses: {
                ul: "a1",
                li: "a2",
                liSelected: "a7",
                iExpanded: "a3",
                iCollapsed: "a4",
                iLeaf: "a5",
                label: "a6",
                labelSelected: "a8"
            }
        };
        $scope.expandedNodes = [];
        $scope.dataForTheTree = [];
        $scope.showSelected = function(sel, selected) {
          var data = vm.existingElements[sel];
          console.log(data);
          vm.selectedNode = data;
          vm.title = data['name'].charAt(0).toUpperCase() + data['name'].slice(1);
          vm.min = data['min'];
          vm.max = data['max'];
          if (vm.max == -1) {
              vm.max = 'infinite';
          }
          vm.containsFilesText = false;
          if (data['containsFiles'] == true) {
            vm.containsFilesText = true;
          }
          vm.uuid = sel;
          vm.fields = data['form'];
          if (data['userForm'].length > 0) {
              vm.fields.push({template: '<hr/><p><b>User defined attributes</b></p>'}); //divider
              console.log(data['userForm']);
              vm.fields = vm.fields.concat(data['userForm']);
          }
          var count = vm.countChildrenWithName(data['parent'], data['name']);
          if (vm.min < count) {
              vm.canDelete = true;
          } else {
              vm.canDelete = false;
          }
          // if (sel == 'root') {
          //   vm.canDelete = false;
          // }
          vm.model = data['formData'];
          vm.selectedElement = data;
          vm.anyAttribute = data['anyAttribute'];
          vm.anyElement = data['anyElement'];
          vm.possibleChildren = [];

          var groups = [];

          vm.fields.forEach(function(field) {
              var groupClass = 'display-flex';
              var fieldClass = 'flex-1';

              var group = {
                  className: groupClass,
                  fieldGroup: [
                      field,
                      {
                          className: fieldClass,
                          type: 'input',
                          key: field['key'] + '_desc',
                          templateOptions: {
                              label: 'Description'
                          },
                      },
                      {
                          className: fieldClass,
                          type: 'checkbox',
                          key: field['key'] + '_hideExpression',
                          templateOptions: {
                              label: 'Hidden'
                          },
                      },
                      {
                          className: fieldClass,
                          type: 'checkbox',
                          key: field['key'] + '_readonly',
                          templateOptions: {
                              label: 'Read Only'
                          },
                      },
                  ]
              }
              groups.push(group)
          });

          vm.fields = groups;

          //count existing children
          var existing = {};
          for (var i in data['children']) {
            var element = data['children'][i];
            if (!(element['name'] in existing)) {
              existing[element['name']] = 1
            } else {
              existing[element['name']] += 1
            }
          }
          //calculate possible children
          var allChildren = [];

          for (var i in data['availableChildren']) {
            var child = data['availableChildren'][i];
            var a = vm.calculatePossibleChildren(child, existing);
            allChildren = allChildren.concat(a);
          }

          //remove children who's already at max
          console.log(allChildren)
          vm.possibleChildren = allChildren;
        };

        vm.calculatePossibleChildren = function(child, existing) {
          var templateElement;
          if (child['name'] in vm.allElements) {
              templateElement = vm.allElements[child['name']];
          } else {
              templateElement = 0;
          }
          var allChildren = [];
          if (child['type'] == 'element') {
            if ((!(child['name'] in existing)) || existing[child['name']] < templateElement['max'] || templateElement['max'] == -1) {
              allChildren.push(child['name']);
            }
          } else if (child['type'] == 'choise') {
            var c = vm.choiseCount.toString();
            vm.choiseCount += 1;
            allChildren.push('Choise'+c+' Begin');
            for (var i in child['elements']) {
              var el = child['elements'][i];
              if (el['type'] == 'element') {
                if (el['name'] in existing) {
                  var maxCount = templateElement['max'];
                  if (maxCount == -1 || existing[el['name']] < maxCount) {
                    return [el['name']];
                  } else {
                    return [];
                  }
                } else {
                  allChildren = allChildren.concat(vm.calculatePossibleChildren(el, existing));
                }
              } else {
                allChildren = allChildren.concat(vm.calculatePossibleChildren(el, existing));
              }
            }
            allChildren.push('Choise'+c+' End');
          }
          return allChildren;
        }

        vm.countChildrenWithName = function(parentName, childName) {
          console.log(parentName);
          if (parentName == 'none') {
            return 0;
          } else {
            var data = vm.existingElements[parentName];
            var count = 0;
            for (var index in data['children']) {
              if (data['children'][index]['name'] == childName) {
                count += 1;
              }
            }
            return count;
          }
        };

        vm.submitForm = function() {
            var data = vm.model;
            data['uuid'] = vm.uuid;
            $http({
                method: 'POST',
                url: '/template/edit/' + templateName + '/',
                data: data
            }).then(function() {
            });
            //TODO give feedback
        };

        vm.addChild = function(child) {
          $http.get('/template/struct/addChild/' + templateName + '/' + child + '/' + vm.uuid + '/').then(function(res) {
            console.log(res.data)
            $scope.treeElements = [];
            $scope.treeElements.push(vm.buildTree('root', res.data));
            vm.existingElements = res.data;
            $scope.showSelected(vm.uuid, false);
          });
        };

        vm.removeChild = function(child) {
            $http.get('/template/struct/removeChild/' + templateName + '/'+vm.uuid+'/').then(function(res) {
              $scope.treeElements = [];
              console.log(res.data)
              $scope.treeElements.push(vm.buildTree('root', res.data));
              vm.existingElements = res.data;
            });
        };

        vm.addAttribute = function() {
            vm.floatingVisable = !vm.floatingVisable;
            vm.floatingmodel = [];
            $http.get('/template/getAttributes/' + templateName + '/').then(function(res) {
              console.log(res.data);
              $scope.allAttributes = res.data;
            });
            // $scope.allAttributes = [];
        };

        $scope.addAttribute = function(data) {
            if (data == undefined) return;
            console.log(data);
            vm.fields.push(data);
            vm.floatingVisable = false;
            $http({
                method: 'POST',
                url: '/template/struct/addAttrib/' + templateName + '/' + vm.uuid + '/',
                data: data
            });
        }

        vm.saveAttribute = function() {
            var attribute = {};
            attribute['key'] = vm.floatingmodel['attribname'];
            attribute['type'] = 'input';
            var to = {};
            to['required'] = vm.floatingmodel['attribrequired'];
            to['label'] = vm.floatingmodel['attribname'];
            to['type'] = 'text';
            attribute['templateOptions'] = to;
            attribute['defaultValue'] = vm.floatingmodel['attribvalue'];
            vm.fields.push(attribute);
            vm.floatingVisable = false;
            $http({
                method: 'POST',
                url: '/template/struct/addAttrib/' + templateName + '/' + vm.uuid + '/',
                data: attribute
            });
        };

        vm.closeFloatingForm = function() {
            vm.floatingVisable = false;
            vm.floatingmodel = [];
        };

        vm.addElement = function() {
            vm.floatingElementVisable = !vm.floatingElementVisable;
            vm.floatingElementmodel = [];
            $http.get('/template/getElements/' + templateName + '/').then(function(res) {
            //   console.log(res.data);
              $scope.allElementsAvaliable = res.data;
            });
            // $scope.allElementsAvaliable
        };

        $scope.addEl = function(data) {
            console.log(data);
            data['parent'] = vm.uuid;
            $http({
                method: 'POST',
                url: '/template/struct/addExtensionChild/' + templateName + '/',
                data: data
            }).then(function(res) {
              console.log(res.data);
                vm.floatingElementVisable = false;
                $scope.treeElements = [];
                $scope.treeElements.push(vm.buildTree('root', res.data));
                vm.existingElements = res.data;
                $scope.showSelected(vm.uuid, false);
            });
        }

        vm.saveElement = function() {
            // console.log(sle)
            var element = {};
            element['parent'] = vm.uuid
            // element['templateOnly'] = false;
            // element['path'] = vm.selectedNode['path']; // + number ? //set in python ?
            element['name'] = vm.floatingElementmodel['elementname'];
            if ('kardMin' in vm.floatingElementmodel) {
                element['min'] = vm.floatingElementmodel['kardMin'];
            } else {
                element['min'] = 0;
            }
            if ('kardMax' in vm.floatingElementmodel) {
                element['max'] = vm.floatingElementmodel['kardMax'];
            } else {
                element['max'] = -1;
            }
            // element['children'] = [];
            $http({
                method: 'POST',
                url: '/template/struct/addUserChild/' + templateName + '/',
                data: element
            }).then(function(res) {
              console.log(res.data)
                vm.floatingElementVisable = false;
                $scope.treeElements = [];
                $scope.treeElements.push(vm.buildTree('root', res.data));
                vm.existingElements = res.data;
                $scope.showSelected(vm.uuid, false);
            });
        };

        vm.closeFloatingElementForm = function() {
            vm.floatingVisable = false;
            vm.floatingmodel = [];
        };

        vm.containsFiles = function() {
          var cf = 1;
          vm.containsFilesText = true;
          if (vm.existingElements[vm.uuid]['containsFiles'] == true) {
            cf = 0;
            vm.containsFilesText = false;
          }
          $http.get('/template/struct/setContainsFiles/' + templateName + '/'+vm.uuid+'/' + cf + '/').then(function(res) {
            vm.existingElements = res.data;
          });
        };

        vm.model = {
        };

        vm.fields = [];
        vm.floatingfields = [{
            key: 'attribname',
            type: 'input',
            templateOptions: {
                type: 'text',
                label: 'Name',
                placeholder: 'Name',
                required: true
            }
        }, {
            key: 'attribvalue',
            type: 'input',
            templateOptions: {
                type: 'text',
                label: 'Value',
                placeholder: 'Value',
                required: false
            }
        }, {
            key: 'attribrequired',
            type: 'checkbox',
            templateOptions: {
                type: 'checkbox',
                label: 'Required',
                required: false
            }
        }, ];
        vm.floatingVisable = false;
        vm.floatingElementfields = [{
            key: 'elementname',
            type: 'input',
            templateOptions: {
                type: 'text',
                label: 'Name',
                placeholder: 'Name',
                required: true
            }
        }, {
            key: 'textContent',
            type: 'input',
            templateOptions: {
                type: 'text',
                label: 'Text content',
                placeholder: 'content',
                required: false
            }
        }, {
            key: 'kardMin',
            type: 'input',
            templateOptions: {
                type: 'text',
                label: 'Min required count (default: 0)',
                placeholder: 'Min',
                required: false
            }
        }, {
            key: 'kardMax',
            type: 'input',
            templateOptions: {
                type: 'text',
                label: 'Max allowed count. -1 for infinite (default: -1)',
                placeholder: 'Max',
                required: false
            }
        }];
        vm.floatingElementVisable = false;

    }
})();
