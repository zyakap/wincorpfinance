from django import forms
from admin1.models import AdminSettings

class AdminSettingsForm(forms.ModelForm):
    
    class Meta:
        model = AdminSettings
        fields = ("interest_type", "interest_rate","loanref_prefix","admin_email_addresses","default_from_email", "support_email", "credit_check", "approval_credit_threshold", "percentage_of_gross", "processing_fee", "processing_amount")