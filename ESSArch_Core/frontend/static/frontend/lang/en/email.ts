/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    EMAIL: {
      EMAIL: 'Email',
      EMAIL_SENT: 'Email sent',
      RECEIVER: 'Receiver',
      SENDER: 'Sender',
      SUBJECT: 'Subject',
    },
  });
};
