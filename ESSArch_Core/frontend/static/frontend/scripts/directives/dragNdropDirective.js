/*
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
*/

export default myService => {
  return {
    restrict: 'EA',
    link: function(scope, elt, attrs) {
      elt.draggable({
        cursor: 'move',
        appendTo: 'body',
        disabled: !scope.$parentNode,
        drag: function(event, ui) {
          const destination = ui.helper.data('destination');
          if (destination) {
            const cursorPos = event.pageY;
            const destPos = destination.offset().top;
            const offset = cursorPos - destPos;
            const h = destination.height();

            let position;
            if (offset <= h / 3) {
              position = 'up';
            } else if (offset >= (2 * h) / 3) {
              position = 'down';
            } else {
              position = 'middle';
            }
            ui.helper.data('position', position);
            destination.removeClass('hover-up hover-middle hover-down');
            destination.addClass('hover-' + position);
          }
        },
        helper: function(event) {
          const helper = $('<div class="helper">' + scope.node.name + '</div>');
          // fill some data to be catched up by droppable() of receiver directives
          helper.data('node', scope.node);
          helper.data('parentNode', scope.$parentNode);
          return helper;
        },
      });
      elt.droppable({
        tolerance: 'pointer',
        over: function(event, ui) {
          ui.helper.data('destination', elt);
          elt.addClass('hover');
        },
        out: function(event, ui) {
          ui.helper.data('destination', null);
          elt.removeClass('hover hover-up hover-middle hover-down');
        },
        drop: function(event, ui) {
          const toNode = scope.node;
          const toParent = scope.$parentNode ? scope.$parentNode.children : null;
          const fromNode = ui.helper.data('node');
          const fromParentNode = ui.helper.data('parentNode');
          const position = ui.helper.data('position');

          scope.$apply(function() {
            let idx;
            if (!myService.hasChild(toNode, fromNode)) {
              if (fromParentNode) {
                idx = fromParentNode.children.indexOf(fromNode);
                if (idx != -1) {
                  fromParentNode.children.splice(idx, 1);
                }
              }
              if (position === 'middle') {
                if (toNode.type === 'file') {
                  if (toParent) {
                    idx = toParent.indexOf(toNode);
                    toParent.splice(idx + 1, 0, fromNode);
                  }
                } else {
                  toNode.children.push(fromNode);
                }
              } else if (position === 'up') {
                if (toParent) {
                  idx = toParent.indexOf(toNode);
                  toParent.splice(idx, 0, fromNode);
                }
              } else if (position === 'down') {
                if (toParent) {
                  idx = toParent.indexOf(toNode);
                  toParent.splice(idx + 1, 0, fromNode);
                }
              }
            }
          });
          elt.removeClass('hover hover-up hover-middle hover-down');
        },
      });

      var dereg = scope.$on('$destroy', function() {
        try {
          elet.draggable('destroy');
        } catch (e) {
          // may fail
        }
        dereg();
        dereg = null;
      });
    },
  };
};
