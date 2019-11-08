const event = ($resource, appConfig) => {
  return $resource(
    appConfig.djangoUrl + 'events/:id/:action/',
    {},
    {
      query: {
        method: 'GET',
        transformResponse: function(data, headers) {
          return {data: JSON.parse(data), headers: headers};
        },
      },
    }
  );
};

export default event;
