(function(){

    'use strict';

    angular
        .module('formlyApp')
        .factory('province', province);

        function province() {
            function getProvinces() {
                return [
                    {
                        "name": "Alberta",
                        "value":"alberta"
                    },
                    {
                        "name":"British Columbia",
                        "value":"british_columbia"
                    },
                    {
                        "name":"Manitoba",
                        "value":"manitoba"
                    },
                    {
                        "name":"New Brunswick",
                        "value":"new_brunswick"
                    },
                    {
                        "name":"Newfoundland and Labrador",
                        "value":"newfoundland_and_labrador"
                    },
                    {
                        "name":"Northwest Territories",
                        "value":"northwest_territories"
                    },
                    {
                        "name":"Nova Scotia",
                        "value":"nova_scotia"
                    },
                    {
                        "name":"Nunavut",
                        "value":"nunavut"
                    },
                    {
                        "name":"Ontario",
                        "value":"ontario"
                    },
                    {
                        "name":"Prince Edward Island",
                        "value":"prince_edward_island"
                    },
                    {
                        "name":"Quebec",
                        "value":"quebec"
                    },
                    {
                        "name":"Saskatchewan",
                        "value":"saskatchewan"
                    },
                    {
                        "name":"Yukon",
                        "value":"Yukon"
                    },
                ];
            }

            return {
                getProvinces: getProvinces
            }
        }

})();
