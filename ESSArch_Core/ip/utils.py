from django.core.cache import cache

from .models import InformationPackage

def get_cached_objid(id):
    objid_cache_name = 'object_identifier_value_%s' % id
    objid = cache.get(objid_cache_name)

    if objid is None:
        objid = InformationPackage.objects.values_list('object_identifier_value', flat=True).get(pk=id)
        cache.set(objid_cache_name, objid, 3600 * 24)

    return objid


def get_package_type(t):
    return {
        'sip': InformationPackage.SIP,
        'aic': InformationPackage.AIC,
        'aip': InformationPackage.AIP,
        'aiu': InformationPackage.AIU,
        'dip': InformationPackage.DIP,
    }[t]
