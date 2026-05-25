from dj_rest_auth.views import (
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
    UserDetailsView,
)
from django.urls import re_path
from knox import views as knox_views
from rest_framework_simplejwt.views import (  # TokenObtainPairView,; TokenRefreshView,
    TokenVerifyView,
)

from ESSArch_Core.auth.views import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    LoginView,
    LogoutView,
    TokenLoginView,
    TokenLogoutView,
    jwt_api_callback,
    login_services,
)

urlpatterns = [
    # URLs that do not require a session or valid token
    re_path(r'^password/reset/$', PasswordResetView.as_view(),
            name='rest_password_reset'),
    re_path(r'^password/reset/confirm/$', PasswordResetConfirmView.as_view(),
            name='rest_password_reset_confirm'),
    re_path(r'^login/$', LoginView.as_view(), name='rest_login'),
    re_path(r'^logout/$', LogoutView.as_view(), name='rest_logout'),
    re_path(r'^services/$', login_services, name='services'),
    re_path(r'^user/$', UserDetailsView.as_view(), name='rest_user_details'),
    re_path(r'^password/change/$', PasswordChangeView.as_view(),
            name='rest_password_change'),
    re_path(r'^token_login/$', TokenLoginView.as_view(), name='knox_login'),
    re_path(r'^token_logout/$', knox_views.LogoutView.as_view(), name='knox_logout'),
    re_path(r'^token_logoutall/$', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    # re_path(r'^token/$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    re_path(r'^token/$', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    # re_path(r'^token/refresh/$', TokenRefreshView.as_view(), name='token_refresh'),
    re_path(r'^token/refresh/$', CookieTokenRefreshView.as_view(), name='token_refresh'),
    re_path(r'^token/verify/$', TokenVerifyView.as_view(), name='token_verify'),
    re_path(r'^token/logout/$', TokenLogoutView.as_view(), name='token_logout'),
    re_path(r'^saml2/jwt-api-callback/$', jwt_api_callback, name='jwt_api_callback'),
]
