const conversion = ($http, appConfig) => {
  const service = {};
  service.getFinished = function (pagination, sortString, searchString) {
    const data = {
      end_date__isnull: false,
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-jobs/',
      params: data,
    }).then(function (response) {
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

  service.getNext = function (pagination, sortString, searchString) {
    const data = {
      status: 'PENDING',
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-jobs/',
      params: data,
    }).then(function (response) {
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

  service.getOngoing = function (pagination, sortString, searchString) {
    const data = {
      status: 'STARTED',
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-jobs/',
      params: data,
    }).then(function (response) {
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

  service.getTemplates = function (pagination, sortString, searchString) {
    const data = {
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    };

    return $http({
      method: 'GET',
      url: appConfig.djangoUrl + 'conversion-templates/',
      params: data,
    }).then(function (response) {
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
