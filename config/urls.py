"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from apps.users.api.v1.views import CustomTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/tomadores/', include('apps.tomadores.api.v1.urls')),
    path('api/v1/users/', include('apps.users.api.v1.urls')),
    path('api/v1/corretores/', include('apps.corretores.api.v1.urls')),
    path('api/v1/segurados/', include('apps.segurados.api.v1.urls')),
    path('api/v1/produtores/', include('apps.produtores.api.v1.urls')),
    path('api/v1/seguradoras/', include('apps.seguradoras.api.v1.urls')),
    path('api/v1/modalidades/', include('apps.modalidades.api.v1.urls')),
    path('api/v1/alterar-senha/', include('apps.alterar_senha.api.v1.urls')),
    path('api/v1/atividades/', include('apps.atividades.urls')),
]
