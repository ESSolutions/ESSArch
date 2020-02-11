import React, {FunctionComponent} from 'react';

const HomePage: FunctionComponent = () => (
  <div className="nav-dynamic-wrapper">
    <div className="info-wrapper">
      <h2>ESSArch - A Digital Archival Solution</h2>
      <p>
        ESSArch is an open source archival solution compliant to the OAIS ISO-standard. ESSArch consist of software
        components that provide functionality for Pre-Ingest, Ingest, Preservation, Access, Data Management,
        Administration and Management. ESSArch has been developed together with the National Archives of Sweden and
        Norway. Every software component of ESSArch can be used individually and also be easily integrated together to
        provide overall functionality for producers, archivists and consumers.
      </p>
    </div>
  </div>
);

export default HomePage;
