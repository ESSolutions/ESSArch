const AgentName = $filter => {
  /**
   * Returns part and main name combined
   * @param {Object} agent
   */
  function getFullName(name) {
    return (name.part !== null && name.part !== '' ? name.part + ', ' : '') + name.main;
  }

  /**
   * Builds date section for agent name
   * @param {Object} agent
   */
  function getAgentNameDates(agent) {
    return !(agent.start_date === null && agent.end_date === null)
      ? ' (' +
          (agent.start_date !== null ? $filter('date')(agent.start_date, 'yyyy') : '') +
          ' - ' +
          (agent.end_date !== null ? $filter('date')(agent.end_date, 'yyyy') : '') +
          ')'
      : '';
  }
  return {
    /**
     * Get authorized name for agent including start/end dates
     * @param {Object} agent
     */
    getAuthorizedName: function(agent, options) {
      agent = angular.copy(agent);
      agent.names.sort(function(a, b) {
        return new Date(b.start_date) - new Date(a.start_date);
      });
      var name = null;
      agent.names.forEach(function(x) {
        if (x.type.id === 1 && x.start_date !== null && x.end_date === null && name === null) {
          name = angular.copy(x);
          name.full_name = getFullName(x);
          if (angular.isUndefined(options) || (!angular.isUndefined(options) && options.includeDates !== false)) {
            if (options && options.printDates) {
            }
            name.full_name += getAgentNameDates(agent);
          }
        }
      });
      if (name === null) {
        agent.names.forEach(function(x) {
          if (x.type.id === 1 && name === null) {
            name = angular.copy(x);
            name.full_name = getFullName(x);
            if (angular.isUndefined(options) || (!angular.isUndefined(options) && options.includeDates !== false)) {
              if (options && options.printDates) {
              }
              name.full_name += getAgentNameDates(agent);
            }
          }
        });
      }
      return name;
    },

    /**
     * Parse agent names setting full_name field to a combination of part and main-names
     * @param {Object} agent
     */
    parseAgentNames: function(agent, options) {
      agent.names.forEach(function(x) {
        x.full_name = getFullName(x);
        if (x.type.id === 1) {
          agent.full_name = getFullName(x);
          if (angular.isUndefined(options) || (!angular.isUndefined(options) && options.includeDates !== false)) {
            agent.full_name += getAgentNameDates(agent);
          }
        }
      });
    },
  };
};

export default AgentName;
