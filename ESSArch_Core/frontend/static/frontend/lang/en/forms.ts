/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    'Enter a valid email address': 'Enter a valid email address',
    'Enter a valid URL with credentials\n(https://example.com,user,pass)':
      'Enter a valid URL with credentials\n(https://example.com,user,pass)',
    'This field is required': 'This field is required',
    'Enter a valid URL': 'Enter a valid URL',
    'This value is too long': 'This value is too long',
  });
};
