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

const resource = (listViewService, Storage, $rootScope) => {
  //Get data for Events table
  function getEventPage(ip, pagination, params, selected, sort, columnFilters, search) {
    let sortString = sort.predicate;
    if (sort.predicate == 'eventDateTime') {
      if (sort.reverse) {
        sortString = sortString + ',-id';
      } else {
        sortString = sortString + ',id';
      }
    }
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return listViewService.getEvents(ip, pagination, sortString, columnFilters, search).then(function(value) {
      const eventCollection = value.data;
      eventCollection.forEach(function(event) {
        selected.forEach(function(item) {
          if (item.id == event.id) {
            event.class = 'selected';
          }
        });
      });
      return {
        data: eventCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }
  //Get data for IP table
  function getIpPage(pagination, params, sort, search, state, expandedAics, columnFilters, archived, workarea) {
    if ($rootScope.auth.ip_list_view_type) {
      var viewType = $rootScope.auth.ip_list_view_type;
    } else {
      var viewType = 'aic';
    }
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return listViewService
      .getListViewData(pagination, sortString, search, state, viewType, columnFilters, archived, workarea, params)
      .then(function(value) {
        const ipCollection = value.data;
        ipCollection.forEach(function(ip) {
          ip.collapsed = true;
          expandedAics.forEach(function(aic, index, array) {
            if (ip.object_identifier_value == aic) {
              ip.collapsed = false;
            }
          });
        });

        return {
          data: ipCollection,
          numberOfPages: Math.ceil(value.count / pagination.number),
        };
      });
  }

  function getWorkareaIps(workarea, pagination, params, sort, search, expandedAics, columnFilters, user) {
    if ($rootScope.auth.ip_list_view_type) {
      var viewType = $rootScope.auth.ip_list_view_type;
    } else {
      var viewType = 'aic';
    }
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return listViewService
      .getWorkareaData(
        workarea,
        pagination,
        $rootScope.navigationFilter,
        sortString,
        search,
        viewType,
        columnFilters,
        user
      )
      .then(function(value) {
        const ipCollection = value.data;
        ipCollection.forEach(function(ip) {
          ip.collapsed = true;
          expandedAics.forEach(function(aic, index, array) {
            if (ip.object_identifier_value == aic) {
              ip.collapsed = false;
            }
          });
        });
        return {
          data: ipCollection,
          numberOfPages: Math.ceil(value.count / pagination.number),
        };
      });
  }

  function getDips(pagination, params, sort, search, columnFilters) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return listViewService.getDipPage(pagination, sortString, search, columnFilters).then(function(value) {
      const ipCollection = value.data;
      ipCollection.forEach(function(ip) {
        ip.collapsed = false;
      });
      return {
        data: ipCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getOrders(pagination, params, sort, search) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return listViewService.getOrderPage(pagination, sortString, search).then(function(value) {
      const ipCollection = value.data;
      ipCollection.forEach(function(ip) {
        ip.collapsed = false;
      });
      return {
        data: ipCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getReceptionPage(pagination, params, sort, search, state, columnFilters) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return listViewService.getReceptionIps(pagination, sortString, search, state, columnFilters).then(function(value) {
      const ipCollection = value.data;
      return {
        data: ipCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  // Storage

  function getStorageMediums(pagination, params, sort, search) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getStorageMediums(pagination, $rootScope.navigationFilter, sortString, search).then(function(
      value
    ) {
      const storageMediumCollection = value.data;
      return {
        data: storageMediumCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }
  function getStorageObjectsForMedium(mediumId, pagination, params, medium, sort, search) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getStorageObjectsForMedium(mediumId, pagination, medium, sortString, search).then(function(value) {
      const storageObjectCollection = value.data;
      return {
        data: storageObjectCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }
  function getStorageObjects(pagination, params, medium, sort, search) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getStorageObjects(pagination, medium, sortString, search).then(function(value) {
      const storageObjectCollection = value.data;
      return {
        data: storageObjectCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getRobots(pagination, params, sort, search) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getRobots(pagination, sortString, search).then(function(value) {
      const robotCollection = value.data;
      return {
        data: robotCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getRobotQueue(pagination, params, sort, search) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getRobotQueue(pagination, sortString, search).then(function(value) {
      const robotQueueCollection = value.data;
      return {
        data: robotQueueCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getRobotQueueForRobot(pagination, params, sort, search, robot) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getRobotQueueForRobot(pagination, sortString, search, robot).then(function(value) {
      const robotQueueCollection = value.data;
      return {
        data: robotQueueCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getIoQueue(pagination, params, sort, search) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getIoQueue(pagination, sortString, search).then(function(value) {
      const ioQueueCollection = value.data;
      return {
        data: ioQueueCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getTapeDrives(pagination, params, sort, search, robot) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getTapeDrives(pagination, sortString, search, robot).then(function(value) {
      const tapeDrivecollection = value.data;
      return {
        data: tapeDrivecollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }

  function getTapeSlots(pagination, params, sort, search, robot) {
    let sortString = sort.predicate;
    if (sort.reverse) {
      sortString = '-' + sortString;
    }
    return Storage.getTapeSlots(pagination, sortString, search, robot).then(function(value) {
      const tapeSlotCollection = value.data;
      return {
        data: tapeSlotCollection,
        numberOfPages: Math.ceil(value.count / pagination.number),
      };
    });
  }
  return {
    getEventPage: getEventPage,
    getIpPage: getIpPage,
    getReceptionPage: getReceptionPage,
    getStorageMediums: getStorageMediums,
    getStorageObjectsForMedium: getStorageObjectsForMedium,
    getStorageObjects: getStorageObjects,
    getWorkareaIps: getWorkareaIps,
    getDips: getDips,
    getOrders: getOrders,
    getRobots: getRobots,
    getRobotQueue: getRobotQueue,
    getRobotQueueForRobot: getRobotQueueForRobot,
    getIoQueue: getIoQueue,
    getTapeDrives: getTapeDrives,
    getTapeSlots: getTapeSlots,
  };
};

export default resource;
