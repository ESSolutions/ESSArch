const selectedIpUpdater = () => {
  function updateSingleIp(oldIP, newIP) {
    angular.copy(newIP, oldIP);
  }
  const service = {
    /**
     * Update selected IP(s) with data from new IP list.
     * @param {Array} newIps new IPs
     * @param {Array} selectedIps selected IPs (multiple select)
     * @param {Object} selectedIp selected IP (single select)
     */

    update: function(newIps, selectedIps, selectedIp) {
      if (selectedIps.length > 0) {
        for (let i = 0; i < selectedIps.length; i++) {
          for (let j = 0; j < newIps.length; j++) {
            if (
              !angular.equals(selectedIps[i], newIps[j]) &&
              (selectedIps[i].id === newIps[j].id ||
                selectedIps[i].object_identifier_value === newIps[j].object_identifier_value)
            ) {
              updateSingleIp(selectedIps[i], newIps[j]);
            }
          }
        }
      } else if (selectedIp !== null) {
        newIps.forEach(function(ip) {
          if (!angular.equals(ip, selectedIp) && ip.id === selectedIp.id) {
            updateSingleIp(selectedIp, ip);
          }
        });
      }
    },
  };
  return service;
};

export default selectedIpUpdater;
