angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('en', {
    SYSINFO: {
      BROKER: 'Broker',
      CONTACT: 'Contact',
      HOSTNAME: 'Hostname',
      'MAX CONCURRENCY': 'Max concurrency',
      MYSQLVERSION: 'MySQL version',
      PID: 'PID',
      PYTHONPACKAGES: 'Python packages',
      SETTINGSFLAGS: 'Settings Flags',
      SUPPORT: 'Support',
      SUPPORTROW1: 'Do you need support? have you found a bug, or do you have an idea for a new feature?',
      SUPPORTROW2:
        'Click on the support link below, log in/create user and create a new issue and we will take care of it as soon as possible.',
      SUPPORTROW3:
        'If the issue is related to a task/step failing you can include the traceback from the step/task and paste it into the issue description to make the problem easier to identify. Click on the step/task label',
      SYSTEMINFORMATION: 'System Information',
      WORKERS: 'Workers',
    },
    VERSIONINFO: 'Version info',
    VERSIONINFORMATION: 'Version Information',
  });
});
