/*
ESSArch is an open source archiving and digital preservation system

ESSArch
Copyright (C) 2005-2019 ES Solutions AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Contact information:
Web - http://www.essolutions.se
Email - essarch@essolutions.se
*/

const listViewService = (
  Tag,
  Profile,
  IP,
  Workarea,
  WorkareaFiles,
  Order,
  IPReception,
  Event,
  EventType,
  SA,
  $q,
  $http,
  $state,
  appConfig,
  $rootScope
) => {
  /**
   * Map given table type with an url
   * @param {String} table - Type of table, example: "ip", "events", "workspace"
   * @param {string} [id] - Optional id for url
   */
  function tableMap(table, id) {
    const map = {
      ip: 'information-packages/',
      events: 'information-packages/' + id + '/events/',
      reception: 'ip-reception/',
      workspace: 'workareas/',
      storage_medium: 'storage-mediums/',
      storage_object: 'storage-objects/',
      robot: 'robots/',
      tapeslot: 'tape-slots/',
      tapedrive: 'tape-drives/',
      robot_queue: 'robot-queue/',
      robot_queue_for_robot: 'robots/' + id + '/queue/',
      io_queue: 'io-queue/',
    };
    return map[table];
  }

  /**
   * Check number of items and how many pages a table has.
   * Used to update tables correctly when amount of pages is reduced.
   * @param {String} table - Type of table, example: "ip", "events", "workspace"
   * @param {Integer} pageSize - Page size
   * @param {Object} filters - All filters and relevant sort string etc
   * @param {String} [id] - ID used in table url, for example IP ID
   */
  function checkPages(table, pageSize, filters, id) {
    const data = angular.extend(
      {
        page: 1,
        page_size: pageSize,
      },
      filters
    );
    let url;
    if (id) {
      url = tableMap(table, id);
    } else {
      url = tableMap(table);
    }
    return $http.head(appConfig.djangoUrl + url, {params: data}).then(function(response) {
      let count = response.headers('Count');
      if (count == null) {
        count = response.length;
      }
      if (count == 0) {
        count = 1;
      }
      return {
        count: count,
        numberOfPages: Math.ceil(count / pageSize),
      };
    });
  }

  //Gets data for list view i.e information packages
  function getListViewData(
    pagination,
    sortString,
    searchString,
    state,
    viewType,
    columnFilters,
    archived,
    workarea,
    params
  ) {
    let data = angular.extend(
      {
        page: pagination.pageNumber,
        page_size: pagination.number,
        pager: pagination.pager,
        ordering: sortString,
        state: state,
        search: searchString,
        view_type: viewType,
        archived: archived,
      },
      columnFilters,
      params
    );

    if (workarea) {
      data = angular.extend(data, {workarea: workarea});
    }

    if ($rootScope.selectedTag != null) {
      return Tag.information_packages(angular.extend({id: $rootScope.selectedTag.id}, data)).$promise.then(function(
        resource
      ) {
        let count = resource.$httpHeaders('Count');
        if (count == null) {
          count = resource.length;
        }
        return {
          count: count,
          data: resource,
        };
      });
    } else {
      return IP.query(data).$promise.then(function(resource) {
        let count = resource.$httpHeaders('Count');

        if (count == null) {
          count = resource.length;
        }
        return {
          count: count,
          data: resource,
        };
      });
    }
  }

  //Fetches IP's for given workarea (ingest or access)
  function getWorkareaData(workarea, pagination, filters, sortString, searchString, viewType, columnFilters, user) {
    return Workarea.query(
      angular.extend(
        {
          workspace_type: workarea,
          page: pagination.pageNumber,
          page_size: pagination.number,
          pager: pagination.pager,
          ordering: sortString,
          search: searchString,
          view_type: viewType,
          tag: $rootScope.selectedTag != null ? $rootScope.selectedTag.id : null,
          workspace_user: user.id,
        },
        columnFilters
      )
    ).$promise.then(function(resource) {
      let count = resource.$httpHeaders('Count');
      if (count == null) {
        count = resource.length;
      }
      return {
        count: count,
        data: resource,
      };
    });
  }

  //Fetches IP's for given workarea (ingest or access)
  function getDipPage(pagination, sortString, searchString, columnFilters) {
    return IP.query(
      angular.extend(
        {
          package_type: 4,
          page: pagination.pageNumber,
          page_size: pagination.number,
          pager: pagination.pager,
          ordering: sortString,
          search: searchString,
        },
        columnFilters
      )
    ).$promise.then(function(resource) {
      let count = resource.$httpHeaders('Count');
      if (count == null) {
        count = resource.length;
      }
      return {
        count: count,
        data: resource,
      };
    });
  }
  function getOrderPage(pagination, sortString, searchString) {
    return Order.query({
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function(resource) {
      let count = resource.$httpHeaders('Count');
      if (count == null) {
        count = resource.length;
      }
      return {
        count: count,
        data: resource,
      };
    });
  }

  function getReceptionIps(pagination, sortString, searchString, state, columnFilters) {
    return IPReception.query(
      angular.extend(
        {
          page: pagination.pageNumber,
          page_size: pagination.number,
          pager: pagination.pager,
          ordering: sortString,
          state: state,
          search: searchString,
        },
        columnFilters
      )
    ).$promise.then(function(resource) {
      let count = resource.$httpHeaders('Count');
      if (count == null) {
        count = resource.length;
      }
      return {
        count: count,
        data: resource,
      };
    });
  }

  //Add a new event
  function addEvent(ip, eventType, eventDetail, outcome) {
    return Event.save({
      eventType: eventType.eventType,
      eventOutcomeDetailNote: eventDetail,
      eventOutcome: outcome.value,
      information_package: ip.id,
    }).$promise.then(function(response) {
      return response;
    });
  }
  //Returns all events for one ip
  function getEvents(ip, pagination, sortString, columnFilters, searchString) {
    let promise;
    if ($state.includes('**.workarea.**') && ip.workarea && ip.workarea.length > 0) {
      promise = Workarea.events(
        angular.extend(
          {
            id: ip.id,
            page: pagination.pageNumber,
            page_size: pagination.number,
            pager: pagination.pager,
            search: searchString,
            ordering: sortString,
          },
          columnFilters
        )
      ).$promise;
    } else {
      promise = IP.events(
        angular.extend(
          {
            id: ip.id,
            page: pagination.pageNumber,
            page_size: pagination.number,
            pager: pagination.pager,
            search: searchString,
            ordering: sortString,
          },
          columnFilters
        )
      ).$promise;
    }

    return promise.then(function(resource) {
      let count = resource.$httpHeaders('Count');
      if (count == null) {
        count = resource.length;
      }
      return {
        count: count,
        data: resource,
      };
    });
  }
  //Gets event type for dropdown selection
  function getEventlogData() {
    return EventType.query().$promise.then(function(data) {
      return data;
    });
  }
  //Returns map structure for a profile
  function getStructure(profileId) {
    return Profile.get({
      id: profileId,
    }).$promise.then(function(data) {
      return data.structure;
    });
  }
  //returns all SA-profiles and current as an object
  //returns all SA-profiles and current as an object
  function getSaProfiles(ip) {
    let sas = [];
    const saProfile = {
      entity: 'PROFILE_SUBMISSION_AGREEMENT',
      profile: null,
      profiles: [],
    };
    const promise = SA.query({
      pager: 'none',
    }).$promise.then(function(resource) {
      sas = resource;
      saProfile.profiles = [];
      sas.forEach(function(sa) {
        saProfile.profiles.push(sa);
        if (ip.submission_agreement == sa.id) {
          saProfile.profile = sa;
          saProfile.locked = ip.submission_agreement_locked;
        }
      });
      return saProfile;
    });
    return promise;
  }

  //Execute prepare ip, which creates a new IP
  function prepareIp(label) {
    ip.post({
      label: label,
      package_type: 0,
    }).$promise.then(function(response) {
      return 'created';
    });
  }
  //Returns IP
  function getIp(id) {
    return IP.get({
      id: id,
    }).$promise.then(function(data) {
      return data;
    });
  }
  //Returns SA
  function getSa(id) {
    SA.get({
      id: id,
    }).$promise.then(function(data) {
      return data;
    });
  }
  //Get list of files in Ip
  function getFileList(ip) {
    return getIp(ip.id).then(function(result) {
      const array = [];
      const tempElement = {
        filename: result.object_path,
        created: result.create_date,
        size: result.object_size,
      };
      array.push(tempElement);
      return array;
    });
  }

  function prepareNewDip(label, objectIdentifierValue, orders) {
    return IP.prepareNewDip({
      label: label,
      object_identifier_value: objectIdentifierValue,
      orders: orders,
      package_type: 4,
    }).$promise.then(function(response) {
      return response;
    });
  }

  function createDip(ip, validators) {
    return IP.createDip(angular.extend({id: ip.id}, validators)).$promise.then(function(response) {
      return response;
    });
  }

  function prepareOrder(order) {
    return Order.save(order).$promise.then(function(response) {
      return response;
    });
  }
  function getWorkareaDir(workareaType, pathStr, pagination, user) {
    let sendData;
    if (pathStr == '') {
      sendData = {
        page: pagination.pageNumber,
        page_size: pagination.number,
        pager: pagination.pager,
        type: workareaType,
        user: user,
      };
    } else {
      sendData = {
        page: pagination.pageNumber,
        page_size: pagination.number,
        pager: pagination.pager,
        path: pathStr,
        type: workareaType,
        user: user,
      };
    }

    return $http.get(appConfig.djangoUrl + 'workarea-files/', {params: sendData}).then(function(response) {
      let count = response.headers('Count');
      if (count == null) {
        count = response.data.length;
      }
      if (response.headers()['content-disposition']) {
        return $q.reject(response);
      } else {
        return {
          numberOfPages: Math.ceil(count / pagination.number),
          data: response.data,
        };
      }
    });
  }

  function getDipDir(ip, pathStr, pagination) {
    let sendData;
    if (pathStr == '') {
      sendData = {
        id: ip.id,
        page: pagination.pageNumber,
        page_size: pagination.number,
        pager: pagination.pager,
      };
    } else {
      sendData = {
        id: ip.id,
        page: pagination.pageNumber,
        page_size: pagination.number,
        pager: pagination.pager,
        path: pathStr,
      };
    }
    return IP.files(sendData).$promise.then(function(data) {
      let count = data.$httpHeaders('Count');
      if (count == null) {
        count = data.length;
      }
      return {
        numberOfPages: Math.ceil(count / pagination.number),
        data: data,
      };
    });
  }

  function addFileToDip(ip, path, file, destination, type) {
    const src = path + file.name;
    const dst = destination + file.name;
    return WorkareaFiles.addToDip({
      dip: ip.id,
      src: src,
      dst: dst,
      type: type,
    }).$promise.then(function(response) {
      return response;
    });
  }

  function addNewFolder(ip, path, file) {
    return IP.addFile(
      {
        id: ip.id,
      },
      {
        path: path + file.name,
        type: file.type,
      }
    ).$promise.then(function(response) {
      return response;
    });
  }

  function addNewWorkareaFolder(workareaType, path, file, user) {
    return WorkareaFiles.addDirectory({
      type: workareaType,
      path: path + file.name,
      user: user,
    }).$promise.then(function(response) {
      return response;
    });
  }

  function deleteFile(ip, path, file) {
    return IP.removeFile({
      id: ip.id,
      path: path + file.name,
    }).$promise.then(function(response) {
      return response;
    });
  }

  function deleteWorkareaFile(workareaType, path, file, user) {
    return WorkareaFiles.removeFile({
      type: workareaType,
      path: path + file.name,
      user: user,
    })
      .$promise.then(function(response) {
        return response;
      })
      .catch(function(response) {
        return response;
      });
  }

  function getDir(ip, pathStr, pagination) {
    let sendData;
    if (pathStr == '') {
      sendData = {
        id: ip.id,
        page: pagination.pageNumber,
        page_size: pagination.number,
        pager: pagination.pager,
      };
    } else {
      sendData = {
        id: ip.id,
        page: pagination.pageNumber,
        page_size: pagination.number,
        pager: pagination.pager,
        path: pathStr,
      };
    }
    if ($state.is('home.ingest.reception') && (ip.state == 'At reception' || ip.state == 'Prepared')) {
      sendData.id = ip.object_identifier_value;
      return IPReception.files(sendData)
        .$promise.then(function(data) {
          let count = data.$httpHeaders('Count');
          if (count == null) {
            count = data.length;
          }
          return {
            numberOfPages: Math.ceil(count / pagination.number),
            data: data,
          };
        })
        .catch(function(response) {
          return response;
        });
    } else {
      return IP.files(sendData)
        .$promise.then(function(data) {
          let count = data.$httpHeaders('Count');
          if (count == null) {
            count = data.length;
          }
          return {
            numberOfPages: Math.ceil(count / pagination.number),
            data: data,
          };
        })
        .catch(function(response) {
          return response;
        });
    }
  }

  function getFile(ip, path, file) {
    return IP.files({
      id: ip.id,
      path: path + file.name,
    }).then(function(response) {
      return response;
    });
  }

  function getWorkareaFile(workareaType, path, file, user) {
    return WorkareaFiles.files({
      type: workareaType,
      path: path + file.name,
      user: user,
    }).then(function(response) {
      return response;
    });
  }

  function getPaginationParams(pagination, defaultNumber) {
    const start = pagination.start || 0; // This is NOT the page number, but the index of item in the list that you want to use to display the table.
    let number = pagination.number || defaultNumber; // Number of entries showed per page.
    const pageNumber = isNaN(start / number) ? 1 : start / number + 1;
    let pager = null;
    if (pagination.number === 'all') {
      pager = 'none';
      number = 1;
    }
    return {start, pageNumber, number, pager};
  }

  return {
    getListViewData: getListViewData,
    getReceptionIps: getReceptionIps,
    addEvent: addEvent,
    getEvents: getEvents,
    getEventlogData: getEventlogData,
    getSaProfiles: getSaProfiles,
    prepareIp: prepareIp,
    getIp: getIp,
    getSa: getSa,
    getFileList: getFileList,
    getStructure: getStructure,
    getWorkareaDir: getWorkareaDir,
    getDipDir: getDipDir,
    getWorkareaData: getWorkareaData,
    addFileToDip: addFileToDip,
    addNewFolder: addNewFolder,
    addNewWorkareaFolder: addNewWorkareaFolder,
    deleteFile: deleteFile,
    deleteWorkareaFile: deleteWorkareaFile,
    prepareNewDip: prepareNewDip,
    getDipPage: getDipPage,
    getOrderPage: getOrderPage,
    prepareOrder: prepareOrder,
    createDip: createDip,
    getDir: getDir,
    getfile: getFile,
    getPaginationParams: getPaginationParams,
    getWorkareaFile: getWorkareaFile,
    checkPages: checkPages,
  };
};

export default listViewService;
