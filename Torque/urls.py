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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Creating Router Object
from Torque import settings
from models import views
from models.views import *

router = DefaultRouter()
router_api = 'api/'
# Register ViewSets with Router
router.register('log', views.LogViewSet, basename='log')
router.register('record', views.RecordViewSet, basename='record')
router.register('sensor', views.SensorViewSet, basename='sensor')

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path(router_api, include(router.urls)),
                  path('upload/', upload_data, name='upload'),
                  path('', sessions_by_id_list, name='session_list'),
                  path('map/<int:session_id>/', session_in_map, name='session_map'),
                  path('download/<int:session_id>/', download_csv, name='download'),
                  path('download_all_csv/', download_csv_all_sessions, name='download_all_csv'),
                  path('track/<int:session_id>/', tracking, name='tracking'),
                  path('route/<int:session_id>/', compare_all_routes, name='route'),
                  path('separe_sessions', separe_sessions, name='separe_sessions'),
                  path('track_all_sessions', tracking_all_sessions, name='tracking_all_sessions'),
                  path('export_data', export_data_to_csv, name='export_data'),
                  path('sensor_from_session/<int:session_id>/', obtain_sensors_from_session,
                       name='sensor_from_session'),
                  path('session_from_sensor/<int:sensor_id>/', obtain_sessions_from_sensor, name='session_from_sensor'),
                  path('generate_csv/', generate_custom_csv, name='generate_csv'),
                  path('generate_csv_multiple_sessions/', generate_csv_multiple_sessions,
                       name='generate_csv_multiple_sessions'),
                  path('export_sensors/', export_sensors_for_react_app, name='export_sensors'),
                  path('export_pdf/<str:filename>/', export_pdf, name="export-pdf"),

                  path('download_summary_all_sessions/', download_summary_all_sessions,
                       name='download_summary_all_sessions'),

                  path('metricas_type_sessions/', metricas_type_sessions, name='metricas_type_sessions'),

                  # AI
                  path('upload_csv/', upload_csv, name='upload_csv'),
                  path('pca/', pca_request, name='pca'),
                  path('svm/', svm_classification_request, name='svm'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
