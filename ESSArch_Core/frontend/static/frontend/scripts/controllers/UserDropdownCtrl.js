export default class UserDropdownCtrl {
  constructor($scope, $log, $state, djangoAuth, $translate, $uibModal) {
    var options, optionsAuth;
    var vm = this;

    vm.$onInit = function() {
      options = [
        {
          label: $translate.instant('LOGIN'),
          click: function() {
            $state.go('login');
          },
        },
      ];

      optionsAuth = [
        {
          label: $translate.instant('USERSETTINGS'),
          click: function() {
            $state.go('home.userSettings');
          },
        },
        {
          label: $translate.instant('CHANGE_PASSWORD'),
          click: function() {
            $scope.changePasswordModal();
          },
        },
        {
          label: $translate.instant('LOGOUT'),
          click: function() {
            vm.auth = null;
            djangoAuth.logout();
          },
        },
      ];
    };

    $scope.$on('djangoAuth.logged_out', function(event) {
      window.location.replace('/');
    });

    $scope.$watch(
      function() {
        return djangoAuth.authenticated;
      },
      function() {
        if (!djangoAuth.authenticated) {
          $scope.editUserOptions = options;
        } else {
          $scope.editUserOptions = optionsAuth;
        }
      },
      true
    );

    $scope.status = {
      isopen: false,
    };

    $scope.toggleDropdown = function($event) {
      $event.preventDefault();
      $event.stopPropagation();
      $scope.status.isopen = !$scope.status.isopen;
    };

    $scope.changePasswordModal = function() {
      var modalInstance = $uibModal.open({
        animation: true,
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'modals/change_password_modal.html',
        scope: $scope,
        size: 'md',
        controller: 'ChangePasswordModalCtrl',
        controllerAs: '$ctrl',
        resolve: {
          data: {},
        },
      });
      modalInstance.result
        .then(function(data) {})
        .catch(function() {
          $log.info('modal-component dismissed at: ' + new Date());
        });
    };

    $scope.appendToEl = angular.element(document.querySelector('#dropdown-long-content'));
  }
}

UserDropdownCtrl.$inject = ['$scope', '$log', '$state', 'djangoAuth', '$translate', '$uibModal'];
