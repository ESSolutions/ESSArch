/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch Preservation Platform (EPP)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

export default class AngularTreeCtrl {
  constructor(Tag, $scope, $rootScope, $translate, $uibModal, $log, $state) {
    $scope.treeOptions = {
      nodeChildren: 'children',
      dirSelectable: true,
      injectClasses: {
        ul: 'a1',
        li: 'a2',
        liSelected: 'a7',
        iExpanded: 'a3',
        iCollapsed: 'a4',
        iLeaf: 'a5',
        label: 'a6',
        labelSelected: 'a8',
      },
    };
    //TAGS
    $scope.tags = [];
    $rootScope.loadTags = function() {
      Tag.query({
        only_roots: true,
      }).$promise.then(function(data) {
        data.forEach(function(tag, index, array) {
          $scope.expandedNodes.forEach(function(node) {
            if (tag.id == node.id) {
              $scope.onNodeToggle(tag);
            }
          });
        });
        $scope.tags = data;
      });
    };
    $rootScope.loadTags();
    $scope.$on('load_tags', function() {
      $rootScope.loadTags();
    });
    $scope.onNodeToggle = function(node) {
      node.children.forEach(function(child, index, array) {
        child.$get().then(function(data) {
          array[index] = data;
        });
      });
    };
    $rootScope.selectedTag = null;
    $scope.showSelectedNode = function(node) {
      if ($rootScope.selectedTag && $rootScope.selectedTag.id === node.id) {
        $rootScope.selectedTag = null;
      } else {
        $rootScope.selectedTag = node;
      }
    };
    // Remove given node
    $scope.removeNode = function(node) {
      if (node.parentNode == null) {
        $scope.tags.forEach(function(element) {
          if (element.name == node.node.name) {
            element.$delete().then(function(response) {
              $rootScope.loadTags();
            });
          }
        });
      } else {
        node.parentNode.children.forEach(function(element) {
          if (element.name == node.node.name) {
            element.$delete().then(function(response) {
              $rootScope.loadTags();
            });
          }
        });
      }
    };
    //Update current node variable with selected node in map structure tree view
    $scope.updateCurrentNode = function(node, selected, parentNode) {
      if (selected) {
        $scope.currentNode = {node: node, parentNode: parentNode};
      } else {
        $scope.currentNode = null;
      }
    };
    //context menu data
    $scope.navMenuOptions = function(item) {
      return [
        [
          $translate.instant('ADD'),
          function($itemScope, $event, modelValue, text, $li) {
            $scope.addTagModal($itemScope.node, true);
          },
        ],
      ];
    };
    //context menu data
    $scope.navMenuItemOptions = function(item) {
      return [
        [
          $translate.instant('ADD'),
          function($itemScope, $event, modelValue, text, $li) {
            $scope.addTagModal($itemScope.node, false);
          },
        ],

        [
          $translate.instant('REMOVE'),
          function($itemScope, $event, modelValue, text, $li) {
            $scope.updateCurrentNode($itemScope.node, true, $itemScope.$parentNode);
            $scope.removeNode($scope.currentNode);
            $scope.selectedNode = null;
          },
        ],
        [
          $translate.instant('UPDATE'),
          function($itemScope, $event, modelValue, text, $li) {
            $scope.tagPropertiesModal($itemScope.node);
          },
        ],
        [
          $translate.instant('APPRAISAL'),
          function($itemScope, $event, modelValue, text, $li) {
            $state.go('home.appraisal', {tag: $itemScope.node});
          },
        ],
      ];
    };
    // open modal for add tag
    $scope.addTagModal = function(tag, isRoot) {
      if (isRoot) {
        $scope.parentTag = null;
      } else {
        $scope.parentTag = tag;
      }
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/add_tag_modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.addTag(tag, data, isRoot);
          $scope.parentTag = null;
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    // Add new tag
    $scope.addTag = function(tag, data, isRoot) {
      isRoot ? (data.parent = null) : (data.parent = tag.url);
      data.information_packages = [];
      if (isRoot) {
        Tag.save(data).$promise.then(function(response) {
          $rootScope.loadTags();
        });
      } else {
        Tag.save(data).$promise.then(function(response) {
          $rootScope.loadTags();
        });
      }
    };
    $scope.tagPropertiesModal = function(tag) {
      $scope.displayedTag = tag;
      const modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'static/frontend/views/tag_properties_modal.html',
        scope: $scope,
        controller: 'ModalInstanceCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result.then(
        function(data) {
          $scope.updateTag(tag, data);
        },
        function() {
          $log.info('modal-component dismissed at: ' + new Date());
        }
      );
    };
    $scope.updateTag = function(tag, data) {
      Tag.update(
        angular.extend(
          {
            id: tag.id,
          },
          data
        )
      ).$promise.then(function(response) {
        $rootScope.loadTags();
      });
    };
  }
}
