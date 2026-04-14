from django.urls import path
from . import views

urlpatterns = [
    path('get_loans/<str:uid>/', views.dcc_get_loans_for_client, name='dcc_get_loans_for_client'),
    path('reset-indcc/', views.reset_indcc, name='reset_indcc'),
]
