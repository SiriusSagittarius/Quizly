from django.urls import path

from auth_app.api.views import (
    CookieTokenRefreshView,
    LoginView,
    RegistrationView,
)

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path(
        'token/refresh/',
        CookieTokenRefreshView.as_view(),
        name='token-refresh',
    ),
]
