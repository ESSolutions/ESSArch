=================================
 Authentication and authorization
=================================

Access to information and actions are dictated by permissions assigned to the
user either directly or through groups and roles. ESSArch is designed such that
each user has a single account which are reused across multiple organizations
(groups) with different roles.

This means that a single user can have the role admin in one organization, an
archivist in another and both in a third.

ESSArch has no requirement that any specific groups or roles are setup or used
in an installation, this is all setup and configured according to the needs
that the installation is supposed to meet.

The permissions available are therefore made in as small building blocks as
possible to allow either very small and specific roles to be created but tat
the same time create roles that can do everything.


.. toctree::
    :maxdepth: 2

    groups
    permissions/index
    roles
