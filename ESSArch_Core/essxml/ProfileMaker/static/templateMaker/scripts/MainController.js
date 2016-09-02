// var json = require('./data.json');

(function() {


    'use strict';

    angular
        .module('formlyApp')
        .controller('MainController', MainController);


    function MainController($scope, $http) {

        $http.get('/template/struct/' + templateName).then(function(res) {
            $scope.treeElements = [];
            $scope.treeElements.push(vm.buildTree('root', res.data));
            vm.existingElements = res.data;
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

        vm.buildTree = function(uuid, data) {
          var element = data[uuid];
          var result = {}
          result['name'] = element['name'];
          result['key'] = uuid;
          var children = [];

          for (var index in element['children']) {
            var child = element['children'][index];
            if (child['type'] == 'sequence') {
              for (var i in child['elements']) {
                var el = child['elements'][i];
                if ('uuid' in el) {
                  children.push(vm.buildTree(el['uuid'], data));
                } else {
                  // var r = {}
                  // r['name'] = el['name'];
                  // r['children'] = [];
                  // r['key'] = el['name'];
                  // children.push(r);
                }
              }
            } else if (child['type'] == 'choise') {
              var ch = [];
              var done = false;
              for (var i in child['elements']) {
                var el = child['elements'][i];
                var r = {};
                r['name'] = el['name'];
                r['children'] = [];
                r['key'] = el['name'];
                if ('uuid' in el) {
                  ch = [];
                  children.push(vm.buildTree(el['uuid'], data));
                  done = true;
                } else {
                  ch.push(r);
                }
              }
              if (!done) {
                var c = {};
                c['name'] = 'choose one of:'
                c['children'] = ch;
                c['key'] = 'choise' + vm.choiseCount;
                vm.choiseCount += 1;
                children.push(c);
              }
            }
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
          if (sel == 'root') {
            vm.canDelete = false;
          }
          vm.model = data['formData'];
          vm.selectedElement = data;
          vm.anyAttribute = data['anyAttribute'];
          vm.anyElement = data['anyElement'];
          vm.possibleChildren = [];
          // console.log(data['avaliableChildren']);
          var pc = {};
          var doneChoises = [];
          for (var index in data['children']) {
            var child = data['children'][index];
            if (child['type'] == 'sequence') {
              for (var i in child['elements']) {
                var el = child['elements'][i];
                if ('uuid' in el) {
                  if (!(el['name'] in pc)) {
                    pc[el['name']] = 1;
                  } else {
                    pc[el['name']] = parseInt(pc[el['name']]);
                  }
                }
              }
            } else if (child['type'] == 'choise') {
              for (var i in child['elements']) {
                var el = child['elements'][i];
                if ('uuid' in el) {
                  doneChoises.push(index);
                  break;
                }
              }
            }
          }
          var ch = vm.allElements[data['name']]['children'];
          if (ch != undefined) {
            for (var index in ch) {
              el = ch[index];
              if (el['type'] == 'sequence') {
                for (var i in el['elements']) {
                  var e = el['elements'][i];
                  if (!(e['name'] in pc)) {
                    pc[e['name']] = 0;
                  }
                }
              } else {
                if (!(index in doneChoises)) {
                  for (i in el['elements']) {
                    var e = el['elements'][i];
                    pc[e['name']] = 0;
                  }
                }
              }
            }
          }
          for (var key in pc) {
            if (pc[key] < vm.allElements[key]['max'] || vm.allElements[key]['max'] == -1) {
              vm.possibleChildren.push(key);
            }
          }
        };

        vm.countChildrenWithName = function(parentName, childName) {
          if (parentName == 'none') {
            return 1;
          } else {
            var data = vm.existingElements[parentName];
            var count = 0;
            for (var index in data['children']) {
              var el = data['children'][index];
              if (el['type'] == 'sequence') {
                for (var i in el['elements']) {
                  var e = el['elements'][i];
                  if (e['name'] == childName && 'uuid' in e) {
                    count += 1;
                  }
                }
              } else {
                for (i in el['elements']) {
                  var e = el['elements'][i];
                  if (e['name'] == childName && 'uuid' in e) {
                    count += 1;
                  }
                }
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
            $scope.treeElements = [];
            $scope.treeElements.push(vm.buildTree('root', res.data));
            vm.existingElements = res.data;
            $scope.showSelected(vm.uuid, false);
          });
        };

        vm.removeChild = function(child) {
            $http.get('/template/struct/removeChild/' + templateName + '/'+vm.uuid+'/').then(function(res) {
              $scope.treeElements = [];
              $scope.treeElements.push(vm.buildTree('root', res.data));
              vm.existingElements = res.data;
            });
        };

        vm.addAttribute = function() {
            vm.floatingVisable = !vm.floatingVisable;
            vm.floatingmodel = [];
        };

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
        };

        // vm.saveElement = function() {
        //     // console.log(sle)
        //     var element = {};
        //     element['templateOnly'] = false;
        //     element['path'] = vm.selectedNode['path']; // + number ? //set in python ?
        //     element['name'] = vm.floatingElementmodel['elementname'];
        //     var meta = {};
        //     if ('kardMin' in vm.floatingElementmodel) {
        //         meta['minOccurs'] = vm.floatingElementmodel['kardMin'];
        //     } else {
        //         meta['minOccurs'] = 0;
        //     }
        //     if ('kardMax' in vm.floatingElementmodel) {
        //         meta['maxOccurs'] = vm.floatingElementmodel['kardMax'];
        //     } else {
        //         meta['maxOccurs'] = -1;
        //     }
        //     element['meta'] = meta;
        //     element['children'] = [];
        //     $http({
        //         method: 'POST',
        //         url: '/template/struct/addUserChild/' + templateName + '/',
        //         data: element
        //     }).then(function(res) {
        //         vm.floatingElementVisable = false;
        //         $scope.treeInfo = [JSON.parse(res.data)];
        //         vm.tree = JSON.parse(res.data);
        //     });
        // };

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
