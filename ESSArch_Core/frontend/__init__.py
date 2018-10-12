from django.conf import settings
from django.shortcuts import redirect, render, reverse

default_app_config = 'ESSArch_Core.frontend.apps.FrontendConfig'


def home(req):
    if req.GET.get('ref') != 'logout' and not req.user.is_authenticated:
        if getattr(settings, 'ENABLE_ADFS_LOGIN', False):
            return redirect(reverse('saml2:saml2_login'))

    return render(req, 'essarch_core_frontend/main.html')
