"""Torque URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from rest_framework.routers import DefaultRouter

# Creating Router Object
from models import views
from models.views import upload_data

router = DefaultRouter()
routa_api = 'api/'
# Register ViewSets with Router
router.register(routa_api + 'log', views.LogViewSet, basename='log')
router.register(routa_api + 'record', views.RecordViewSet, basename='record')
router.register(routa_api + 'sensor', views.SensorViewSet, basename='sensor')
router.register(routa_api + 'kmeans', views.KMeansViewSet, basename='KMeans')
router.register(routa_api + 'svm', views.SVMViewSet, basename='SVM')
router.register(routa_api + 'dataset', views.DatasetViewSet, basename='Dataset')
router.register(routa_api + 'prediction', views.PredictionViewSet, basename='prediction')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('upload/', upload_data)
]
