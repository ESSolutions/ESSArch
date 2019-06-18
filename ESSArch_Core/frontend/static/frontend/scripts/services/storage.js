const storage = (StorageMedium, StorageObject, Robot, RobotQueue, IOQueue, TapeSlot, TapeDrive) => {
  // Get storage mediums
  function getStorageMediums(pageNumber, pageSize, filters, sortString, searchString) {
    return StorageMedium.query({
      page: pageNumber,
      page_size: pageSize,
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
  function getStorageObjectsForMedium(mediumId, pageNumber, pageSize, medium, sortString, searchString) {
    return StorageMedium.objects({
      id: mediumId,
      page: pageNumber,
      page_size: pageSize,
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

  // Get storage objects given storage medium
  function getStorageObjects(pageNumber, pageSize, medium, sortString, searchString) {
    return StorageObject.query({
      page: pageNumber,
      page_size: pageSize,
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
  function getRobots(pageNumber, pageSize, sortString, searchString) {
    return Robot.query({
      page: pageNumber,
      page_size: pageSize,
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

  // Get tape slots given robot
  function getTapeSlots(pageNumber, pageSize, sortString, searchString, robot) {
    return TapeSlot.query({
      page: pageNumber,
      page_size: pageSize,
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

  // Get tape drives
  function getTapeDrives(pageNumber, pageSize, sortString, searchString, robot) {
    return TapeDrive.query({
      page: pageNumber,
      page_size: pageSize,
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

  function getRobotQueueForRobot(pageNumber, pageSize, sortString, searchString, robot) {
    return Robot.queue({
      id: robot.id,
      page: pageNumber,
      page_size: pageSize,
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

  function getRobotQueue(pageNumber, pageSize, sortString, searchString) {
    return RobotQueue.query({
      page: pageNumber,
      page_size: pageSize,
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

  function getIoQueue(pageNumber, pageSize, sortString, searchString) {
    return IOQueue.query({
      page: pageNumber,
      page_size: pageSize,
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

  // Inventory robot
  function inventoryRobot(robot) {
    return robot
      .$inventory()
      .then(function(response) {
        return response;
      })
      .catch(function(response) {
        return response.statusText;
      });
  }

  function mountTapeDrive(tapeDrive, medium) {
    return TapeDrive.mount({id: tapeDrive.id, storage_medium: medium.id}).$promise.then(function(response) {
      return response;
    });
  }

  function unmountTapeDrive(tapeDrive, force) {
    return TapeDrive.unmount({id: tapeDrive.id, force: force}).$promise.then(function(response) {
      return response;
    });
  }

  function mountTapeSlot(tapeSlot, medium) {
    return StorageMedium.mount({id: tapeSlot.storage_medium.id}).$promise.then(function(response) {
      return response;
    });
  }

  function unmountTapeSlot(tapeSlot, force) {
    return StorageMedium.unmount({id: tapeSlot.storage_medium.id, force: force}).$promise.then(function(response) {
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
