
from django import forms
from django.conf import settings
from loan.models import Loan, LoanFile, Payment, PaymentUploads
from .widgets import DatePickerInput


class LoanApplicationForm(forms.ModelForm):
    
    #repayment_start_date = forms.DateField(widget=forms.SelectDateWidget())
    
    class Meta:
        model = Loan
        fields = ("amount", "number_of_fortnights", "repayment_start_date")

        widgets = {
            'repayment_start_date' : DatePickerInput(), }
        
class PaymentForm(forms.ModelForm):
    
    class Meta:
        model = Payment
        fields = ('date', 'amount', 'mode', 'statement')
        
        widgets = {
            'date': DatePickerInput(),
        }

class PaymentUploadForm(forms.ModelForm):

    class Meta:
        model = PaymentUploads
        fields = ("payment_proof","type")


class RequiredUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['application_form', 'terms_conditions', 'stat_dec', 'irr_sd_form',]

class LoanStatementUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['bank_statement', 'loan_statement1', 'loan_statement2', 'loan_statement3',  'super_statement', 'bank_standing_order']

class WorkUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['work_confirmation_letter', 'payslip1', 'payslip2',]

class ReceiptUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['funding_receipt',]

