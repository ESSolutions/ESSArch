const conversion = ($http, appConfig) => {
  const service = {};
  service.getFinished = function(pageNumber, pageSize, sortString, searchString) {
    const data = {
      end_date__isnull: false,
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-jobs/',
      params: data,
    }).then(function(response) {
      let count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };

  service.getNext = function(pageNumber, pageSize, sortString, searchString) {
    const data = {
      status: 'PENDING',
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-jobs/',
      params: data,
    }).then(function(response) {
      let count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };

  service.getOngoing = function(pageNumber, pageSize, sortString, searchString) {
    const data = {
      status: 'STARTED',
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-jobs/',
      params: data,
    }).then(function(response) {
      let count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };

  service.getRules = function(pageNumber, pageSize, sortString, searchString) {
    const data = {
      page: pageNumber,
      page_size: pageSize,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-rules/',
      params: data,
    }).then(function(response) {
      let count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      return {
        count: count,
        data: response.data,
      };
    });
  };
  return service;
};

export default conversion;
