const ip = ($resource, appConfig, Event, Step, Task) => {
  return $resource(
    appConfig.djangoUrl + 'information-packages/:id/:action/',
    {},
    {
      query: {
        method: 'GET',
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      delete: {
        method: 'DELETE',
        params: {id: '@id'},
      },
      events: {
        method: 'GET',
        params: {action: 'events', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.forEach(function(res, idx, array) {
              array[idx] = new Event(res);
            });
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      prepare: {
        method: 'POST',
      },
      create: {
        method: 'POST',
        params: {action: 'create', id: '@id'},
      },
      submit: {
        method: 'POST',
        params: {action: 'submit', id: '@id'},
      },
      setUploaded: {
        method: 'POST',
        params: {action: 'set-uploaded', id: '@id'},
      },
      mergeChunks: {
        method: 'POST',
        params: {action: 'merge-uploaded-chunks', id: '@id'},
      },
      prepareForUpload: {
        method: 'POST',
        params: {action: 'prepare', id: '@id'},
      },
      prepareDip: {
        method: 'POST',
        params: {action: 'prepare-dip'},
      },
      createDip: {
        method: 'POST',
        params: {action: 'create-dip', id: '@id'},
      },
      files: {
        method: 'GET',
        params: {action: 'files', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      workflow: {
        method: 'GET',
        params: {action: 'workflow', id: '@id'},
        isArray: true,
        interceptor: {
          response: function(response) {
            response.resource = response.resource.map(function(res) {
              return res.flow_type === 'task' ? new Task(res) : new Step(res);
            });
            response.resource.$httpHeaders = response.headers;
            return response.resource;
          },
        },
      },
      checkProfile: {
        method: 'PUT',
        params: {method: 'check-profile', id: '@id'},
      },
      unlockProfile: {
        method: 'POST',
        params: {action: 'unlock-profile', id: '@id'},
      },
      changeProfile: {
        method: 'PUT',
        params: {action: 'change-profile', id: '@id'},
      },
      addFile: {
        method: 'POST',
        params: {action: 'files', id: '@id'},
      },
      removeFile: {
        method: 'DELETE',
        hasBody: true,
        params: {action: 'files', id: '@id'},
        headers: {'Content-type': 'application/json;charset=utf-8'},
      },
      preserve: {
        method: 'POST',
        isArray: false,
        params: {action: 'preserve', id: '@id'},
      },
      access: {
        method: 'POST',
        params: {action: 'access', id: '@id'},
        isArray: false,
      },
      changeSa: {
        method: 'PATCH',
        params: {id: '@id'},
      },
      moveToApproval: {
        method: 'POST',
        params: {action: 'receive', id: '@id'},
      },
      appraisalRules: {
        method: 'GET',
        params: {action: 'appraisal-rules', id: '@id'},
        isArray: true,
      },
      conversionRules: {
        method: 'GET',
        params: {action: 'conversion-rules', id: '@id'},
        isArray: true,
      },
      storageObjects: {
        method: 'GET',
        params: {action: 'storage-objects', id: '@id'},
        isArray: true,
      },
      update: {
        method: 'PATCH',
        params: {id: '@id'},
      },
    }
  );
};

export default ip;
