angular
  .module('essarch.controllers')
  .controller('ChangePasswordModalCtrl', function($uibModalInstance, djangoAuth, data) {
    var $ctrl = this;
    if (data) {
      $ctrl.data = data;
    }

    $ctrl.error_messages_old = [];
    $ctrl.error_messages_pw1 = [];
    $ctrl.error_messages_pw2 = [];

    $ctrl.changePassword = function() {
      djangoAuth
        .changePassword($ctrl.pw1, $ctrl.pw2, $ctrl.oldPw)
        .then(function(response) {
          $uibModalInstance.close($ctrl.data);
        })
        .catch(function(error) {
          $ctrl.error_messages_old = error.old_password || [];
          $ctrl.error_messages_pw1 = error.new_password1 || [];
          $ctrl.error_messages_pw2 = error.new_password2 || [];
          $ctrl.errors = error.data;
        });
    };

    $ctrl.cancel = function() {
      $uibModalInstance.dismiss('cancel');
    };
  });
