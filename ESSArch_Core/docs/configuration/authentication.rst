==============
Authentication
==============

The following keys control the authentication support.

Single Sign-On (SSO)
====================

``ESSARCH_SAML_MAPPING_BACKEND``

Python path to a SAML mapping backend.

If provided, ESSArch will use the backend during authentication through SAML to
map external attributes to internal. For example, attributes included in a SAML
response could be used to assign the user to groups and roles.

Defaults to ``None``.
