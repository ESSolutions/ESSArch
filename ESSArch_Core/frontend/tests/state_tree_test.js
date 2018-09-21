/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
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

'use strict';

describe('StateTreeCtrl', function() {
    beforeEach(module('myApp'));
    window.onbeforeunload = jasmine.createSpy();

    var $controller, $scope;

    beforeEach(inject(function(_$controller_){
        $controller = _$controller_;
    }));

    describe('toggling', function() {
        var $scope, controller;

        beforeEach(inject(function($rootScope){
            $scope = $rootScope.$new();
            controller = $controller('StateTreeCtrl', { $scope: $scope });
        }));

        describe('controller.getArgsString', function() {
            it('with non null values', function() {
                var array = ['arg1', 'arg2', 'arg3'];
                expect(controller.getArgsString(array)).toBe('arg1, arg2, arg3');
            });

            it('with null values', function() {
                var array = [null, 'arg2', null];
                expect(controller.getArgsString(array)).toBe('null, arg2, null');
            });
        });
    });
});
