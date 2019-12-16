export default ($timeout, $document) => {
  return {
    link: function(scope, element, attrs, controller) {
      // Attempt to integrate with ngRepeat
      var match = attrs.ngRepeat.match(/^\s*([\s\S]+?)\s+in\s+([\s\S]+?)(?:\s+track\s+by\s+([\s\S]+?))?\s*$/);
      var tabs;
      scope.$watch(match[2], function(newTabs) {
        tabs = newTabs;
      });

      var index = scope.$index;
      scope.$watch('$index', function(newIndex) {
        index = newIndex;
      });

      attrs.$set('draggable', true);

      // Wrapped in $apply so Angular reacts to changes
      var wrappedListeners = {
        // On item being dragged
        dragstart: function(e) {
          e.originalEvent.dataTransfer.effectAllowed = 'move';
          e.originalEvent.dataTransfer.dropEffect = 'move';
          e.originalEvent.dataTransfer.setData('application/json', index);
          element.addClass('dragging');
        },
        dragend: function(e) {
          //e.stopPropagation();
          element.removeClass('dragging');
        },

        // On item being dragged over / dropped onto
        dragenter: function(e) {},
        dragleave: function(e) {
          element.removeClass('hover');
        },
        drop: function(e) {
          e.preventDefault();
          e.stopPropagation();
          var sourceIndex = e.originalEvent.dataTransfer.getData('application/json');
          move(sourceIndex, index);
          element.removeClass('hover');
        },
      };

      // For performance purposes, do not
      // call $apply for these
      var unwrappedListeners = {
        dragover: function(e) {
          e.preventDefault();
          element.addClass('hover');
        },
        /* Use .hover instead of :hover. :hover doesn't play well with
           moving DOM from under mouse when hovered */
        mouseenter: function() {
          element.addClass('hover');
        },
        mouseleave: function() {
          element.removeClass('hover');
        },
      };

      angular.forEach(wrappedListeners, function(listener, event) {
        element.on(event, wrap(listener));
      });

      angular.forEach(unwrappedListeners, function(listener, event) {
        element.on(event, listener);
      });

      function wrap(fn) {
        return function(e) {
          scope.$apply(function() {
            fn(e);
          });
        };
      }

      function move(fromIndex, toIndex) {
        tabs.splice(toIndex, 0, tabs.splice(fromIndex, 1)[0]);
      }
    },
  };
};
