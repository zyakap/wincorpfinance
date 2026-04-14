from django.urls import path, re_path

from admin1.mainView import (admin_settings, admin_dashboard, statements, 
                          defaults, DownloadApplicationByAdmin, create_default, DownloadLoanStatement, reports,
                          payment_uploads, support_system_admin, admin_instructions, admin_run_defaults, process_upload
                          
                        )

from admin1.views.loansView import ( loans, pending_loans, running_loans, defaulted_loans,
                          all_loans, completed_loans, recovery_loans, view_loan, approve, decline, funding_list, fund_loan, cancel_funding, funding_receipt_upload
                          
                        )

from admin1.views.transactionsView import ( transactions, transactions_all, transactions_defaults, transactions_expected, transactions_payments)

from admin1.views.customersView import (customers, customers_all, customers_withloan,customers_pending, customers_flagged, customers_suspended, view_customer, inform_account_activation, customers_pending_activation)
from admin1.views.employerView import employer_overview, loans_by_employer

from admin1.views.locationsView import (locations, locations_customers, locations_loans, locations_transactions)
from message.views import messages_admin, create_message_admin, message_drafts_admin, delivery_reports_admin, delivery_statuses_admin
from support.views import admin_view_ticket, support_tickets_admin, closed_tickets_admin, open_tickets_admin, pending_tickets_admin

urlpatterns = [
    
    path('settings/', admin_settings, name='admin_settings'),
    path('dashboard/', admin_dashboard, name='admin_dashboard'),
    path('loans/', loans, name='loans'),
    path('loans/all', all_loans, name='all_loans'),
    path('loans/pending', pending_loans, name='pending_loans'),
    path('loans/running', running_loans, name='running_loans'),
    path('loans/defaulted', defaulted_loans, name='defaulted_loans'),
    path('loans/running', running_loans, name='running_loans'),
    path('loans/completed', completed_loans, name='completed_loans'),
    path('loans/recovery', recovery_loans, name='recovery_loans'),
    path('loans/funding_list', funding_list, name='funding_list'),
    path('loans/fund_loan/<str:loanref>/', fund_loan, name='fund_loan'),
    path('loans/cancel_funding/<str:loanref>/', cancel_funding, name='cancel_funding'),

    path('admin_run_defaults/', admin_run_defaults, name="admin_run_defaults"),
   
    # from transactions view
    path('transactions/', transactions, name='transactions'),
    path('transactions/all', transactions_all, name='transactions_all'),
    path('transactions/payments', transactions_payments, name='transactions_payments'),
    path('transactions/defaults', transactions_defaults, name='transactions_defaults'),
    path('transactions/expected', transactions_expected, name='transactions_expected'),
    
    path('statements/', statements, name='statements'),
    path('defaults/', defaults, name='defaults'),
    path('messages/', messages_admin, name='messages_admin'),
    path('message/create/', create_message_admin, name='create_message_admin'),
    path('message/drafts/', message_drafts_admin, name='message_drafts_admin'),
    path('message/delivery_reports/', delivery_reports_admin, name='delivery_reports_admin'),
    path('message/delivery_statuses/', delivery_statuses_admin, name='delivery_statuses_admin'),

    path('support/tickets/', support_tickets_admin, name='support_tickets_admin'),
    path('support/tickets/pending/', pending_tickets_admin, name='pending_tickets_admin'),
    path('support/tickets/open/', open_tickets_admin, name='open_tickets_admin'),
    path('support/tickets/closed/', closed_tickets_admin, name='closed_tickets_admin'),
    path('support/tickets/view/<str:ref>/', admin_view_ticket, name='admin_view_ticket'),


    path('admin_instructions/', admin_instructions, name='admin_instructions'),
    path('process-payment/<str:ref>/', process_upload, name='process_upload'),
    
    
    
    #from locations view
    path('locations/', locations, name='locations'),
    path('locations/customers', locations_customers, name='locations_customers'),
    path('locations/loans', locations_loans, name='locations_loans'),
    path('locations/transactions', locations_transactions, name='locations_transactions'),
    
    
    #from customers view
    path('customers/', customers, name='customers'),
    path('customers/inform_customer/<int:uid>/', inform_account_activation, name='inform_account_activation'),
    path('customers/all', customers_all, name='customers_all'),
    path('customers/withloan', customers_withloan, name='customers_withloan'),
    path('customers/pending', customers_pending, name='customers_pending'),
    path('customers/pending_activation', customers_pending_activation, name='customers_pending_activation'),
    
    path('customers/flagged', customers_flagged, name='customers_flagged'),
    path('customers/suspended', customers_suspended, name='customers_suspended'),
    re_path(r'customers/view_customer/(?P<uid>[0-9]+)/$', view_customer, name='view_customer'),
    
    path('loans/<str:loan_ref>/', view_loan, name='view_loan'),
    re_path(r'^approve/([a-zA-Z]+[0-9]+[A-Z]+[0-9]+)/$', approve, name='approve'),
    path('decline/<str:loan_ref>/', decline, name='decline'),
    re_path(r'download/(?P<loanref>[a-zA-Z]+[0-9]+[A-Z]+[0-9]+)/$', DownloadApplicationByAdmin.as_view(), name="download_loan_application"),
    
    path('create-default/<str:loan_ref>/', create_default, name="create_default"),
    re_path(r'dls/(?P<loanref>[a-zA-Z]+[0-9]+[A-Z]+[0-9]+)/$', DownloadLoanStatement.as_view(), name="download_loan_statement"),
    
    path('payment_uploads/', payment_uploads, name='payment_uploads'),
    path('reports/', reports, name='reports'),
    path('loan/funding_receipt_upload/<str:loanref>/', funding_receipt_upload, name='funding_receipt_upload'),
    
    #employerView
    path('employer-overview/', employer_overview, name='employer_overview'),
    path('employer/loans/', loans_by_employer, name='loans_by_employer'),

]



#re_path(r'^loans/([a-zA-Z]+[0-9]+[A-Z]+[0-9]+)/$', view_loan, name='view_loan'),
# re_path(r'^approve/([a-zA-Z]+[0-9]+[A-Z]+[0-9]+)/$', approve, name='approve'),
 #   re_path(r'^decline/([a-zA-Z]+[0-9]+[A-Z]+[0-9]+)/$', decline, name='decline'),