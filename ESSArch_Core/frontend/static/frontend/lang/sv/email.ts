/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    EMAIL: {
      EMAIL: 'E-post',
      EMAIL_SENT: 'E-post skickat',
      RECEIVER: 'Mottagare',
      SENDER: 'Sändare',
      SUBJECT: 'Ämne',
    },
  });
};
