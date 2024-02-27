/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('sv', {
    COLLECTED: 'Samlade in',
    DELIVERED: 'Levererad',
    FAIL: 'Fel',
    FULL: 'Full',
    INACTIVE: 'Inaktiv',
    INUSE: 'Används',
    MOUNT: 'Montera',
    MOUNTED: 'Monterad',
    PLACED: 'Placerad',
    RECEIVED: 'Mottagen',
    ROBOT: 'Robot',
    UNMOUNT: 'Avmontera',
    UNMOUNT_FORCE: 'Avmontera (hårt)',
    WRITE: 'Skriv',
  });
};
