from rest_framework.routers import DynamicRoute, Route
from rest_framework_extensions.routers import ExtendedDefaultRouter

from ESSArch_Core.ip.views import InformationPackageViewSet


class ESSArchRouter(ExtendedDefaultRouter):
    def get_lookup_regex(self, viewset):
        if issubclass(viewset, InformationPackageViewSet):
            return (
                r'(?:(?P<lookup_type>id|oid)/)?'
                r'(?P<pk>[^/]+)'
            )

        return super().get_lookup_regex(viewset)

    routes = [
        # List route.
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'head': 'list',
                'get': 'list',
                'post': 'create'
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        # Dynamically generated list routes. Generated using
        # @action(detail=False) decorator on methods of the viewset.
        DynamicRoute(
            url=r'^{prefix}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={}
        ),
        # Detail route.
        Route(
            url=r'^{prefix}/{lookup}{trailing_slash}$',
            mapping={
                'head': 'list',
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated detail routes. Generated using
        # @action(detail=True) decorator on methods of the viewset.
        DynamicRoute(
            url=r'^{prefix}/{lookup}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        ),
    ]


class ESSArchRouterWithoutTrailingSlash(ExtendedDefaultRouter):
    def get_lookup_regex(self, viewset):
        if issubclass(viewset, InformationPackageViewSet):
            return (
                r'(?:(?P<lookup_type>id|oid)/)?'
                r'(?P<pk>[^/]+)'
            )

        return super().get_lookup_regex(viewset)

    routes = [
        # List route.
        Route(
            url=r'^{prefix}$',
            mapping={
                'head': 'list',
                'get': 'list',
                'post': 'create'
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'}
        ),
        # Dynamically generated list routes. Generated using
        # @action(detail=False) decorator on methods of the viewset.
        DynamicRoute(
            url=r'^{prefix}/{url_path}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={}
        ),
        # Detail route.
        Route(
            url=r'^{prefix}/{lookup}$',
            mapping={
                'head': 'list',
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated detail routes. Generated using
        # @action(detail=True) decorator on methods of the viewset.
        DynamicRoute(
            url=r'^{prefix}/{lookup}/{url_path}$',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={}
        ),
    ]
