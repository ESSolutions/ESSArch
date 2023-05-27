/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    COLLECTED: 'Collected',
    DELIVERED: 'Delivered',
    FAIL: 'Fail',
    FULL: 'Full',
    INACTIVE: 'Inactive',
    INUSE: 'In use',
    MOUNT: 'Mount',
    MOUNTED: 'Mounted',
    PLACED: 'Placed',
    RECEIVED: 'Received',
    ROBOT: 'Robot',
    UNMOUNT: 'Unmount',
    UNMOUNT_FORCE: 'Unmount (hard)',
    WRITE: 'Write',
  });
};
