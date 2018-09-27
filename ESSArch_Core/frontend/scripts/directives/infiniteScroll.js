angular.module('essarch.directives').directive('onScroll', function() {
    return {
        restrict: 'A',
        link: function (scope, element, attrs) {
            var raw = element[0];
            console.log('loading onScroll directive');

            element.bind('scroll', function () {
                if (raw.scrollTop + raw.offsetHeight >= raw.scrollHeight) {
                    scope.$apply(attrs.onScroll);
                }
            });
        }
    };
});
