from django.urls import path, include
from .views import SignUpView
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
]
