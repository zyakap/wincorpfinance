from django.urls import path, re_path
from . import views
from loan.views import staff_enter_payment

urlpatterns = [
    
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('adduser/', views.add_user, name='add_user'),
    path('userloans/', views.userloans, name='userloans'),
    path('userstatements/', views.userstatements, name='userstatements'),
    path('usermembers/', views.usermembers, name='usermembers'),
    path('usersmes/', views.usersmes, name='usersmes'),
    path('add_sme_profile/', views.add_sme_profile, name='add_sme_profile'),
    path('view_member/<int:uid>/', views.view_member, name='view_member'),
    path('edit_personalinfo_staff/<int:uid>/', views.edit_personalinfo_staff, name='edit_personalinfo_staff'),
    path('edit_bankinfo_staff/<int:uid>/', views.edit_bankinfo_staff, name='edit_bankinfo_staff'),
    path('edit_bankinfo2_staff/<int:uid>/', views.edit_bankinfo2_staff, name='edit_bankinfo2_staff'),
    path('edit_addressinfo_staff/<int:uid>/', views.edit_addressinfo_staff, name='edit_addressinfo_staff'),
    path('edit_useruploads_staff/<int:uid>/', views.edit_useruploads_staff, name='edit_useruploads_staff'),
    path('edit_work_uploads_staff/<int:uid>/', views.edit_work_uploads_staff, name='edit_work_uploads_staff'),
    path('edit_required_uploads_staff/<int:uid>/', views.edit_required_uploads_staff, name='edit_required_uploads_staff'),
    #sme profile
    #sme profile
    path('view_sme_profile_staff/<int:smid>/', views.view_sme_profile_staff, name='view_sme_profile_staff'),
    path('edit_sme_profile_staff/<int:uid>/', views.edit_sme_profile_staff, name='edit_sme_profile_staff'),
    path('edit_sme_profile_bank_staff/<int:uid>/', views.edit_sme_profile_bank_staff, name='edit_sme_profile_bank_staff'),
    path('edit_sme_profile_uploads_staff/<int:uid>/', views.edit_sme_profile_uploads_staff, name='edit_sme_profile_uploads_staff'),
    path('edit_loan_statement_uploads_staff/<int:uid>/', views.edit_loan_statement_uploads_staff, name='edit_loan_statement_uploads_staff'),
    path('edit_employerinfo_staff/<int:uid>/', views.edit_employerinfo_staff, name='edit_employerinfo_staff'),
    path('edit_jobinfo_staff/<int:uid>/', views.edit_jobinfo_staff, name='edit_jobinfo_staff'),
   
   #loan functions
   
    path('userloans/unfinished/', views.userloans_unfinished, name='userloans_unfinished'),
    path('userloans/under_review/', views.userloans_review, name='userloans_review'),
    path('userloans/pending/', views.userloans_pending, name='userloans_pending'),
    path('userloans/all/', views.userloans_all, name='userloans_all'),
    path('userloans/create/', views.create_loan, name='create_loan'),
    path('userloans/view_loan/<str:loan_ref>/', views.view_loan_staff, name='view_loan_staff'),
    path('userloans/review_loan/<str:loan_ref>/', views.review_loan, name='review_loan'),
    path('userloans/tc_upload/<str:loan_ref>/', views.tc_upload, name='tc_upload'),
    path('userloans/loan_req_matrix/', views.loan_req_matrix, name='loan_req_matrix'),
    path('usercredit/', views.usercredit, name='usercredit'),
    path('enter_payment/', staff_enter_payment, name='staff_enter_payment'),

    #imports
    path('addexistingloan/', views.add_existing_loan, name='add_existing_loan' ),
    path('addexistingstatement/', views.add_existing_loan_statement, name='add_existing_loan_statement' ),
    path('uploadstatement/loan/<str:loanref>/', views.upload_statement, name='upload_statement' ),
    path('send_repayment_reminder/', views.send_repayment_reminder, name='send_repayment_reminder'),
    path('send_loan_repayment_reminder/<str:loanref>/', views.send_loan_repayment_reminder, name='send_loan_repayment_reminder'),

    path('run_defaults/', views.run_defaults, name='run_defaults'),
    path('upload-statements/', views.add_existing_statements, name='add_existing_statements'),

    
    
]