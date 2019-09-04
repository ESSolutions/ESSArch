const PropsFilter = () => {
  return function(items, props) {
    let out = [];

    if (angular.isArray(items)) {
      items.forEach(function(item) {
        let itemMatches = false;

        const keys = Object.keys(props);
        for (let i = 0; i < keys.length; i++) {
          const prop = keys[i];
          const text = props[prop].toLowerCase();
          if (
            item[prop]
              .toString()
              .toLowerCase()
              .indexOf(text) !== -1
          ) {
            itemMatches = true;
            break;
          }
        }

        if (itemMatches) {
          out.push(item);
        }
      });
    } else {
      // Let the output be the input untouched
      out = items;
    }

    return out;
  };
};

export default PropsFilter;
