import React, {FunctionComponent} from 'react';
import {Link, LinkProps} from 'react-router-dom';

import './Navbar.scss';

export const NavbarItem: FunctionComponent<LinkProps> = props => <Link className="nav-item" {...props}></Link>;

const Navbar: FunctionComponent = () => (
  <div className="header">
    <Link to="/">
      <h3>ESSArch</h3>
    </Link>
    <div className="menu nav">
      <NavbarItem to="/producer">Producer</NavbarItem>
      &nbsp;
      <NavbarItem to="/ingest">Ingest</NavbarItem>
      &nbsp;
    </div>
  </div>
);

export const SubNavbar: FunctionComponent = props => <div className="sub-menu">{props.children}</div>;

export default Navbar;
