/*@ngInject*/
export default $translateProvider => {
  $translateProvider.translations('sv', {
    'Enter a valid email address': 'Ange en giltig email-adress',
    'Enter a valid URL with credentials\n(https://example.com,user,pass)':
      'Ange en giltig URL med inloggningsuppgifter\n(https://example.com,user,pass)',
    'This field is required': 'Detta fält är obligatoriskt',
    'Enter a valid URL': 'Ange en giltig URL',
  });
};
