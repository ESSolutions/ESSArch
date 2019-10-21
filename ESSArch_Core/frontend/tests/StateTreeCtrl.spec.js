/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

describe('StateTreeCtrl', function() {
  beforeEach(module('essarch.controllers'));

  var $controller, $scope, controller, Task, Step, StateTree;

  beforeEach(inject(function(_$controller_) {
    $controller = _$controller_;
  }));

  Task = jasmine.createSpyObj('Task', ['get', 'validations']);

  Step = jasmine.createSpyObj('Step', ['get']);

  StateTree = jasmine.createSpyObj('StateTree', ['getTreeData']);
  module(function($provide) {
    $provide.value('Task', Task);
    $provide.value('Step', Step);
    $provide.value('StateTree', StateTree);
  });

  beforeEach(inject(function($rootScope) {
    $scope = $rootScope.$new();
    controller = $controller('StateTreeCtrl', {
      $scope: $scope,
      Task: Task,
      Step: Step,
      StateTree: StateTree,
    });
  }));

  it('controller defined', function() {
    expect($controller).toBeDefined();
  });

  describe('controller.getArgsString', function() {
    it('with non null values', function() {
      this.array = ['arg1', 'arg2', 'arg3'];
      expect(controller.getArgsString(this.array)).toBe('arg1, arg2, arg3');
    });

    it('with null values', function() {
      this.array = [null, 'arg2', null];
      expect(controller.getArgsString(this.array)).toBe('null, arg2, null');
    });
  });

  describe('task', function() {
    describe('getTask', function() {
      beforeEach(inject(function($q) {
        var TaskPromise = {
          get: $q.defer(),
        };

        Task.get.and.returnValue({$promise: TaskPromise.get.promise});

        TaskPromise.get.resolve({
          id: '6ac9f7a1-a144-4c07-adef-16e0a4125b0f',
          name: 'ESSArch_Core.ip.tasks.CreatePhysicalModel',
          label: 'ESSArch_Core.ip.tasks.CreatePhysicalModel',
          status: 'SUCCESS',
          progress: 100,
          time_created: '2018-09-18T16:42:00.0+02:00',
          time_started: '2018-09-18T16:42:00.0+02:00',
          time_done: '2018-09-18T16:43:01.0+02:00',
          undone: null,
          undo_type: false,
          retried: null,
          responsible: 'admin',
          hidden: false,
        });
        $scope.$apply(function() {
          $scope.getTask({id: '6ac9f7a1-a144-4c07-adef-16e0a4125b0f'}).then(function() {});
        });
      }));

      it('Task resource is called', function() {
        expect(Task.get).toHaveBeenCalled();
      });
      it('Task resource returns correct data', function() {
        expect($scope.currentStepTask.id).toEqual('6ac9f7a1-a144-4c07-adef-16e0a4125b0f');
      });
      it('task duration is correctly calculated', function() {
        expect($scope.currentStepTask.duration).toEqual('00:01:01.000');
      });
    });
    describe('vm.getValidations', function() {
      beforeEach(inject(function($q) {
        var TaskPromise = {
          validations: $q.defer(),
        };
        Task.validations.and.returnValue({$promise: TaskPromise.validations.promise});

        TaskPromise.validations.resolve([
          {
            id: '28b0af54-316b-44f3-afe2-4dda571c1501',
            filename: 'mets.xml',
            validator: 'XMLSchemaValidator',
            passed: true,
            message: '',
            information_package: '25605b34-3606-4ef3-93bf-53b0709c9454',
            required: true,
          },
        ]);

        var tableState = {
          sort: {
            predicate: 'time_started',
            reverse: false,
          },
          search: {},
          pagination: {
            start: 0,
            totalItemCount: 0,
            number: 10,
          },
        };

        $scope.currentStepTask = {id: '6ac9f7a1-a144-4c07-adef-16e0a4125b0f'};

        $scope.$apply(function() {
          controller.getValidations(tableState).then(function() {});
        });
      }));
      it('Task.validations is called', function() {
        expect(Task.validations).toHaveBeenCalled();
      });
      it('validation result should not be empty', function() {
        expect(controller.validations.length).not.toBeLessThan(0);
      });
      it('validation result list contains given object', function() {
        expect(controller.validations[0].id).toEqual('28b0af54-316b-44f3-afe2-4dda571c1501');
      });
    });
  });
  describe('step', function() {
    describe('getStep', function() {
      beforeEach(inject(function($q) {
        var StepPromise = {
          get: $q.defer(),
        };

        Step.get.and.returnValue({$promise: StepPromise.get.promise});

        StepPromise.get.resolve({
          id: 'd9a827f8-ef52-4ec5-9194-5e2c99a0e1b8',
          name: 'Validate AIP',
          result: null,
          type: null,
          user: '',
          parallel: false,
          status: 'SUCCESS',
          progress: 100,
          undone: false,
          time_created: '2018-08-03T15:16:32.471865+02:00',
          parent_step_pos: 2,
          task_count: 4,
          failed_task_count: 0,
          exception: null,
          traceback: null,
        });
        $scope.$apply(function() {
          $scope.getStep({id: 'd9a827f8-ef52-4ec5-9194-5e2c99a0e1b8'}).then(function() {});
        });
      }));

      it('Step resource is called', function() {
        expect(Step.get).toHaveBeenCalled();
      });
      it('Step resource returns correct data', function() {
        expect($scope.currentStepTask.id).toEqual('d9a827f8-ef52-4ec5-9194-5e2c99a0e1b8');
      });
    });
  });

  describe('get step/task-list', function() {
    beforeEach(inject(function($q) {
      var StateTreePromise = {
        getTreeData: $q.defer(),
      };
      StateTree.getTreeData.and.returnValue(StateTreePromise.getTreeData.promise);

      StateTreePromise.getTreeData.resolve([
        {
          id: 'cec675f3-8874-4d0a-bedf-1e85770799bd',
          flow_type: 'step',
          name: 'Receive SIP',
          label: 'Receive SIP',
          hidden: false,
          progress: 100,
          status: 'SUCCESS',
          responsible: '',
          step_position: 0,
          time_started: '2018-08-03T15:16:39.575387+02:00',
          time_done: '2018-08-03T15:16:39.706938+02:00',
          undo_type: null,
          undone: false,
          retried: null,
        },
        {
          id: '531991ab-dbf3-4adf-b957-61b1c514a71f',
          flow_type: 'step',
          name: 'Access AIP',
          label: 'Access AIP',
          hidden: false,
          progress: 100,
          status: 'SUCCESS',
          responsible: '',
          step_position: 0,
          time_started: '2018-08-13T21:56:52.679244+02:00',
          time_done: '2018-08-13T21:56:53.191450+02:00',
          undo_type: null,
          undone: false,
          retried: null,
        },
      ]);
      $scope.$apply(function() {
        $scope.statusViewUpdate({id: 'cec675f3-8874-4d0a-bedf-1e857707uhjg'}).then(function() {});
      });
    }));
    it('StateTree.getTreeData is called', function() {
      expect(StateTree.getTreeData).toHaveBeenCalled();
    });
  });
});
