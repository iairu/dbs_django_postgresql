from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('v1/health', views.v1_health, name='v1_health'),
]