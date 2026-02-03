from django.urls import path
from .views import receive_audit, dashboard, devices_json
from .views import download_inventory_json, download_device_json

urlpatterns = [
    path("audit/", receive_audit, name="receive_audit"),
    path("devices/", devices_json),
    path("", dashboard, name="dashboard"),
    path("download/json/", download_inventory_json),
    path("download/device/<str:device_hash>/", download_device_json),
]
