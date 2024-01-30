# Email configuration
# EMAIL_HOST = 'mail.essolutions.se'
# EMAIL_PORT = 4465
# EMAIL_USE_SSL = True
# EMAIL_HOST_USER = 'e-archive@essarch.org'
# EMAIL_HOST_PASSWORD = 'xyz'
# SERVER_EMAIL = 'e-archive@essarch.org' # "admin" from
# DEFAULT_FROM_EMAIL = 'e-archive@essarch.org' # from
# EMAIL_SUBJECT_PREFIX = "[ESSArch x] "
# ADMINS = (
#     ('Henrik Ek', 'henrik@essolutions.se'),
# )

# ### BEGIN LDAP ###
try:
    import ldap
    from django_auth_ldap.config import (
        ActiveDirectoryGroupType,
        LDAPSearch,
        LDAPSearchUnion,
    )
except ImportError:
    pass
else:
    ENABLE_LDAP_LOGIN = env.bool('ESSARCH_ENABLE_LDAP_LOGIN', default=False)
    if ENABLE_LDAP_LOGIN:
        AUTHENTICATION_BACKENDS.insert(
            0, 'django_auth_ldap.backend.LDAPBackend')
    # Baseline configuration.
    AUTH_LDAP_SERVER_URI = "ldap://fs.essarch.local"

    AUTH_LDAP_BIND_DN = "arch@essarch.org"
    AUTH_LDAP_BIND_PASSWORD = "xyz"
    AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(
        LDAPSearch("cn=users,dc=essarch,dc=org",
                   ldap.SCOPE_ONELEVEL, "(sAMAccountName=%(user)s)"),
        LDAPSearch("ou=ESSArch1,ou=ESSArch,dc=essarch,dc=org",
                   ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"),
    )
    # or perhaps:
    # AUTH_LDAP_USER_DN_TEMPLATE = "uid=%(user)s,ou=users,dc=kdrs,dc=no"

    # Set up the basic group parameters.
    AUTH_LDAP_GROUP_SEARCH = LDAPSearch("ou=ESSArch,dc=essarch,dc=org",
                                        ldap.SCOPE_SUBTREE, "(objectClass=group)"
                                        )
    AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType(name_attr="cn")

    # Simple group restrictions
    AUTH_LDAP_REQUIRE_GROUP = "cn=ESSArch1_active,ou=ESSArch1,ou=ESSArch,dc=essarch,dc=org"
    AUTH_LDAP_DENY_GROUP = "cn=ESSArch_disabled,ou=Global,ou=ESSArch,dc=essarch,dc=org"

    # Populate the Django user from the LDAP directory.
    AUTH_LDAP_USER_ATTR_MAP = {
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail"
    }

    AUTH_LDAP_USER_FLAGS_BY_GROUP = {
        "is_active": "cn=ESSArch1_active,ou=ESSArch1,ou=ESSArch,dc=essarch,dc=org",
        "is_staff": "cn=ESSArch_staff,ou=Global,ou=ESSArch,dc=essarch,dc=org",
        "is_superuser": "cn=ESSArch_superuser,ou=Global,ou=ESSArch,dc=essarch,dc=org"
    }

    # This is the default, but I like to be explicit.
    AUTH_LDAP_ALWAYS_UPDATE_USER = True

    # Use LDAP group membership to calculate group permissions.
    AUTH_LDAP_FIND_GROUP_PERMS = True

    # Cache group memberships for an hour to minimize LDAP traffic
    AUTH_LDAP_CACHE_GROUPS = False
    # AUTH_LDAP_GROUP_CACHE_TIMEOUT = 30 # does not seem to work with redis as cache backend

    # Furnish permissions for any Django user, regardless of which backend authenticated it
    AUTH_LDAP_AUTHORIZE_ALL_USERS = True

    # AUTH_LDAP_START_TLS = True

    LOGGING_LDAP = {
        'handlers': {
            'log_file_auth_ldap': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'verbose',
                'filename': os.path.join(LOGGING_DIR, 'auth_ldap.log'),
                'maxBytes': 1024 * 1024 * 100,  # 100MB
                'backupCount': 5,
            },
        },
        'loggers': {
            'django_auth_ldap': {
                'level': 'INFO',
                'handlers': ['log_file_auth_ldap'],
                'propagate': False,
            },
        },
    }
# ### END LDAP ###

# ### BEGIN ADFS ###
try:
    import saml2
    import saml2.saml
