const EditMode = () => {
  let unsaved = false;
  // Register event listener that is triggered before page is closed or refreshed
  // Opens dialog with warning that data may be lost
  window.addEventListener('beforeunload', function(e) {
    if (unsaved) {
      // Cancel the event
      e.preventDefault();
      // Chrome requires returnValue to be set
      e.returnValue = '';
    }
  });

  const service = {
    // Disables edit mode, refresh and closing the tab can be done without dialog
    disable: function() {
      unsaved = false;
    },
    // Enables edit mode, refresh and closing the tab will open a dialog that must be confirmed to close/refresh
    enable: function() {
      unsaved = true;
    },
  };
  return service;
};

export default EditMode;
