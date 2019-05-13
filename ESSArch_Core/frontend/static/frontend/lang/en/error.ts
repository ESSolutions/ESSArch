/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    ERROR: {
      ERROR: 'Error',
      CONNECTION_LOST: 'Lost connection to server',
      CONNECTION_RESTORED: 'Connection has been restored',
      ERROR_403: 'You do not have permission to perform this action',
      ERROR_500: 'Internal server error',
      ERROR_503: 'Request failed, try again',
      RETRY_CONNECTION: 'Retry connection',
      UNKNOWN_ERROR: 'Unknown error',
    },
  });
};
