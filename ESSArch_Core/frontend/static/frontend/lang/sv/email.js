/*@ngInject*/
export default $translateProvider => {
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
