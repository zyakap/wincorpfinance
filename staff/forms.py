from django import forms
from accounts.models import UserProfile, SMEProfile
from loan.models import Loan, LoanFile
from .widgets import DatePickerInput

class MemberInfoForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields =['first_name','middle_name', 'last_name', 'gender', 'date_of_birth', 'email', 'mobile1']
        
        widgets = {
            'date_of_birth' : DatePickerInput(), }
   
class PersonalInfoForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields =['first_name','middle_name', 'last_name', 'gender', 'date_of_birth', 'marital_status', 'propic']
        
        widgets = {
            'date_of_birth' : DatePickerInput(), }
      
class ContactInfoForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields = ['email', 'mobile1', 'mobile2']
      
class BankAccountInfoForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields = ['bank','bank_account_name','bank_account_number','bank_branch',]
        
class UserUploadForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields = ['nid', 'nid_number', 'passport','passport_number', 'drivers_license', 'drivers_license_number', 'superid', 'super_member_code' ]
        
class SMEProfileForm(forms.ModelForm):
    
    class Meta:
        model = SMEProfile
        fields = ['category','trading_name','registered_name', 'business_address', 'email', 'phone', 'website' ,'ipa_registration_number', 'tin_number' ]

class CreateSMEProfileForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(CreateSMEProfileForm, self).__init__(*args, **kwargs)
        self.fields['owner'].queryset = UserProfile.objects.filter(activation=1)

    class Meta:
        model = SMEProfile
        fields = ['owner', 'category','trading_name','registered_name', 'business_address', 'email', 'phone', 'website' ,'ipa_registration_number', 'tin_number' ]

class SMEUploadsForm(forms.ModelForm):
    
    class Meta:
        model = SMEProfile
        fields = ['ipa_certificate', 'tin_certificate', 'cash_flow', 'sme_bank_statement', 'location_pic' ]

class SMEBankInfoForm(forms.ModelForm):
    
    class Meta:
        model = SMEProfile
        fields = ['bank','bank_account_name','bank_account_number','bank_branch','bank_standing_order']

class LoanStatementUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['loan_statement1', 'loan_statement2', 'loan_statement3', 'bank_statement', 'super_statement', 'bank_standing_order' ]

        
class EmployerInfoUpdateForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields = ['sector','employer', 'office_address','work_phone', 'work_email']
        
class AddressInfoForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields = ['mobile1', 'mobile2', 'resident_owner', 'residential_address', 'residential_province', 'place_of_origin', 'province']

class RequiredUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['application_form' , 'terms_conditions', 'stat_dec', 'irr_sd_form']
           
class WorkUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['work_confirmation_letter', 'payslip1', 'payslip2', ]
    
class JobInfoUpdateForm(forms.ModelForm):
    
    class Meta:
        model = UserProfile
        fields = ['job_title', 'start_date', 'pay_frequency', 'last_paydate', 'gross_pay', 'work_id_number', 'work_id',]
        
        widgets = {
            'start_date' : DatePickerInput(),
            'last_paydate' : DatePickerInput(),}   

class CreateLoanForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(CreateLoanForm, self).__init__(*args, **kwargs)
        self.fields['owner'].queryset = UserProfile.objects.filter(activation=1)
    
    class Meta:
        model = Loan
        fields = ['owner','location', 'amount','number_of_fortnights','repayment_start_date']
        
        widgets = {
            'repayment_start_date' : DatePickerInput(), }
        
class UploadRequirementsByStaffForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['application_form' , 'terms_conditions', 'stat_dec', 'irr_sd_form', 'work_confirmation_letter', 'payslip1', 'payslip2', 'loan_statement1', 'loan_statement2', 'loan_statement3', 'bank_statement', 'super_statement', 'bank_standing_order',]


class ReceiptUploadForm(forms.ModelForm):
    
    class Meta:
        model = LoanFile
        fields = ['funding_receipt', ]