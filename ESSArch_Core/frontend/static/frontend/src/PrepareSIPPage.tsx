import React, {FunctionComponent, useState} from 'react';

const PrepareSIPPage: FunctionComponent = () => {
  let [state, setState] = useState<string>('');

  return (
    <div className="nav-dynamic-wrapper">
      <div className="info-wrapper">
        <h2>Prepare SIP</h2>
        <input onChange={e => setState(e.target.value)} />
        <div>Data: {state}</div>
      </div>
    </div>
  );
};

export default PrepareSIPPage;
