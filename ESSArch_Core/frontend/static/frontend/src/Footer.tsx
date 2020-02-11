import React from 'react';

import './Footer.scss';

const Footer = () => {
  const year = new Date().getFullYear();
  return (
    <footer className="page-footer">
      <h4>ESSArch</h4>
      <div className="footer-info">
        <div className="company-info-wrapper">
          <div className="text-center d-flex">
            <a className="px-base" ui-sref="home.support" title="ES Solutions support">
              Support
            </a>
            <div className="vertical-line-separator"></div>
            <a className="px-base" href="http://www.essolutions.se" title="essolutions.se" target="_blank">
              Contact
            </a>
          </div>
        </div>
      </div>
      <div className="copyright">
        &copy; {year}&nbsp;
        <a tabIndex={-1} href="http://essolutions.se">
          ES Solutions
        </a>
      </div>
    </footer>
  );
};

export default Footer;
