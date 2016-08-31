// var json = require('./data.json');

(function() {


    'use strict';

    angular
        .module('formlyApp')
        .controller('MainController', MainController);


    function MainController($scope, $http) {

        //TODO not hardcoded 'test' in future
        $http.get('/template/struct/test').then(function(res) {
            var treeRoot = document.getElementById("tree");
            vm.buildTree('root', treeRoot, res.data);
        });

        var vm = this;
        vm.title = 'title'; // placeholder only
        vm.countAll = {};
        vm.anyAttribute = false;
        vm.anyElement = false;
        vm.possibleChildren = [];
        vm.existingChildren = [];

        vm.buildTree = function(uuid, divElement, data) {
          var element = data[uuid];
          var newDiv = document.createElement("div");
          var childDiv = document.createElement('div');
          var newP = document.createElement("p");
          childDiv.className = 'treeChildren';
          newDiv.className = 'treerow';
          newP.onclick = function(e) {
            e.target.nextSibling.classList.toggle("hidden");
          };
          newP.innerHTML = element['name'];

          newDiv.appendChild(newP);
          newDiv.appendChild(childDiv);
          divElement.appendChild(newDiv);

          for (var index in element['children']) {
            var child = element['children'][index];
            if (child['type'] == 'sequence') {
              for (var i in child['elements']) {
                var el = child['elements'][i];
                if ('uuid' in el) {
                  vm.buildTree(el['uuid'], childDiv, data);
                } else {
                  var nd = document.createElement("div");
                  nd.className = 'treerow';
                  var np = document.createElement("p");
                  np.innerHTML = el['name']
                  nd.appendChild(np);
                  childDiv.appendChild(nd);
                }
                // if has uuid, add that element, else add greyed out element
              }
            } else if (child['type'] == 'choise') {
              for (var i in child['elements']) {
                var el = child['elements'][i];
                // console.log(el['name']);
                var nd = document.createElement("div");
                nd.className = 'treerow deleted';
                var np = document.createElement("p");
                np.innerHTML = el['name']
                nd.appendChild(np);
                childDiv.appendChild(nd);
                // if has uuid, add that element, else add greyed out element
              }
            }
          }
        };

        vm.expandNode = function(node) {
          node.classList.toggle("hidden");
          console.log('expand');
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
            vm.selectedNode = sel;
            $http.get(('/template/struct/test/' + sel['key'])).then(function(res) {
                console.log(res.data);
                var data = JSON.parse(res.data);
                vm.title = sel['name'].charAt(0).toUpperCase() + sel['name'].slice(1); //TODO make first char capitol
                vm.min = data['min'];
                vm.max = data['max'];
                if (vm.max == -1) {
                    vm.max = 'infinite';
                }
                vm.uuid = sel['key'];
                // vm.schemaName = 'test';
                var arr = [];
                vm.fields = data['form'];
                if (data['userForm'].length > 0) {
                    vm.fields.push({template: '<hr/><p><b>User defined attributes</b></p>'}); //divider
                    vm.fields = vm.fields.concat(data['userForm']);
                }
                if (vm.min == 0) {
                    vm.canDelete = true;
                } else {
                    vm.canDelete = false;
                }
                vm.model = data['formData'];
                vm.selectedElement = data;
                vm.anyAttribute = data['anyAttribute'];
                vm.anyElement = data['anyElement'];
                vm.possibleChildren = data['avaliableChildren'];
            });
        };

        vm.submitForm = function() {
            var data = vm.model;
            data['uuid'] = vm.uuid;
            data['schemaName'] = vm.schemaName;
            // console.log(vm.model);
            $http({
                method: 'POST',
                url: '/template/edit/test/',
                data: data
            }).then(function(res) {
            });
            //TODO give feedback
            // $scope.showSelected(vm.selectedNode, false);
        };

        // vm.onSubmit = function() {
        //     for (var key in vm.model) {
        //         for (var j = 0; j < vm.selectedNode.attributes.length; j++) {
        //             console.log(key);
        //             console.log(vm.selectedNode.attributes[j].key);
        //             if (key == vm.selectedNode.attributes[j].key) {
        //                 vm.selectedNode.attributes[j].defaultValue = vm.model[key];
        //                 break;
        //             }
        //         }
        //     }
        // };

        vm.addChild = function(child) {
          console.log(child.element);
            $http.get('/template/struct/addChild/test/' + child.name + '/' + vm.uuid + '/').then(function(res) {
                // $http.get('/template/struct/test').then(function(res) {
                //     $scope.treeInfo = [JSON.parse(res.data)];
                //     vm.tree = JSON.parse(res.data);
                // });
            });

        };

        vm.addAttribute = function() {
            vm.floatingVisable = !vm.floatingVisable;
            vm.floatingmodel = [];
        };

        vm.closeFloatingForm = function() {
            vm.floatingVisable = false;
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
                url: '/template/struct/addAttrib/test/' + vm.uuid + '/',
                data: attribute
            });
        };

        vm.addElement = function() {
            vm.floatingElementVisable = !vm.floatingElementVisable;
            vm.floatingElementmodel = [];
        };

        vm.saveElement = function() {
            // console.log(sle)
            var element = {};
            element['templateOnly'] = false;
            element['path'] = vm.selectedNode['path']; // + number ? //set in python ?
            element['name'] = vm.floatingElementmodel['elementname'];
            var meta = {};
            if ('kardMin' in vm.floatingElementmodel) {
                meta['minOccurs'] = vm.floatingElementmodel['kardMin'];
            } else {
                meta['minOccurs'] = 0;
            }
            if ('kardMax' in vm.floatingElementmodel) {
                meta['maxOccurs'] = vm.floatingElementmodel['kardMax'];
            } else {
                meta['maxOccurs'] = -1;
            }
            element['meta'] = meta;
            element['children'] = [];
            $http({
                method: 'POST',
                url: '/template/struct/addUserChild/test/',
                data: element
            }).then(function(res) {
                vm.floatingElementVisable = false;
                $scope.treeInfo = [JSON.parse(res.data)];
                vm.tree = JSON.parse(res.data);
            });
        };

        vm.removeElement = function(child) {
            //post path and if it is one of the last so it should not be removed but merly changed value of templateOnly
            var data = {};
            data['path'] = vm.selectedNode['path'];
            if (vm.countOfCurrent <= 1) {
                data['remove'] = false;
            } else {
                data['remove'] = true;
            }
            $http({
                method: 'POST',
                url: '/template/struct/removeChild/test/',
                data: data
            }).then(function() {
                $http.get('/template/struct/test').then(function(res) {
                    $scope.treeInfo = [JSON.parse(res.data)];
                    vm.tree = JSON.parse(res.data);
                });
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
