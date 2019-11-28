/*@ngInject*/
const general = $translateProvider => {
  $translateProvider.translations('en', {
    ACCESSIP: 'Storage units',
    ADD_ATTRIBUTE: 'Add Attribute',
    ADD_EXTENSION: 'Add extension',
    ADD: 'Add',
    ADDRESS: 'Address',
    ADMINISTRATION: 'Administration',
    AGENT: 'Agent',
    AGENTS: 'Agents',
    AIC_DESC: 'AIC for IP',
    ALL: 'All',
    ALLOW_UNKNOWN_FILES: 'Allow unknown files',
    APPLY: 'Apply',
    APPLYCHANGES: 'Apply changes',
    APPLYFILTERS: 'Apply filters',
    APPRAISAL_DATE_DESC: 'Appraisal date',
    APPRAISAL_DATE: 'Appraisal date',
    APPRAISAL: 'Appraisal',
    APPROVAL: 'Approval',
    ARCHIVAL_DESCRIPTIONS: 'Archival descriptions',
    ARCHIVAL_LOCATION: 'Archival location',
    ARCHIVAL_STORAGE: 'Archival storage',
    ARCHIVAL_TYPE: 'Archival type',
    ARCHIVALINSTITUTION: 'Archival institution',
    ARCHIVALLOCATION: 'Archival location',
    ARCHIVALTYPE: 'Archival type',
    ARCHIVECREATORS: 'Authority records',
    ARCHIVE_POLICY: 'Archive policy',
    ARCHIVED: 'Archived',
    ARCHIVISTORGANIZATION: 'Archivist organization',
    AVAILABLE: 'Available',
    BLOCKSIZE: 'Block size',
    CACHED: 'Cached',
    CANCEL: 'Cancel',
    CANCELPRESERVATION: 'Close preservation',
    CANNOT_RECEIVE_ERROR: 'Invalid submission agreement in XML-file',
    CHANGE_PASSWORD: 'Change Password',
    CHANGED: 'Changed',
    CHOOSELANGUAGE: 'Choose preferred language',
    CITY: 'City',
    CLEAR_ALL: 'Clear all',
    CLEAR: 'Clear',
    CLOSE: 'Close',
    COLLAPSE_ALL: 'Collapse all',
    COLLECTCONTENT: 'Collect content',
    COLUMN: 'Column',
    COMMENT: 'Comment',
    COMPLETED_UPLOAD_DESC: 'Do you want to complete upload of IP(s)?',
    CONSIGN_METHOD: 'Consign method',
    CONTENT: 'Content',
    CONTENTLOCATION: 'Content location',
    CONVERSION: 'Conversion',
    CONVERTFILES: 'Convert files',
    COPYID: 'Copy ID',
    COPYPATH: 'Copy path',
    COULD_NOT_LOAD_PATH: 'Could not load path!',
    CREATE_SIP_DESC: 'Do you want to create SIP(s) from IP(s)?',
    CREATE_SIP: 'Create SIP',
    CREATE_TEMPLATE: 'Create template',
    CREATE: 'Create',
    CREATED: 'Created',
    CREATEDIP: 'Create dissemination',
    CREATE_DIP_DESC: 'Do you want to create dissemination package?',
    CREATESIP: 'Create SIP',
    CURRENTMEDIUMID: 'Current medium ID',
    CURRENTMEDIUMPREFIX: 'Current medium prefix',
    CUSTOM_IDENTIFICATION: 'Custom identification',
    DASHBOARD: 'Dashboard',
    DATABASE: 'Database',
    DATE: 'Date',
    DATES: 'Dates',
    DAY: 'Day',
    DEACTIVATEMEDIA: 'Deactivate media',
    DEACTIVATESTORAGEMEDIUM: 'Deactivate storage medium',
    DELETE: 'Delete',
    DELIVERY: 'Delivery',
    DELIVERIES: 'Deliveries',
    DESC: 'Description',
    DESCRIPTION: 'Description',
    DESELECTALL: 'Deselect all',
    DEVICE: 'Device',
    DIFFCHECK: 'Diff-check',
    DIR_EXISTS_IN_DIP_DESC:
      'Folder with this name already exists in the dissemination. Do you want to overwrite current folder?',
    DIR_EXISTS_IN_DIP: 'Folder with this name already exists!',
    DIR_EXISTS_IN_IP_DESC: 'Folder with this name already exists in the IP. Do you want to overwrite current folder?',
    DIR_EXISTS_IN_IP: 'Folder with this name already exists!',
    DISSEMINATION_PACKAGES: 'Dissemination packages',
    DISSEMINATION: 'Dissemination',
    DO_YOU_WANT_TO_REMOVE_ORDER: 'Do you want to remove order',
    DO_YOU_WANT_TO_REMOVE_TEMPLATE: 'Do you want to remove template?',
    DO_YOU_WANT_TO_DOWNLOAD_DIP: 'Do you want to download dissemination?',
    DO_YOU_WANT_TO_DOWNLOAD_ORDER: 'Do you want to download order?',
    DOWNLOAD: 'Download',
    DOCS: 'Documentation',
    DONE: 'Done',
    DOYOUWANTTOLOCKSA: 'Do you want to lock sa',
    DOYOUWANTTOREMOVEIP: 'Do you want to remove ip?',
    DO_YOU_WANT_TO_REMOVE_IP_WORKAREA: 'Do you want to remove IP from workspace?',
    EDIT: 'Edit',
    EDIT_ORDER: 'Edit order',
    EMAILS_FAILED: 'Emails failed',
    EMAILS_SENT: 'Emails sent',
    EMPTY: 'Empty',
    ENABLED: 'Enabled',
    ENABLEDDESC: 'If checked, profile is enabled',
    END: 'End',
    ENTERORDERLABEL: 'Enter label for order',
    ENTERPROFILENAME: 'Enter new profile name',
    ENTER_VALID_COORDINATE_VALUE: 'Enter valid coordinate value. Example: 40.785091',
    ENTERSAPROFILENAME: 'Enter new SA-profile name',
    ENTITY: 'Entity',
    ENTITYDESC: 'Profile type',
    EXPAND_ALL: 'Expand all',
    EXPORT_ACTION: 'Export',
    EXPORT_RESULT: 'Export result',
    FAILED: 'Failed',
    FAILURE: 'Failure',
    FAMILY_NAME: 'Family name',
    FILE_EXISTS_IN_DIP_DESC:
      'File with this name already exists in the dissemination. Do you want to overwrite current file?',
    FILE_EXISTS_IN_DIP: 'File with this name already exists!',
    FILE_EXISTS_IN_IP_DESC: 'File with this name already exists in the IP. Do you want to overwrite current file?',
    FILE_EXISTS_IN_IP: 'File with this name already exists!',
    FILE: 'File',
    FILECONVERSION: 'File conversion',
    FILENAME: 'File name',
    FILES_PER_PAGE: 'Files per page',
    FILTER: 'Filter',
    FILTERBY: 'Filter by',
    FILTERS: 'Filters',
    FIRST_NAME: 'First name',
    FORCECOPIES: 'Force additional copies on the same target medium',
    FORMAT_CONVERSION: 'Format conversion',
    FORMAT: 'Format',
    FROM: 'from',
    GENERATE_TEMPLATE: 'Generate template',
    GET_AS_CONTAINER: 'Get as container',
    GET_AS_NEW_GENERATION: 'Get as new generation',
    GET: 'Get',
    GLOBALSEARCH: 'search ...',
    GLOBALSEARCHDESC_ARCHIVE_CREATORS: 'List all authority records associated to the search term',
    GLOBALSEARCHDESC_ARCHIVES: 'List all resources associated to the search term',
    GLOBALSEARCHDESC_IP: "List all IP's associated to the search term",
    GLOBALSEARCHDESC_MEDIUM_CONTENT: 'List all medium content associated to the search term',
    GLOBALSEARCHDESC_MEDIUM: 'List all storage mediums associated to the search term',
    GLOBALSEARCHDESC_MIGRATION: 'List all migrations associated to the search term',
    GLOBALSEARCHDESC_ORDER: 'List all orders associated to the search term',
    GLOBALSEARCHDESC_QUEUE: 'List all queue entries associated to the search term',
    GLOBALSEARCHDESC_ROBOT: 'List all robots associated to the search term',
    GLOBALSEARCHDESC_RULE: 'List all rules associated to the search term',
    GLOBALSEARCHDESC_STRUCTURES: 'List all classification structures associated to the search term',
    GLOBALSEARCHDESC_TAPE_DRIVE: 'List all tape drives associated to the search term',
    GLOBALSEARCHDESC_TAPE_SLOT: 'List all tape slots associated to the search term',
    GLOBALSEARCHDESC_VALIDATION: 'List all validations associated to the search term',
    GRID_VIEW: 'Grid',
    HELP: 'Help',
    ID: 'ID',
    IDENTIFICATION: 'Identification',
    INCLUDE_AIC_XML: 'Include AIC XML',
    INCLUDE_INACTIVE_IPS: 'Include inactive information packages',
    INCLUDE_PACKAGE_XML: 'Include package XML',
    INCLUDEDPROFILES: 'Included profiles',
    INFO: 'Info',
    INFOPAGE: 'Info Page',
    INFORMATION_CLASS: 'Information class',
    INFORMATION_PACKAGE: 'Information Package',
    INFORMATION_PACKAGE_INFORMATION: 'Package information',
    INFORMATION_PACKAGES: 'Information packages',
    INGEST: 'Ingest',
    INPROGRESS: 'In progress',
    INVENTORY: 'Inventory',
    INVENTORYROBOTS: 'Inventory robots',
    IOQUEUE: 'IO-queue',
    IP_DELETE: "IP's to be deleted",
    IP_EXISTS: 'IP with object identifer value "{{ip}}" already exists',
    IP_GENERATION: 'IP generation: {{generation}}',
    IP_REMOVED: 'IP {{label}} removed!',
    IP_VIEW_TYPE: 'IP view type',
    IPAPPROVAL: 'Approval',
    ITEMSPERPAGE: 'Items per page',
    LABEL: 'Label',
    LANGUAGE: 'Language',
    LEVEL: 'Level',
    LIST_VIEW: 'List',
    LOADING: 'Loading',
    LOCATION: 'Location',
    LOCATIONSTATUS: 'Location status',
    LOCK_ERROR: 'could not be locked',
    LOCK: 'Lock',
    LOCK_SA_TO_IP: 'Lock submission agreement to information package',
    LOCKED: 'Locked',
    LOCKPROFILE: 'Lock profile',
    LOCKSA: 'Lock SA',
    LOGIN: 'Login',
    LOGOUT: 'Logout',
    LONGTERM_ARCHIVAL_STORAGE: 'Long-term archival storage',
    MANAGEMENT: 'Management',
    MAPSTRUCTURE: 'Map structure',
    MARKFORRECEIVE: 'Mark for receive',
    MATCH_ERROR: 'Information_class in archive policy does not match information_class in ip: ',
    MAXCAPACITY: 'Max capacity',
    MEDIA_MIGRATION: 'Media migration',
    MEDIAINFORMATION: 'Media information',
    MEDIUM: 'Medium',
    MEDIUM_RANGE_ENABLED: 'Enter medium ID range',
    MEDIUMCONTENT: 'Medium content',
    MEDIUMID: 'Medium ID',
    MEDIUMID_MAX: 'Medium ID end',
    MEDIUMID_MIN: 'Medium ID start',
    MEDIUMPREFIX: 'Medium prefix',
    MESSAGE: 'Message',
    METADATA: 'Metadata',
    MIGRATABLE: 'Migratable',
    MIGRATE: 'Migrate',
    MIGRATION_TASKS: 'Migration tasks',
    MINUTE: 'Minute',
    MISSING_AIC_DESCRIPTION: 'AIC Description profile missing in Submission agreement',
    MISSING_AIP_DESCRIPTION: 'AIP Description profile missing in Submission agreement',
    MISSING_AIP: 'AIP profile missing in Submission agreement',
    MISSING_DIP: 'DIP profile missing in Submission agreement',
    MONTH: 'Month',
    MOUNT: 'Mount',
    MOVE_TO_APPROVAL: 'Move to Approval',
    MOVE_TO_INGEST_APPROVAL: 'Move to Ingest/Approval',
    MY_PAGE: 'My page',
    MYPAGE: 'My page',
    NAME: 'Name',
    NAVIGATETO: 'Navigate to',
    NEEDTOMIGRATE: 'Need to migrate',
    NEWORDER: 'New order',
    NEWPASSWORD: 'New Password',
    NO_ACTIONS_FOR_SELECTED_IPS: 'No actions available for selected object(s)',
    NO_ARGUMENTS: 'No arguments',
    NO_PARAMETERS: 'No parameters',
    NO_RESPONSE_FROM_SERVER: 'No response from server',
    NO_RESULTS_FOUND: 'No results found',
    NO_SUBMISSION_AGREEMENT_AVAILABLE: 'No Submission Agreement available',
    NO_AUTHORIZED_NAME_TYPE: 'Authorized name type missing',
    NO: 'No',
    NOTES: 'Notes',
    NUMBEROFMOUNTS: 'Number of mounts',
    OBJECT: 'Object',
    OBJECTID: 'Object ID',
    OBJECTIDENTIFIERVALUE: 'Object identifier value',
    OFFLINE: 'Offline',
    OK: 'Ok',
    OLDPASSWORD: 'Old Password',
    ONLINE: 'Online',
    OPTIONS: 'Options',
    OR: 'Or',
    ORDER: 'Order',
    ORDER_CONTENT: 'Content description',
    ORDERS: 'Orders',
    OTHER: 'Other',
    OUTCOME: 'Outcome',
    OVERVIEW: 'Overview',
    PACKAGE_TYPE_NAME_EXCLUDE: 'Exclude package type',
    PACKAGE_TYPE: 'Package type',
    PACKAGE: 'Package',
    PACKAGEDEPENDENCIES: 'Package dependencies',
    PACKAGEINFORMATION: 'Package information',
    PAGE_DOES_NOT_EXIST: 'Page does not exist',
    PARAMETERS: 'Parameters',
    PASSWORD: 'Password',
    PATH: 'Path',
    PENDING: 'Pending',
    PERSONAL_NUMBER: 'Personal identification number',
    PHONE: 'Phone number',
    PLATFORM: 'Platform',
    POLICY: 'Policy',
    POLICYID: 'Policy ID',
    POLICYSTATUS: 'Policy status',
    POSTAL_CODE: 'Postal code',
    POSTED: 'Posted',
    PREPARE_IP_DESC: 'Do you want to prepare IP(s) for upload?',
    PREPARE_IP: 'Prepare IP',
    PREPARE_NEW_IP: 'Prepare new IP',
    PREPARE: 'Prepare',
    PREPAREDIP: 'Prepare dissemination',
    PREPAREDIPDESC: 'Prepare new dissemination',
    PREPAREIP: 'Prepare IP',
    PREPAREIPDESC: 'Create a new IP',
    PREPARESIP: 'Prepare SIP',
    PRESERVE: 'Preserve',
    PREVIOUSMEDIUMPREFIX: 'Previous medium prefix',
    PRODUCER: 'Producer',
    PROFILE: 'Profile',
    PROFILEDESC: 'Select profile',
    PROFILEMAKER: 'Profile maker',
    PROFILEMANAGER: 'Profile manager',
    PUBLIC: 'Public',
    PUBLISH: 'Publish',
    PURPOSE: 'Purpose',
    QUEUES: 'Queues',
    QUARANTINE: 'Quarantine',
    READ_ONLY: 'Read only',
    RECEIVE_SIP_DESC: 'Do you want to receive SIP {{object_identifier_value}}?',
    RECEIVE_SIP: 'Receive SIP',
    RECEIVE: 'Receive',
    RECEIVE_INFORMATION_PACKAGE: 'Receive information package',
    RECEIVESIP: 'Receive SIP',
    RECEPTION: 'Reception',
    REDO: 'Retry',
    REFRESH: 'Refresh',
    REFRESHPAGE: 'Refresh page',
    REFRESHTABLEDESC: 'Refresh table',
    REMOVE: 'Remove',
    REPEATPASSWORD: 'Repeat Password',
    REQUEST: 'Request',
    REQUESTAPPROVED: 'Request approved',
    REQUESTTYPE: 'Request',
    RESPONSIBLE: 'Responsible',
    RESTRICTEDVIEW: 'You do not have permission to access this view.',
    RESULT: 'Result',
    RETRY: 'Retry',
    REVOKE: 'Stop',
    REVOKED: 'Stopped',
    ROBOTINFORMATION: 'Robot information',
    ROBOTQUEUE: 'Robot queue',
    ROOT: 'Root',
    RULES_SAVED: 'Rules saved',
    SA_PUBLISHED: 'Submission agreement: {{name}} has been published',
    SAEDITOR: 'SA editor',
    SAVE_ERROR: 'An error occured!',
    SAVE: 'Save',
    SAVED_MESSAGE: 'Saved!',
    SAVESAPROFILE: 'Save SA profile',
    SEARCH_ADMIN: 'Search',
    SEARCH_ADMINISTRATION: 'Administration for search views',
    SEARCH: 'Search',
    SEE_ALL: 'See all',
    SEE_MORE_INFO_ABOUT_PAGE: 'See more information about this page',
    SEE_MY_IPS: 'See own information packages',
    SELECT: 'Select',
    SEETRACEBACK: 'See traceback',
    SELECT_ALL: 'Select all',
    SELECT_ORDERS: 'Select orders ..',
    SELECT_TAGS: 'Select tags ...',
    SELECTALL: 'Select all',
    SELECTED: 'Selected',
    SELECTIONLIST: 'Selection list',
    SELECTONE: 'Select One',
    SETTINGS_SAVED: 'Settings saved',
    SETTINGS: 'Settings',
    SIZE: 'Size',
    SKIP: 'Skip',
    START: 'Start',
    STARTED: 'Started',
    STARTMIGRATION: 'Start migration',
    STATE: 'State',
    STATEDESC: 'Profile state',
    STATUS: 'Status',
    STEP: 'Step',
    STORAGE_MEDIUMS: 'Storage mediums',
    STORAGE_POLICY: 'Storage policy',
    STORAGE_STATUS_DESC: 'Storage status, Archival storage or Long-term archival storage',
    STORAGE_STATUS: 'Storage status',
    STORAGE_UNIT: 'Storage unit',
    STORAGE_UNITS: 'Storage units',
    STORAGE: 'Storage',
    STORAGEMAINTENANCE: 'Storage maintenance',
    STORAGEMEDIUM: 'Storage medium',
    STORAGEMIGRATION: 'Storage migration',
    STORAGETARGET: 'Storage target',
    SUBMISSION_AGREEMENT: 'Submission agreement',
    SUBMISSIONAGREEMENT: 'Submission Agreement',
    SUBMIT_SIP_DESC: 'Do you want to submit SIP(s)?',
    SUBMIT: 'Submit',
    SUBMITDESCRIPTION: 'Submit description',
    SUBMITSIP: 'Submit SIP',
    SUCCESS: 'Success',
    SUPPORT: 'Support',
    SYSTEM: 'System',
    TAGS: 'Tags',
    TAPEDRIVES: 'Tape drives',
    TAPELIBRARY: 'Tape library',
    TAPESLOTS: 'Tape slots',
    TARGET_NAME: 'Target name',
    TARGET: 'Target',
    TARGETNAME: 'Target name',
    TARGETVALUE: 'Target value',
    TASKS: 'Tasks',
    TEMPPATH: 'Temporary path',
    TIME: 'Time',
    TOACCESS: 'to gain access.',
    TOIP: 'to IP',
    TRACEBACK: 'Traceback',
    TYPE: 'Type',
    UNAVAILABLE: 'Unavailable',
    UNDO: 'Undo',
    UNLOCKPROFILE: 'Unlock profile',
    UNLOCKPROFILEINFO:
      'If you unlock this profile, the IP will be moved to the "Prepare IP" view. Proceed by clicking OK.',
    UNMOUNT_FORCE: 'Unmount(force)',
    UNMOUNT: 'Unmount',
    UNPUBLISH: 'Unpublish',
    UNSAVED_DATA_WARNING: 'Any changes will be lost, are you sure?',
    UNSPECIFIED: 'Unspecified',
    UPDATE: 'Update',
    USE_SELECTED_SA_AS_TEMPLATE: 'Use selected submission agreement as template',
    USE_TEMPLATE: 'Use template',
    USE: 'Use',
    USEDCAPACITY: 'Used capacity',
    USERNAME: 'Username',
    VALIDATEFILEFORMAT: 'Validate file format',
    VALIDATEFILES: 'Validate files',
    VALIDATEINTEGRITY: 'Validate Integrity',
    VALIDATELOGICALPHYSICALREPRESENTATION: 'Validate logical physical representation',
    VALIDATEXMLFILE: 'Validate XML file',
    VALIDATOR: 'Validator',
    VALIDATORCHOICES: 'Validator choices',
    VALUE: 'Value',
    VERSION: 'Version',
    VERSIONS: 'Versions',
    VIEW: 'View',
    WORKAREA: 'Workspace',
    WORKING_ON_NEW_GENERATION: '{{username}} is working on a new generation of this IP',
    YES: 'Yes',
    YOUHAVELOGGEDOUT: 'You have logged out.',
    en: 'English',
    sv: 'Svenska',
  });
};

export default general;
