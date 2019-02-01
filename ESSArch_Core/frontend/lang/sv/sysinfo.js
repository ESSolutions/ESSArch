angular.module('essarch.language').config(function($translateProvider) {
  $translateProvider.translations('sv', {
    SYSINFO: {
      BROKER: 'Broker',
      CONTACT: 'Kontakt',
      HOSTNAME: 'Värdnamn',
      MAX_CONCURRENCY: 'Max concurrency',
      MYSQLVERSION: 'MySQL-version',
      PID: 'PID',
      PYTHONPACKAGES: 'Pythonpaket',
      SETTINGSFLAGS: 'Inställningsflaggor',
      SUPPORT: 'Support',
      SUPPORTROW1: 'Behöver du hjälp? Har du hittat den bugg, eller har du en idé om en ny funktion?',
      SUPPORTROW2:
        'Klicka på support-länken nedan, logga in/gör ett konto och gör ett nytt ärende och vi kommer hantera ärendet snarast möjligt.',
      SUPPORTROW3:
        'Om ärendet är relaterat till ett misslyckat step/task kan du klistra in traceback i ärendets beskrivning så blir problemet lättare att identifiera. Klicka på step/taskens etikett',
      SYSTEMINFORMATION: 'Systeminformation',
      WORKERS: 'Workers',
    },
    VERSIONINFO: 'Version-info',
    VERSIONINFORMATION: 'Versionsinformation',
  });
});
