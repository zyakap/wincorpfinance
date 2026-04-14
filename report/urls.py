from django.urls import path
from . import views

urlpatterns = [
    path('view_report/', views.view_reports, name='view_reports'),
    path('overview/', views.report_overview, name='report_overview'),
    path('monthly_collections_report/', views.monthly_collections_report, name='monthly_collections_report'),
    path('cash-flow/', views.cash_flow, name='cash_flow'),
]
