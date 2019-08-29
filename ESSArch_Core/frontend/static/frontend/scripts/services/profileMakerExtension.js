const ProfileMakerExtension = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'profilemaker-extensions/:id/:action/',
    {id: '@id'},
    {
      add: {
        method: 'POST',
      },
    }
  );
};

export default ProfileMakerExtension;
