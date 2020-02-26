/*@ngInject*/
export default ($translateProvider: ng.translate.ITranslateProvider) => {
  $translateProvider.translations('en', {
    ACCESS: {
      ACCESS: 'Access',
      ADD_FIELD: 'Add field',
      ADD_FIRST_LEVEL_LOCATION: 'Add first level location',
      ADD_IDENTIFIER: 'Add identifier',
      ADD_LOCATION: 'Add location',
      ADD_NODE: 'Add node',
      ADD_RELATED_ARCHIVE: 'Add related resource',
      ADD_RELATED_ARCHIVE_CREATOR: 'Add related authority record',
      ADD_RELATION: 'Add relation',
      ADD_RELATION_TO_STRUCTURE_UNIT: 'Add relation to structure unit',
      ADD_RULE: 'Add rule',
      ADD_STRUCTURE_RULE: 'Add new structure rule',
      ADD_STRUCTURE_UNIT: 'Add structure unit',
      ADD_TO_STRUCTURE: 'Add to structure unit',
      ADDED_TO_TRANSFER: 'Added to transfer',
      ADMINISTRATIVE_DATES: 'Administrative dates',
      ALT_NAME: 'Alternate name',
      ALT_NAMES: 'Names',
      APPRAISAL_DATE: 'Appraisal date',
      ARCHIVE: 'Resource',
      ARCHIVES: 'Resources',
      ARCHIVE_CREATOR: 'Creator',
      ARCHIVE_SAVED: 'Resource saved',
      ARCHIVE_REFERENCE: 'Resource reference',
      ARCHIVE_RESPONSIBLE: 'Resource responsible',
      AUTHORIZED_NAME: 'Authorized name',
      BASIC_DATA: 'Basic data',
      CAN_BE_MOVED: 'Can be moved',
      CAPACITY: 'Capacity',
      CERTAINTY: 'Certainty',
      CLASSIFICATION_STRUCTURE: 'Structure',
      CLASSIFICATION_STRUCTURES: 'Structures',
      CLASSIFICATION_STRUCTURE_CREATED: 'Structure created',
      CLASSIFICATION_STRUCTURE_NAME: 'Structure name',
      CLASSIFICATION_STRUCTURE_REMOVED: 'Structure removed',
      COMPONENT: 'Component',
      CONTENTS: 'Contents',
      CONTENT_TYPE: 'Content type',
      COULD_NOT_BE_MOVED: 'Could not be moved',
      CPF: 'Cpf',
      CREATE_ARCHIVE_CREATOR: 'New authority record',
      CREATE_DELIVERY: 'Create delivery',
      CREATE_LABELS: 'Create labels',
      CREATE_NEW_FIELD: 'Create new field',
      CREATE_NEW_STRUCTURE: 'Create new structure',
      CREATE_NEW_VERSION: 'Create new version',
      CREATE_TRANSFER: 'Create transfer',
      CREATING: 'Creating',
      CUSTOM_FIELDS: 'Custom fields',
      DATES: 'Dates',
      DATE_MISSING: 'Date missing',
      DECISION_DATE: 'Decision date',
      DELETE_FIELD: 'Do you want to delete field: {{field}}?',
      DELIVERY: 'Delivery',
      DESELECT_FILTER: 'Remove filter choice',
      DIP_PACKAGES: 'Dissemination information packages',
      DOCUMENT: 'Document',
      DO_YOU_WANT_TO_REMOVE_AGENT_NAME: 'Do you want to remove agent name?',
      DO_YOU_WANT_TO_REMOVE_ARCHIVE_CREATOR: 'Do you want to remove authority record?',
      DO_YOU_WANT_TO_REMOVE_ARCHIVE_RELATION: 'Do you want to remove resource relation?',
      DO_YOU_WANT_TO_REMOVE_DELIVERY: 'Do you want to remove delivery?',
      DO_YOU_WANT_TO_REMOVE_HISTORY: 'Do you want to remove history?',
      DO_YOU_WANT_TO_REMOVE_IDENTIFIER: 'Do you want to remove identifier?',
      DO_YOU_WANT_TO_REMOVE_LOCATION: 'Do you want to remove location?',
      DO_YOU_WANT_TO_REMOVE_MANDATE: 'Do you want to remove mandate?',
      DO_YOU_WANT_TO_REMOVE_NODE: 'Do you want to remove node?',
      DO_YOU_WANT_TO_REMOVE_NODE_FROM_CLASSIFICATION_STRUCTURE: 'Do you want to remove node from structure?',
      DO_YOU_WANT_TO_REMOVE_NOTE: 'Do you want to remove note?',
      DO_YOU_WANT_TO_REMOVE_PLACE: 'Do you want to remove place?',
      DO_YOU_WANT_TO_REMOVE_RELATION: 'Do you want to remove relation?',
      DO_YOU_WANT_TO_REMOVE_STRUCTURE: 'Do you want to delete structure?',
      DO_YOU_WANT_TO_REMOVE_STRUCTURE_UNIT: 'Do you want to remove structure unit?',
      DO_YOU_WANT_TO_REMOVE_TRANSFER: 'Do you want to remove transfer?',
      EDIT_ARCHIVE: 'Edit resource',
      EDIT_ARCHIVE_CREATOR: 'Edit authority record',
      EDIT_CLASSIFICATION_STRUCTURE: 'Edit structure',
      EDIT_DELIVERY: 'Edit delivery',
      EDIT_FIELD: 'Edit field',
      EDIT_LOCATION: 'Edit location',
      EDIT_RELATED_ARCHIVE: 'Edit resource relation',
      EDIT_RELATED_ARCHIVE_CREATOR: 'Edit related authority record',
      EDIT_RELATION_TO_STRUCTURE_UNIT: 'Edit relation to structure unit',
      EDIT_TRANSFER: 'Edit transfer',
      END_YEAR: 'End year',
      EXPORT_ARCHIVE: 'Printable finding aid',
      EXPORT_OPTION: 'Export option',
      FIELD_EXISTS: 'Field already exists!',
      FILE_EXTENSIONS: 'File format',
      FLAGGED_FOR_APPRAISAL: 'Appraisal',
      GO_TO_SEARCH: 'Go to Search',
      GLOBALSEARCHDESC_DELIVERIES: 'List all deliveries associated to the search term',
      GLOBALSEARCHDESC_TAGS: 'List all nodes associated to the search term',
      GLOBALSEARCHDESC_TRANSFERS: 'List all transfers associated to the search term',
      GLOBALSEARCHDESC_UNITS: 'List all structure units associated to the search term',
      HISTORY: 'History',
      HITS: 'List',
      HREF: 'Link',
      IDENTIFIER: 'Identifier',
      IDENTIFIERS: 'Identifiers',
      IDS: 'IDs',
      IMPORT_DATE: 'Import date',
      INCLUDED_TYPES: 'Included types',
      INCLUDE_DESCENDANT_NODES: 'Include descendant nodes',
      INDEX: 'Index',
      INSTANCE: 'Instance',
      KEY: 'Key',
      LANGUAGE: 'Language',
      LATITUDE: 'Latitude',
      LEVEL: 'Level',
      LEVEL_OF_DETAIL: 'Level of detail',
      LINK_TO_TRANSFER: 'Link to transfer',
      LINK_TO_LOCATION: 'Link to location',
      LOCATION: 'Location',
      LOCATION_FUNCTION: 'Function',
      LOCATION_LINK_SUCCESS: 'Location link updated',
      LONGITUDE: 'Longitude',
      MAIN: 'Last name',
      MAIN_CATEGORY: 'Main category',
      MANDATE: 'Mandate',
      MANDATES: 'Mandates',
      MANDATES_DESC: '',
      METRIC: 'Metric',
      METRIC_PROFILE: 'Location profile',
      NARROW_RESULTS: 'Narrow results',
      NAVIGATE_TO_TRANSFER: 'Navigate to related transfer',
      NEW_ARCHIVE: 'New resource',
      NEW_ARCHIVE_CREATED: 'New resource created!',
      NEW_CLASSIFICATION_STRUCTURE: 'New structure',
      NEW_FIELD: 'New custom field',
      NEW_STRUCTURE_CREATED: 'New structure created',
      NEW_TYPE: 'New rule',
      NEW_VERSION: 'New version',
      NEW_VERSION_CREATED: 'New version created',
      NODE: 'Node',
      NODES: 'Nodes',
      NODE_ADDED: 'Node added!',
      NODE_EDITED: 'Node edited!',
      NODE_REMOVED: 'Node removed!',
      NODE_REMOVED_FROM_STRUCTURE: 'Node removed from structure',
      NO_ARCHIVES: 'There are no resources ...',
      NO_CLASSIFICATION_STRUCTURES: 'There are no structures ...',
      NO_HISTORY: 'No history available',
      NO_REMARKS: 'No notes available',
      NO_STRUCTURE_UNITS: 'There are no structure units ...',
      OF: 'of',
      ORGANIZATION: 'Organization',
      PART: 'First name',
      PERSONAL_IDENTIFICATION_NUMBER: 'Personal identification number',
      PLACE: 'Place',
      PLACE_IN_ARCHIVE: 'Place in archive',
      PLACE_NODE_IN_ARCHIVE: 'Place node in archive',
      PLACES: 'Places',
      PRODUCER_ORGANIZATION: 'Producer organization',
      PUBLISH_CLASSIFICATION_STRUCTURE: 'Publish structure',
      PUBLISH_CLASSIFICATION_STRUCTURE_DESC: 'Do you want to publish structure: {{name}}',
      PUBLISHED: 'Published',
      RECORD: 'Record',
      RECORD_STATUS: 'Record status',
      REFERENCE_CODE: 'Reference code',
      RELATED: 'Related',
      RELATED_AGENTS: 'Related agents',
      RELATED_ARCHIVE_CREATORS: 'Related authority records',
      RELATED_RESOURCES: 'Related resources',
      RELATED_STRUCTURE_UNITS: 'Related structure units',
      REMARKS: 'Notes',
      REMOVE_ARCHIVE: 'Remove resource',
      REMOVE_ARCHIVE_DESC: 'Do you want to remove resource: {{name}}',
      REMOVE_FROM_CLASSIFICATION_STRUCTURE: 'Remove from structure',
      REMOVE_LOCATION_FOR_NODE: 'Remove location link for: {{reference_code}} {{name}}',
      REMOVE_LOCATION_FOR_NODES: 'Remove location links for:',
      REMOVE_LOCATION_LINK: 'Remove location link',
      REMOVE_NODE: 'Remove node',
      REMOVE_NODE_FROM_TRANSFER: 'Do you want to remove node: {{reference_code}} {{name}} from transfer?',
      REMOVE_NODES_FROM_TRANSFER: 'Do you want to remove nodes from transfer?',
      REMOVE_RELATION_TO_STRUCTURE_UNIT: 'Remove structure unit relation',
      REMOVE_RELATION_TO_STRUCTURE_UNIT_DESC: 'Do you want to remove relation to {{name}}?',
      REMOVE_SAVED_SEARCH: 'Do you want to remove saved search?',
      REMOVE_STRUCTURE_RULE: 'Remove rule',
      REMOVE_STRUCTURE_RULE_DESC: 'Do you want to remove rule?',
      REMOVE_TRANSFER_LINK: 'Remove transfer link',
      REPLACE: 'Link to new location',
      REVISE_DATE: 'Last modified',
      RULE_ADDED: 'Rule added',
      RULE_REMOVED: 'Rule removed',
      RULES: 'Rules',
      SAVE_RULES: 'Save rules',
      SAVE_SEARCH: 'Save search',
      SAVED_SEARCHES: 'Saved searches',
      SCRIPT: 'Script',
      SEE_ALL: 'See all',
      SEE_MORE: 'See more',
      SELECT_LOCATION_FOR_NODE: 'Link {{type.name}}: {{reference_code}} {{name}} to location',
      SELECT_LOCATION_FOR_NODES: 'Link nodes to location',
      SELECT_TRANSFER_FOR_NODE: 'Select transfer for {{reference_code}} {{name}}',
      SELECT_TRANSFER_FOR_NODES: 'Select transfer for nodes',
      SEND_AS_EMAIL: 'Send as email',
      SET_CURRENT_VERSION: 'Set as current',
      SHOWING_RESULT: 'Showing result',
      START_YEAR: 'Start year',
      STRUCTURE_UNIT: 'Structure unit',
      SUB_CATEGORY: 'Subcategory',
      SUB_TYPE: 'Subtype',
      SUBMITTER_ORGANIZATION: 'Submitter organization',
      SUBMITTER_ORGANIZATION_MAIN_ADDRESS: 'Address',
      SUBMITTER_INDIVIDUAL: 'Submitter individual',
      SUBMITTER_INDIVIDUAL_NAME: 'Name',
      SUBMITTER_INDIVIDUAL_PHONE: 'Phone number',
      SUBMITTER_INDIVIDUAL_EMAIL: 'Email',
      SUBMITTER_INFO: 'Submitter information',
      SURE: 'Sure',
      TAGS_IN_LOCATION: 'Content in location',
      TAGS_IN_TRANSFER: 'Nodes in transfer',
      TEMPLATE_OR_INSTANCE: 'Template or instance',
      TEMPLATE: 'Template',
      TERMS_AND_CONDITION: 'Terms and condition',
      TEXT: 'Text',
      TIME_RANGE_END: 'Time range end',
      TIME_RANGE_START: 'Time range start',
      TITLE: 'Title',
      TOPOGRAPHY: 'Topography',
      TRANSFER: 'Transfer',
      TRANSFERS: 'Transfers',
      UNITS_IN_TRANSFER: 'Structure units in transfer',
      UNPUBLISH_CLASSIFICATION_STRUCTURE: 'Unpublish structure',
      UNPUBLISH_CLASSIFICATION_STRUCTURE_DESC: 'Do you want to unpublish structure: {{name}}',
      UNPUBLISHED: 'Unpublished',
      UNSURE: 'Unsure',
      UPDATE_DESCENDANTS: 'Update descendant nodes',
      USE_UUID_AS_REFCODE: 'Use archive UUID as reference code',
      VALID_DATE_END: 'Period of validity end',
      VALID_DATE_START: 'Period of validity start',
      VERSION: 'Version',
      VERSION_HISTORY: 'Version history',
      VERSION_HISTORY_DESC: 'List of all versions of data for current node',
    },
    ARCHIVEMANAGER: 'Resource manager',
    CLASSIFICATIONSTRUCTURES: 'Structures',
    ARCHIVECREATORS: 'Authority records',
    TRANSFERS: 'Transfers',
  });
};
