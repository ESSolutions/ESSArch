const AgentName = ($filter) => {
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
     * Parse agent names setting full_name field to a combination of part and main-names
     * @param {Object} agent
     */
    parseAgentNames: function (agent, options) {
      agent.names.forEach(function (x) {
        x.full_name = getFullName(x);
      });
    },

    /**
     * Parse agent name setting full_name field to a combination of part and main-names and including start/end dates
     * @param {Object} agent
     */
    parseAgentName: function (agent, options) {
      let agent_name_obj = null;
      agent_name_obj = angular.copy(agent.name);
      agent.full_name = getFullName(agent_name_obj);
      agent_name_obj.full_name = agent.full_name;
      if (angular.isUndefined(options) || (!angular.isUndefined(options) && options.includeDates !== false)) {
        agent.full_name += getAgentNameDates(agent);
        agent_name_obj.full_name = agent.full_name;
      }
      return agent_name_obj;
    },
  };
};

export default AgentName;
