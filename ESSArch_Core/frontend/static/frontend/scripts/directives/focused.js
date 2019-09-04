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

export default ($timeout, $parse) => {
  return {
    link: function($scope, element, attributes) {
      const model = $parse(attributes.focused);
      $scope.$watch(model, function(value) {
        if (value === true) {
          $timeout(function() {
            element[0].focus();
          });
        }
      });

      // set attribute value to 'false' on blur event:
      element.bind('blur', function() {
        if (model && model.assign) {
          $scope.$apply(model.assign($scope, false));
        }
      });
    },
  };
};
