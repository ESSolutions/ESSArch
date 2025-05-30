export default (IP, Step, $filter, linkHeaderParser, Workarea, $state) => {
  //Get data for status view. child steps and tasks
  function getTreeData(ip, expandedNodes, paginationParams, sortString, searchString, columnFilters) {
    let promise;
    let filter_name;
    filter_name = null;
    if ($state.includes('**.storageMigration.**')) {
      filter_name = 'Migrate Information Package';
    }
    console.log('columnFilters after - :', filter_name);
    if ($state.includes('**.workarea.**') && ip.workarea && ip.workarea.length > 0) {
      promise = Workarea.workflow(
        angular.extend(
          {
            id: ip.id,
            hidden: false,
            page: paginationParams.pageNumber,
            page_size: paginationParams.number,
            pager: paginationParams.pager,
            ordering: sortString,
            search: searchString,
          },
          columnFilters
        )
      ).$promise;
    } else if ($state.includes('**.storageMigration.**') && angular.isUndefined(ip)) {
      promise = Step.query(
        angular.extend(
          {
            name: 'Migrate Storage Medium',
            childs: true,
            hidden: false,
            page: paginationParams.pageNumber,
            page_size: paginationParams.number,
            pager: paginationParams.pager,
            ordering: sortString,
            search: searchString,
          },
          columnFilters
        )
      ).$promise;
    } else {
      promise = IP.workflow(
        angular.extend(
          {
            id: ip.id,
            name: filter_name,
            hidden: false,
            page: paginationParams.pageNumber,
            page_size: paginationParams.number,
            pager: paginationParams.pager,
            ordering: sortString,
            search: searchString,
          },
          columnFilters
        )
      ).$promise;
    }
    return promise.then(function (workflow) {
      workflow.forEach(function (flow_node) {
        flow_node.time_started = $filter('date')(flow_node.time_started, 'yyyy-MM-dd HH:mm:ss');
        flow_node.children = flow_node.flow_type == 'step' ? [{val: -1}] : [];
        flow_node.childrenFetched = false;
      });
      return expandAndGetChildren(workflow, expandedNodes);
    });
  }

  function getTreeActionData(ip, expandedNodes) {
    let promise;
    if ($state.includes('**.workarea.**') && ip.workarea && ip.workarea.length > 0) {
      promise = Workarea.workflow({
        id: ip.id,
        hidden: false,
      }).$promise;
    } else {
      promise = IP.workflow({
        id: ip.id,
        hidden: false,
      }).$promise;
    }
    return promise.then(function (workflow) {
      workflow.forEach(function (flow_node) {
        flow_node.time_started = $filter('date')(flow_node.time_started, 'yyyy-MM-dd HH:mm:ss');
        flow_node.children = flow_node.flow_type == 'step' ? [{val: -1}] : [];
        flow_node.childrenFetched = false;
      });
      return expandAndGetActionChildren(workflow, expandedNodes);
    });
  }

  // Takes an array of steps, expands the ones that should be expanded and
  // populates children recursively.

  // Takes an array of steps, expands the ones that should be expanded and
  // populates children recursively.
  function expandAndGetChildren(steps, expandedNodes) {
    const expandedObject = expand(steps, expandedNodes);
    const expanded = expandedObject.expandedSteps;
    steps = expandedObject.steps;
    expanded.forEach(function (item) {
      steps[item.stepIndex] = getChildrenForStep(steps[item.stepIndex], item.number).then(function (stepChildren) {
        const temp = stepChildren;
        temp.children = expandAndGetChildren(temp.children, expandedNodes);
        return temp;
      });
    });
    return steps;
  }

  function expandAndGetActionChildren(steps, expandedNodes) {
    var search = 'action tool';
    var stepsToKeep = [];
    const expandedObject = expand(steps, expandedNodes);
    const expanded = expandedObject.expandedSteps;
    steps = expandedObject.steps;
    expanded.forEach(function (item) {
      steps[item.stepIndex] = getChildrenForStep(steps[item.stepIndex], item.number).then(function (stepChildren) {
        const temp = stepChildren;
        temp.children = expandAndGetChildren(temp.children, expandedNodes);
        return temp;
      });
    });
    for (var i = 0; i < steps.length; i++) {
      if (steps[i].label) {
        if (steps[i].label.toUpperCase() === search.toUpperCase()) {
          stepsToKeep.push(steps[i]);
        }
      }
    }

    steps = stepsToKeep;

    return steps;
  }

  // Gets children for a step and processes each child step/task.
  // Returns the updated step
  function getChildrenForStep(step, page_number) {
    const page_size = 10;
    if (angular.isUndefined(page_number) || !page_number) {
      step.page_number = 1;
    } else {
      step.page_number = page_number;
    }
    return Step.children({
      id: step.id,
      page: step.page_number,
      page_size: page_size,
      hidden: false,
    }).$promise.then(function (resource) {
      let count = resource.$httpHeaders('Count');
      if (count == null) {
        count = resource.length;
      }
      step.pages = Math.ceil(count / page_size);
      const linkHeader = resource.$httpHeaders('Link');
      if (linkHeader !== null) {
        const link = linkHeaderParser.parse(linkHeader);
        link.first ? (step.first = link.first) : (step.first = null);
        link.next ? (step.next = link.next) : (step.next = null);
        link.prev ? (step.prev = link.prev) : (step.prev = null);
        link.last ? (step.last = link.last) : (step.last = null);
      } else {
        step.first = null;
        step.next = null;
        step.prev = null;
        step.last = null;
      }

      step.page_number = page_number || 1;
      if (resource.length > 0) {
        // Delete placeholder
        step.children.pop();
      }
      const tempChildArray = [];
      resource.forEach(function (child) {
        if (child.flow_type == 'step') {
          child.isCollapsed = false;
          child.tasksCollapsed = true;
          child.children = [{val: -1}];
          child.childrenFetched = false;
        }
        tempChildArray.push(child);
      });
      step.children = tempChildArray;
      step.children = step.children.map(function (c) {
        c.time_started = $filter('date')(c.time_started, 'yyyy-MM-dd HH:mm:ss');
        return c;
      });
      if (step.children.length <= 0) {
        step.children = [{name: 'Empty', empty: true}];
      }
      return step;
    });
  }

  // Set expanded to true for each item in steps that exists in expandedNodes
  // Returns updated steps and an array containing the expanded nodes
  function expand(steps, expandedNodes) {
    const expanded = [];
    expandedNodes.forEach(function (node) {
      steps.forEach(function (step, idx) {
        if (step.id == node.id) {
          step.expanded = true;
          expanded.push({stepIndex: idx, number: node.page_number});
        }
      });
    });
    return {steps: steps, expandedSteps: expanded};
  }
  return {
    getTreeData: getTreeData,
    getTreeActionData: getTreeActionData,
    getChildrenForStep: getChildrenForStep,
  };
};
