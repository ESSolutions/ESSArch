import React, {FunctionComponent, useState} from 'react';
import InformationPackageTable from './InformationPackageTable';

const PrepareSIPPage: FunctionComponent = () => {
  let [state, setState] = useState<string>('');

  return (
    <div className="nav-dynamic-wrapper">
      <div className="info-wrapper">
        <h2>Prepare SIP</h2>
        <div className="content-wrapper">
          <InformationPackageTable />
        </div>
      </div>
    </div>
  );
};

export default PrepareSIPPage;
