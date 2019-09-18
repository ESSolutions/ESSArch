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

const requests = (Notifications, IP, Workarea, $state) => {
  function preserve(ip, request) {
    let promise;
    if ($state.includes('**.workarea.**') && ip.workarea && ip.workarea[0].read_only === false) {
      promise = Workarea.preserve(angular.extend(request, {id: ip.id})).$promise;
    } else {
      promise = IP.preserve(angular.extend(request, {id: ip.id})).$promise;
    }
    return promise.then(function(response) {
      Notifications.add(response.detail, 'success', 3000);
      return response;
    });
  }
  function access(ip, data) {
    return IP.access(angular.extend(data, {id: ip.id})).$promise.then(function(response) {
      Notifications.add(response.detail, 'success', 3000);
      return response;
    });
  }
  function moveToApproval(ip, data) {
    let promise;
    if ($state.includes('**.workarea.**') && ip.workarea && ip.workarea[0].read_only === false) {
      promise = Workarea.moveToApproval(angular.extend(data, {id: ip.id})).$promise;
    } else {
      promise = IP.moveToApproval(angular.extend(data, {id: ip.id})).$promise;
    }
    return promise.then(function(response) {
      Notifications.add(response.detail, 'success', 3000);
      return response;
    });
  }
  return {
    preserve: preserve,
    access: access,
    moveToApproval: moveToApproval,
  };
};

export default requests;
