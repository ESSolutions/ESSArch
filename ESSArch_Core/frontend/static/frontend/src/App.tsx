import React from 'react';
import {Helmet} from 'react-helmet';
import {Router} from 'react-router-dom';
import {createBrowserHistory} from 'history';

import Navbar from './Navbar';
import Footer from './Footer';
import Routes from './Routes';

import './App.scss';

const App = () => (
  <Router history={createBrowserHistory()}>
    <div>
      <div className="body-wrapper">
        <Helmet>
          <title>ESSArch</title>
        </Helmet>
        <Navbar />
        <Routes />
      </div>
      <Footer />
    </div>
  </Router>
);

export default App;
