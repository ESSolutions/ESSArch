const eventType = ($resource, appConfig) => {
  return $resource(appConfig.djangoUrl + 'event-types/:id/:action/', {}, {});
};

export default eventType;
