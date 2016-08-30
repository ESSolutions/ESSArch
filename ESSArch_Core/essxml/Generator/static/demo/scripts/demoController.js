// var json = require('./data.json');

(function() {


    'use strict';

    angular
        .module('formlyApp')
        .controller('MainController', MainController);


    function MainController($scope, $http) {

        //TODO not hardcoded 'test' in future
        // $http.get('/template/form/test').then(function(res) {
        //     // console.log()
        //     vm.fields = res.data;
        // });
        //
        // $http.get('/template/data/test').then(function(res) {
        //     // console.log()
        //     vm.model = res.data;
        // });

        var vm = this;
        // vm.title = 'title'; // placeholder only
        // vm.countAll = {};
        // vm.anyAttribute = false;
        // vm.anyElement = false;
        // vm.possibleChildren = [];
        // vm.existingChildren = [];

        vm.submitForm = function() {
            var data = vm.model;
            // data['uuid'] = vm.uuid;
            // data['schemaName'] = vm.schemaName;
            // console.log(vm.model);
            $http({
                method: 'POST',
                url: '/demo/',
                data: data
            }).then(function(res) {
                console.log(res);
            });
            //TODO give feedback
            // $scope.showSelected(vm.selectedNode, false);
        };

        vm.model = {
          "agentname1": "ESS",
          "agentname2": "HR Employed",
          "agentname3": "5.0.34",
          "agentname4": "Noark 5",
          "agentname5": "Government X, Dep Y",
          "agentname6": "Government X, Archival Dep",
          "agentname7": "Gene Simmons",
          "agentname8": "Government X system type",
          "agentname9": "Government X, Service Dep",
          "agentname10": "Lita Ford",
          "agentname11": "Government X, Legal Dep",
          "agentname12": "National Archives of X",
          "SUBMISSIONAGREEMENT": "RA 13-2011/5329; 2012-04-12",
          "STARTDATE": "2012-01-01",
          "ENDDATE": "2012-12-30",
          "DOCUMENTID": "info.xml",
          "MetsLABEL": "test1",
          "MetsType": "SIP",
          "MetsId": "8e202e62-2f36-11e3-aad3-028037ec0200",
          "MetsOBJID": "83f4ba00-2f36-11e3-9e9e-028037ec0200",
          "MetsHdrCREATEDATE": "2013-10-07T11:55:11+02:00",
          "MetsHdrRECORDSTATUS": "NEW"
        };

        vm.fields = [
          //list all fields
          {
            "type": "input",
            "key": "agentname1",
            "templateOptions": {
              "type": "text",
              "label": "Archivist Organization"
            }
          },
          {
            "type": "input",
            "key": "agentname2",
            "templateOptions": {
              "type": "text",
              "label": "Archivist Software"
            }
          },
          {
            "type": "input",
            "key": "agentname3",
            "templateOptions": {
              "type": "text",
              "label": "Archivist Software"
            }
          },
          {
            "type": "input",
            "key": "agentname4",
            "templateOptions": {
              "type": "text",
              "label": "Archivist Software"
            }
          },
          {
            "type": "input",
            "key": "agentname5",
            "templateOptions": {
              "type": "text",
              "label": "Creator Organization"
            }
          },
          {
            "type": "input",
            "key": "agentname6",
            "templateOptions": {
              "type": "text",
              "label": "Producer Organization"
            }
          },
          {
            "type": "input",
            "key": "agentname7",
            "templateOptions": {
              "type": "text",
              "label": "Producer Individual"
            }
          },
          {
            "type": "input",
            "key": "agentname8",
            "templateOptions": {
              "type": "text",
              "label": "Producer Software"
            }
          },
          {
            "type": "input",
            "key": "agentname9",
            "templateOptions": {
              "type": "text",
              "label": "Submitter Organization"
            }
          },
          {
            "type": "input",
            "key": "agentname10",
            "templateOptions": {
              "type": "text",
              "label": "Submitter Individual"
            }
          },
          {
            "type": "input",
            "key": "agentname11",
            "templateOptions": {
              "type": "text",
              "label": "IPOwner Individual"
            }
          },
          {
            "type": "input",
            "key": "agentname12",
            "templateOptions": {
              "type": "text",
              "label": "Preservation Organization"
            }
          },
          {
            "type": "input",
            "key": "SUBMISSIONAGREEMENT",
            "templateOptions": {
              "type": "text",
              "label": "Submission Agreement"
            }
          },
          {
            "type": "input",
            "key": "STARTDATE",
            "templateOptions": {
              "type": "text",
              "label": "Start data"
            }
          },
          {
            "type": "input",
            "key": "ENDDATE",
            "templateOptions": {
              "type": "text",
              "label": "End date"
            }
          },
          {
            "type": "input",
            "key": "DOCUMENTID",
            "templateOptions": {
              "type": "text",
              "label": "document name"
            }
          },
          {
            "type": "input",
            "key": "INPUTFILE",
            "templateOptions": {
              "type": "text",
              "label": "tar folder"
            }
          },
          {
            "type": "input",
            "key": "MetsLABEL",
            "templateOptions": {
              "type": "text",
              "label": "Mets Label"
            }
          },
          {
            "type": "input",
            "key": "MetsType",
            "templateOptions": {
              "type": "text",
              "label": "Mets Type"
            }
          },
          {
            "type": "input",
            "key": "MetsId",
            "templateOptions": {
              "type": "text",
              "label": "Mets ID"
            }
          },
          {
            "type": "input",
            "key": "MetsOBJID",
            "templateOptions": {
              "type": "text",
              "label": "Mets OBJID"
            }
          },
          {
            "type": "input",
            "key": "MetsHdrCREATEDATE",
            "templateOptions": {
              "type": "text",
              "label": "Created Date"
            }
          },
          {
            "type": "input",
            "key": "MetsHdrRECORDSTATUS",
            "templateOptions": {
              "type": "text",
              "label": "Record Status"
            }
          },
        ];
    }
})();
