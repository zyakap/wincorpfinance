from django.contrib import admin
from .models import Loan, Statement, Payment
from import_export.admin import ImportExportModelAdmin

# Register your models here.
##admin.site.register(Loan)
##admin.site.register(Payment)
#@admin.register(Loan, Statement, Payment )
#class ViewAdmin(ImportExportModelAdmin):
#    pass


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'ref', 'owner', 'officer', 'loan_type', 'classification', 'amount', 'status', 'funding_date', 'repayment_start_date', 'expected_end_date',
    )
    list_filter = (
        'loan_type', 'classification', 'category', 'funded_category', 'status', 'repayment_frequency', 'aging_category',
    )
    search_fields = (
        'ref', 'uid', 'luid', 'owner__name', 'officer__name', 'location__name',
    )
    date_hierarchy = 'funding_date'
    readonly_fields = ('created_at', 'updated_at','application_date', 'amount')

    fieldsets = (
        ('Loan Details', {
            'fields': ('ref', 'uid', 'luid', 'existing_code', 'owner', 'officer', 'location', 'loan_type', 'classification', 'application_date')
        }),
        ('Financial Details', {
            'fields': ('amount', 'processing_fee', 'interest', 'total_loan_amount', 'repayment_frequency', 'number_of_fortnights', 'repayment_amount')
        }),
        ('Funding & Repayment', {
            'fields': ('funding_date', 'repayment_start_date', 'expected_end_date', 'repayment_dates', 'next_payment_date')
        }),
        ('Payment Tracking', {
            'fields': ('principal_loan_paid', 'interest_paid', 'default_interest_paid', 'total_paid', 'fortnights_paid', 'number_of_repayments',
                      'last_repayment_amount', 'last_repayment_date', 'number_of_advance_payments', 'last_advance_payment_date',
                      'last_advance_payment_amount', 'total_advance_payment', 'advance_payment_surplus')
        }),
        ('Default & Arrears', {
            'fields': ('number_of_defaults', 'last_default_date', 'last_default_amount', 'days_in_default', 'total_arrears')
        }),
        ('Receivables & Aging', {
            'fields': ('principal_loan_receivable', 'ordinary_interest_receivable', 'default_interest_receivable', 'total_outstanding',
                      'turnover_days', 'aging_category', 'aging_amount', 'considered_unrecoverable',
                      'principal_c_unrecoverable', 'interest_c_unrecoverable', 'recovery_date')
        }),
        ('Status & Notes', {
            'fields': ('category', 'funded_category', 'status', 'tc_agreement', 'tc_agreement_timestamp', 'dcc', 'notes')
        }),
        ('Optional Fields', {
            'fields': ('opt1', 'opt2', 'opt3', 'opt4', 'opt5')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('owner', 'officer', 'location')


# Let me know if you want any adjustments or added features! 🚀


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = (
        'ref', 'uid', 'luid', 'owner', 'loanref', 'date', 'type', 
        'debit', 'credit', 'arrears', 'balance', 
        'default_amount', 'default_interest',
        'principal_collected', 'interest_collected', 'default_interest_collected',
        'created_at', 'updated_at'
    )
    list_filter = ('type', 'date', 'owner', 'loanref')
    search_fields = ('ref', 'uid', 'luid', 'statement', 'dcc')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Info', {
            'fields': ('ref', 'uid', 'luid', 'owner', 'loanref', 'date', 'type', 's_count')
        }),
        ('Transaction Details', {
            'fields': ('statement', 'debit', 'credit', 'arrears', 'balance')
        }),
        ('Default & Collections', {
            'fields': (
                'default_amount', 'default_interest', 
                'principal_collected', 'interest_collected', 'default_interest_collected'
            )
        }),
        ('Metadata', {
            'fields': ('dcc', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        # Optimize query performance
        qs = super().get_queryset(request)
        return qs.select_related('owner', 'loanref')


# Let me know if you’d like any adjustments or custom actions! 🚀


class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'ref', 'owner', 'loanref', 'p_count', 'date', 'amount', 'type', 'mode', 'officer', 'created_at', 'updated_at'
    )
    list_filter = ('type', 'mode', 'date', 'officer')
    search_fields = ('ref', 'loanref__ref', 'owner__user__username', 'statement')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Payment Details', {
            'fields': ('ref', 'loanref', 'owner', 'officer', 'p_count', 'date', 'amount', 'type', 'mode')
        }),
        ('Additional Info', {
            'fields': ('statement', 'upload_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

admin.site.register(Payment, PaymentAdmin)

# Let me know if you want to add any custom actions or improve something! 🚀
