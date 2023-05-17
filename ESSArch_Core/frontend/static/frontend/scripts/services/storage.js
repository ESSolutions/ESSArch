const storage = (StorageMedium, StorageObject, Robot, RobotQueue, IOQueue, TapeSlot, TapeDrive) => {
  // Get storage mediums
  function getStorageMediums(pagination, filters, sortString, searchString) {
    return StorageMedium.query({
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function successCallback(resource) {
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

  // Get storage objects given storage medium
  function getStorageObjectsForMedium(mediumId, pagination, medium, sortString, searchString) {
    return StorageMedium.objects({
      id: mediumId,
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function (resource) {
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

  // Get storage objects given storage medium
  function getStorageObjects(pagination, medium, sortString, searchString) {
    return StorageObject.query({
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function successCallback(resource) {
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

  // Get robots
  function getRobots(pagination, sortString, searchString) {
    return Robot.query({
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function (resource) {
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

  // Get tape slots given robot
  function getTapeSlots(pagination, sortString, searchString, robot) {
    return TapeSlot.query({
      robot_id: robot.id,
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function (resource) {
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

  // Get tape drives given robot
  function getTapeDrives(pagination, sortString, searchString, robot) {
    return TapeDrive.query({
      robot_id: robot.id,
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function (resource) {
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

  function getRobotQueueForRobot(pagination, sortString, searchString, robot) {
    return Robot.queue({
      id: robot.id,
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function (resource) {
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

  function getRobotQueue(pagination, sortString, searchString) {
    return RobotQueue.query({
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function (resource) {
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

  function getIoQueue(pagination, sortString, searchString) {
    return IOQueue.query({
      page: pagination.pageNumber,
      page_size: pagination.number,
      pager: pagination.pager,
      ordering: sortString,
      search: searchString,
    }).$promise.then(function (resource) {
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

  // Inventory robot
  function inventoryRobot(robot) {
    return robot
      .$inventory()
      .then(function (response) {
        return response;
      })
      .catch(function (response) {
        return response.statusText;
      });
  }

  function mountTapeDrive(robot, tapeDrive, medium_id) {
    return TapeDrive.mount({robot_id: robot.id, id: tapeDrive.id, medium_id: medium_id}).$promise.then(function (
      response
    ) {
      return response;
    });
  }

  function unmountTapeDrive(robot, tapeDrive, force) {
    return TapeDrive.unmount({robot_id: robot.id, id: tapeDrive.id, force: force}).$promise.then(function (response) {
      return response;
    });
  }

  function mountTapeSlot(tapeSlot, medium) {
    return StorageMedium.mount({id: tapeSlot.storage_medium.id}).$promise.then(function (response) {
      return response;
    });
  }

  function unmountTapeSlot(tapeSlot, force) {
    return StorageMedium.unmount({id: tapeSlot.storage_medium.id, force: force}).$promise.then(function (response) {
      return response;
    });
  }
  return {
    getStorageMediums: getStorageMediums,
    getStorageObjectsForMedium: getStorageObjectsForMedium,
    getStorageObjects: getStorageObjects,
    getTapeSlots: getTapeSlots,
    getTapeDrives: getTapeDrives,
    getRobots: getRobots,
    inventoryRobot: inventoryRobot,
    getRobotQueueForRobot: getRobotQueueForRobot,
    getRobotQueue: getRobotQueue,
    getIoQueue: getIoQueue,
    mountTapeDrive: mountTapeDrive,
    unmountTapeDrive: unmountTapeDrive,
    mountTapeSlot: mountTapeSlot,
    unmountTapeSlot: unmountTapeSlot,
  };
};

export default storage;
