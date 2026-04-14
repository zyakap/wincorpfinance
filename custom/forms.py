from django import forms
from accounts.models import UserProfile, SMEProfile
from loan.models import Loan, LoanFile
from .widgets import DatePickerInput



class AddAdditionalLoanForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(AddAdditionalLoanForm, self).__init__(*args, **kwargs)
        self.fields['owner'].queryset = UserProfile.objects.filter(activation=1)
    
    class Meta:
        model = Loan
        fields = ['owner','location', 'amount', 'funding_date', 'number_of_fortnights','repayment_start_date']
        
        widgets = {
            'funding_date' : DatePickerInput(), 
            'repayment_start_date' : DatePickerInput()}

class AddNewLoanForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(AddNewLoanForm, self).__init__(*args, **kwargs)
        self.fields['owner'].queryset = UserProfile.objects.filter(activation=1)
    
    class Meta:
        model = Loan
        fields = ['owner','location', 'amount', 'funding_date', 'number_of_fortnights','repayment_start_date','total_outstanding']
        
        widgets = {
            'funding_date' : DatePickerInput(), 
            'repayment_start_date' : DatePickerInput()
            }   
