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
from models.views import upload_data, viewMap, sessions_by_id_list, session_in_map, download_csv, tracking, \
    compare_all_routes, separe_sessions

router = DefaultRouter()
router_api = 'api/'
# Register ViewSets with Router
router.register(router_api + 'log', views.LogViewSet, basename='log')
router.register(router_api + 'record', views.RecordViewSet, basename='record')
router.register(router_api + 'sensor', views.SensorViewSet, basename='sensor')
router.register(router_api + 'kmeans', views.KMeansViewSet, basename='KMeans')
router.register(router_api + 'svm', views.SVMViewSet, basename='SVM')
router.register(router_api + 'dataset', views.DatasetViewSet, basename='Dataset')
router.register(router_api + 'prediction', views.PredictionViewSet, basename='prediction')
router.register(router_api + 'datatorque', views.DataTorqueViewSet, basename='datatorque')

urlpatterns = [
    path('admin/', admin.site.urls),
    path(router_api, include(router.urls)),
    path('upload/', upload_data, name='upload'),
    path('map2/', viewMap, name='map2'),  # Need to generate geojson/kml and csv files (using 'map/session_id)'
    path('', sessions_by_id_list, name='session_list'),
    path('map/<int:session_id>/', session_in_map, name='session_map'),
    path('download/<int:session_id>/', download_csv, name='download'),
    path('track/<int:session_id>/', tracking, name='tracking'),
    path('route/<int:session_id>/', compare_all_routes, name='routes'),
    path('route/<int:session_id>/<int:percentage>/', compare_all_routes, name='routes'),
    path('separe_sessions', separe_sessions, name='separe_sessions')

]
