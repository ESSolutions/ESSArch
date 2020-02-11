import React, {useContext} from 'react';
import Loadable from 'react-loadable';
import {Link, Redirect, Route, Switch} from 'react-router-dom';
import {SubNavbar, NavbarItem} from './Navbar';
import CollectContentPage from './CollectContentPage';
import ApprovalPage from './ApprovalPage';

const Loading = () => <div>Loading...</div>;

const HomePage = Loadable({
  loader: () => import('./HomePage'),
  loading: () => <Loading />,
});

const PrepareSIPPage = Loadable({
  loader: () => import('./PrepareSIPPage'),
  loading: () => <Loading />,
});

const ReceptionPage = Loadable({
  loader: () => import('./ReceptionPage'),
  loading: () => <Loading />,
});

const Routes = () => {
  return (
    <>
      <Route exact path="/" component={HomePage} />
      <Route path="/producer/">
        <SubNavbar>
          <NavbarItem to="prepare">Prepare IP</NavbarItem>
          &nbsp;
          <NavbarItem to="collect">Collect content</NavbarItem>
          &nbsp;
          <NavbarItem to="create-sip">Create SIP</NavbarItem>
          &nbsp;
          <NavbarItem to="submit-sip">Submit SIP</NavbarItem>
        </SubNavbar>
        <Switch>
          <Route path="/producer/prepare" component={PrepareSIPPage} />
          <Route path="/producer/collect" component={CollectContentPage} />
          <Route path="/" render={() => <Redirect to={'/producer/prepare'} />} />
        </Switch>
      </Route>
      <Route path="/ingest/">
        <SubNavbar>
          <NavbarItem to="reception">Reception</NavbarItem>
          &nbsp;
          <NavbarItem to="approval">Approval</NavbarItem>
        </SubNavbar>
        <Switch>
          <Route path="/ingest/reception" component={ReceptionPage} />
          <Route path="/ingest/approval" component={ApprovalPage} />
          <Route path="/" render={() => <Redirect to={'/ingest/reception'} />} />
        </Switch>
      </Route>
    </>
  );
};

export default Routes;
