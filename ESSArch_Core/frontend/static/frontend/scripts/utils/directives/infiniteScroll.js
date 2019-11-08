const infiniteScroll = () => {
  return {
    restrict: 'A',
    link: function(scope, element, attrs) {
      const raw = element[0];
      console.log('loading onScroll directive');

      element.bind('scroll', function() {
        if (raw.scrollTop + raw.offsetHeight >= raw.scrollHeight) {
          scope.$apply(attrs.onScroll);
        }
      });
    },
  };
};

export default infiniteScroll;
