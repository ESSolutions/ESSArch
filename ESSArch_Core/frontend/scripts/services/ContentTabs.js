angular.module('essarch.services').factory('ContentTabs', function($translate, Notifications) {
    var disabledStates = [
        'Creating',
        'Submitting',
        'Receiving',
        'Transferring',
        'Preserving'
    ];
    var specialTabs = {
        // ETP
        'home.createSip.prepareIp': {
            prepare: ['Preparing', 'Prepared']
        },
        'home.createSip.collectContent': {
            collect_content: ['Prepared', 'Uploading']
        },
        'home.createSip.ipApproval': {
            approval: ['Uploaded']
        },
        'home.submitSip.prepareSip': {
            submit_sip: ['Created']
        },
        // ETA
        'home.reception': {
            receive: ['At reception', 'Prepared']
        },
        'home.workarea.validation': {
            validation: ['Received']
        },
        'home.workarea.transformation': {
            transformation: ['Received']
        },
        'home.transferSip': {
            transfer_sip: ['Received']
        },
        // EPP
        'home.access.createDip':
        {
            create_dip: ['Prepared'],
            preserve: ['Created']
        },
        'home.workarea': {
            workarea: ['Ingest Workarea', 'Access Workarea']
        },
        'home.access.accessIp': {
            access_ip: ['Preserved']
        },
        'home.ingest.workarea': {
            workarea: ['Ingest Workarea']
        },
        'home.access.workarea': {
            workarea: ['Access Workarea']
        },
        'home.ingest.ipApproval': {
            approval: ['Received']
        },
        'home.ingest.reception': {
            receive: ['At reception', 'Prepared']
        }
    }
    var service = {
        /**
         * Returns allowed tabs in correct order to decide visibility and set proper
         * default selected tab
         * @param {Array} ips Array of selected IPs
         * @param {String} page Current page, ie ip_approval, dip or access_ip
         * @param {String} tab Tab to check visibility for
         */
        visible: function(ips, page) {
            var visible = true;
            var list = [];
            if(specialTabs[page]) {
                ips.forEach(function(ip) {
                    if(disabledStates.includes(ip.state)) {
                        visible = false;
                    }
                    angular.forEach(specialTabs[page], function(value, key) {
                        if(value.includes(ip.state)) {
                            if(!list.includes(key)) {
                                list.push(key)
                            }
                        }
                    })
                })
                ips.forEach(function(ip) {
                    list.forEach(function(item, idx, array) {
                        if(!specialTabs[page][item].includes(ip.state)) {
                            array.splice(idx, 1);
                        }
                    })
                })
            }
            if(!visible) {
                list = [];
            }
            return list;
        }
    }
    return service;
})
