import React from 'react';
import PropTypes from 'prop-types';

const ReactComponent = ({value, addOne}) => (
  <div className="react-component">
    <span>react value: {value} </span>
    <button onClick={addOne}>Add one</button>
  </div>
);

ReactComponent.propTypes = {
  value: PropTypes.number,
  addOne: PropTypes.func,
};

export default ReactComponent;
