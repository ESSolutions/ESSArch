'use strict';

/* @ngInject */
const djangoAuth = ($q, $http, $rootScope, $window) => {
  // AngularJS will instantiate a singleton by calling "new" on this function
  const service = {
    /* START CUSTOMIZATION HERE */
    // Change this to point to your Django REST Auth API
    // e.g. /api/rest-auth  (DO NOT INCLUDE ENDING SLASH)
    API_URL: '/api/auth',
    // Set use_session to true to use Django sessions to store security token.
    // Set use_session to false to store the security token locally and transmit it as a custom header.
    use_session: true,
    /* END OF CUSTOMIZATION */
    authenticated: null,
    authPromise: null,
    request: function(args) {
      // Continue
      args = args || {};
      const deferred = $q.defer(),
        url = this.API_URL + args.url,
        method = args.method || 'GET',
        params = args.params || {},
        data = args.data || {};
      // Fire the request, as configured.
      $http({
        url: url,
        withCredentials: this.use_session,
        method: method.toUpperCase(),
        params: params,
        data: data,
      })
        .then(
          angular.bind(this, function(data, status) {
            deferred.resolve(data, status);
          })
        )
        .catch(
          angular.bind(this, function(data, status, headers, config) {
            console.log('error syncing with: ' + url);
            // Set request status
            if (data) {
              data.status = status;
            }
            if (status == 0) {
              if (data == '') {
                data = {};
                data['status'] = 0;
                data['non_field_errors'] = ['Could not connect. Please try again.'];
              }
              // or if the data is null, then there was a timeout.
              if (data == null) {
                // Inject a non field error alerting the user
                // that there's been a timeout error.
                data = {};
                data['status'] = 0;
                data['non_field_errors'] = ['Server timed out. Please try again.'];
              }
            }
            deferred.reject(data, status, headers, config);
          })
        );
      return deferred.promise;
    },
    login: function(username, password) {
      const djangoAuth = this;
      return this.request({
        method: 'POST',
        url: '/login/',
        data: {
          username: username,
          password: password,
        },
      }).then(function(response) {
        const data = response.data;
        djangoAuth.authenticated = true;
        $rootScope.$broadcast('djangoAuth.logged_in', data);
        return data;
      });
    },
    logout: function() {
      return ($window.location.href = this.API_URL + '/logout/');
    },
    changePassword: function(password1, password2, oldPassword) {
      return this.request({
        method: 'POST',
        url: '/password/change/',
        data: {
          new_password1: password1,
          new_password2: password2,
          old_password: oldPassword,
        },
      });
    },
    resetPassword: function(email) {
      return this.request({
        method: 'POST',
        url: '/password/reset/',
        data: {
          email: email,
        },
      });
    },
    profile: function() {
      return this.request({
        method: 'GET',
        url: '/user/',
      });
    },
    updateProfile: function(data) {
      return this.request({
        method: 'PATCH',
        url: '/user/',
        data: data,
      });
    },
    verify: function(key) {
      return this.request({
        method: 'POST',
        url: '/registration/verify-email/',
        data: {key: key},
      });
    },
    confirmReset: function(uid, token, password1, password2) {
      return this.request({
        method: 'POST',
        url: '/password/reset/confirm/',
        data: {
          uid: uid,
          token: token,
          new_password1: password1,
          new_password2: password2,
        },
      });
    },
    authenticationStatus: function(restrict, force) {
      // Set restrict to true to reject the promise if not logged in
      // Set to false or omit to resolve when status is known
      // Set force to true to ignore stored value and query API
      restrict = restrict || false;
      force = force || false;
      if (this.authPromise == null || force) {
        this.authPromise = this.request({
          method: 'GET',
          url: '/user/',
        });
      }
      const da = this;
      const getAuthStatus = $q.defer();
      if (this.authenticated != null && !force) {
        // We have a stored value which means we can pass it back right away.
        if (this.authenticated == false && restrict) {
          getAuthStatus.reject('User is not logged in.');
        } else {
          getAuthStatus.resolve();
        }
      } else {
        // There isn't a stored value, or we're forcing a request back to
        // the API to get the authentication status.
        this.authPromise.then(
          function(response) {
            da.authenticated = true;
            getAuthStatus.resolve(response);
          },
          function() {
            da.authenticated = false;
            if (restrict) {
              getAuthStatus.reject('User is not logged in.');
            } else {
              getAuthStatus.resolve();
            }
          }
        );
      }
      return getAuthStatus.promise;
    },
    initialize: function(url) {
      this.API_URL = url;
      return this.authenticationStatus();
    },
  };
  return service;
};

export default djangoAuth;
