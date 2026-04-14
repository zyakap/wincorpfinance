from django.urls import path
from . import views

urlpatterns = [
    path('profiles/', views.userprofiles, name='userprofiles'),
    path('loans/', views.allloans, name='allloans'),
    path('statements/', views.statements, name='statements'),
]