except ImportError:
    pass
else:
    INSTALLED_APPS.append('djangosaml2')
    AUTHENTICATION_BACKENDS.append('djangosaml2.backends.Saml2Backend')
    MIDDLEWARE.append('djangosaml2.middleware.SamlSessionMiddleware')
    ENABLE_ADFS_LOGIN = env.bool('ESSARCH_ENABLE_ADFS_LOGIN', default=False)
    ENABLE_SAML2_METADATA = env.bool('ESSARCH_ENABLE_SAML2_METADATA', default=True)
    LOGIN_URL = '/saml2/login/'
    LOGIN_REDIRECT_URL = '/'
    ESSARCH_PUBLIC_URL = env.url('ESSARCH_PUBLIC_URL', default='https://essarch.domain.xyz')
    SP_SERVICE_URL = '{}://{}/{}'.format(ESSARCH_PUBLIC_URL.scheme,
                                         ESSARCH_PUBLIC_URL.netloc,
                                         ESSARCH_PUBLIC_URL.path).rstrip('/')
    ESSARCH_IDP_SERVICE_URL = env.url('ESSARCH_IDP_SERVICE_URL', default='https://idp.domain.xyz')
    IDP_SERVICE_URL = '{}://{}/{}'.format(ESSARCH_IDP_SERVICE_URL.scheme,
                                          ESSARCH_IDP_SERVICE_URL.netloc,
                                          ESSARCH_IDP_SERVICE_URL.path).rstrip('/')
    # XMLSEC_BINARY = '/usr/bin/xmlsec1'
    CERTS_DIR = os.path.join(CONFIG_DIR, 'certs')
    # ATTRIBUTE_MAP_DIR = os.path.join(CONFIG_DIR, 'attribute-maps')
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

    # Change Email/UserName/FirstName/LastName to corresponding SAML2 userprofile attributes.
    SAML_ATTRIBUTE_MAPPING = {
        'uid': ('username', ),
        'mail': ('email', ),
        'givenName': ('first_name', ),
        'sn': ('last_name', ),
    }

    # SAML_ATTRIBUTE_MAPPING = {
    #     'urn:oid:0.9.2342.19200300.100.1.1': ('username', ),
    #     'urn:oid:0.9.2342.19200300.100.1.3': ('email', ),
    #     'urn:oid:2.5.4.42': ('first_name', ),
    #     'urn:oid:2.5.4.4': ('last_name', ),
    # }

    SAML_LOGOUT_REQUEST_PREFERRED_BINDING = saml2.BINDING_HTTP_POST

    SAML_CONFIG = {
        # full path to the xmlsec1 binary programm
        # 'xmlsec_binary': XMLSEC_BINARY,

        'allow_unknown_attributes': True,

        # your entity id, usually your subdomain plus the url to the metadata view
        'entityid': SP_SERVICE_URL + '/saml2/metadata/',

        # directory with attribute mapping
        # 'attribute_map_dir': ATTRIBUTE_MAP_DIR,

        # this block states what services we provide
        'service': {
            # we are just a lonely SP
            'sp': {
                'name': 'Federated ESSArch Service',
                'name_id_format': saml2.saml.NAMEID_FORMAT_TRANSIENT,


                # For Okta add signed logout requests. Enable this:
                'logout_requests_signed': True,

                'endpoints': {
                    # url and binding to the assetion consumer service view
                    # do not change the binding or service name
                    'assertion_consumer_service': [
                        (SP_SERVICE_URL + '/saml2/acs/',
                         saml2.BINDING_HTTP_POST),
                    ],
                    # url and binding to the single logout service view
                    # do not change the binding or service name
                    'single_logout_service': [
                        # (SP_SERVICE_URL + '/saml2/ls/',
                        #  saml2.BINDING_HTTP_REDIRECT),
                        (SP_SERVICE_URL + '/saml2/ls/post/',
                         saml2.BINDING_HTTP_POST),
                    ],
                },

                'signing_algorithm': saml2.xmldsig.SIG_RSA_SHA256,
                'digest_algorithm': saml2.xmldsig.DIGEST_SHA256,

                # Mandates that the identity provider MUST authenticate the
                # presenter directly rather than rely on a previous security context.
                'force_authn': False,

                # Enable AllowCreate in NameIDPolicy.
                'name_id_format_allow_create': False,

                # attributes that this project need to identify a user
                'required_attributes': [
                    "uid",  # urn:oid:0.9.2342.19200300.100.1.1
                    # "sAMAccountName",
                    # "eduPersonPrincipalName",  # urn:oid:1.3.6.1.4.1.5923.1.1.1.6
                    # "UserName",
                    "givenName",  # urn:oid:2.5.4.42
                    "sn",  # urn:oid:2.5.4.4
                    "mail",  # urn:oid:0.9.2342.19200300.100.1.3
                ],

                # attributes that may be useful to have but not required
                # 'optional_attributes': ['eduPersonAffiliation'],

                'want_response_signed': False,
                'authn_requests_signed': True,
                'logout_requests_signed': True,
                # Indicates that Authentication Responses to this SP must
                # be signed. If set to True, the SP will not consume
                # any SAML Responses that are not signed.
                'want_assertions_signed': True,

                'only_use_keys_in_metadata': True,

                # When set to true, the SP will consume unsolicited SAML
                # Responses, i.e. SAML Responses for which it has not sent
                # a respective SAML Authentication Request.
                'allow_unsolicited': False,

                # in this section the list of IdPs we talk to are defined
                'idp': {
                    # we do not need a WAYF service since there is
                    # only an IdP defined here. This IdP should be
                    # present in our metadata

                    # the keys of this dictionary are entity ids
                    IDP_SERVICE_URL + '/federationmetadata/2007-06/federationmetadata.xml': {
                        'single_sign_on_service': {
                            saml2.BINDING_HTTP_REDIRECT: IDP_SERVICE_URL + '/adfs/ls/idpinitiatedsignon.aspx',
                        },
                        'single_logout_service': {
                            saml2.BINDING_HTTP_REDIRECT: IDP_SERVICE_URL + '/adfs/ls/?wa=wsignout1.0',
                        },
                    },
                },
            },
        },

        # where the remote metadata is stored
        # Open https://fs.essarch.local/federationmetadata/2007-06/federationmetadata.xml
        # Save this xml file, rename it to idp_federation_metadata.xml
        'metadata': {
            'local': [os.path.join(CERTS_DIR, 'idp_federation_metadata.xml')],
        } if ENABLE_ADFS_LOGIN else {},

        # set to 1 to output debugging information
        'debug': 1,

        # Signing
        # private key
        'key_file': os.path.join(CERTS_DIR, 'saml2_essarch.key'),
        # cert
        'cert_file': os.path.join(CERTS_DIR, 'saml2_essarch.crt'),

        # Encryption
        'encryption_keypairs': [{
            # private key
            'key_file': os.path.join(CERTS_DIR, 'saml2_essarch.key'),
            # cert
            'cert_file': os.path.join(CERTS_DIR, 'saml2_essarch.crt'),
        }],
        # own metadata settings
        'contact_person': [
            {'given_name': 'Henrik',
             'sur_name': 'Ek',
             'company': 'ES Solutions AB',
             'email_address': 'henrik@essolutions.se',
             'contact_type': 'technical'},
        ],
        # you can set multilanguage information here
        'organization': {
            'name': [('ES Solutions AB', 'en')],
            'display_name': [('ESS', 'en')],
            'url': [('https://www.essolutions.se', 'en')],
        },
        'valid_for': 24,  # how long is our metadata valid
    }

    LOGGING_SAML2 = {
        'handlers': {
            'log_file_auth_saml2': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'verbose',
                'filename': os.path.join(LOGGING_DIR, 'auth_saml2.log'),
                'maxBytes': 1024 * 1024 * 100,  # 100MB
                'backupCount': 5,
            },
        },
        'loggers': {
            'djangosaml2': {
                'level': 'INFO',
                'handlers': ['log_file_auth_saml2'],
                'propagate': True,
            },
            'saml2': {
                'level': 'INFO',
                'handlers': ['log_file_auth_saml2'],
                'propagate': True,
            },
        },
    }
# ### END ADFS ###

# INSTALLED_APPS.append('axes')
# AUTHENTICATION_BACKENDS.insert(0, 'axes.backends.AxesStandaloneBackend')
# MIDDLEWARE.append('axes.middleware.AxesMiddleware')

# MIDDLEWARE.append('django_auto_logout.middleware.auto_logout')
# AUTO_LOGOUT = {
#     'IDLE_TIME': 30,
#     'REDIRECT_TO_LOGIN_IMMEDIATELY': True,
# }
