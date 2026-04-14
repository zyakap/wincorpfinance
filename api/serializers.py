from rest_framework import serializers
from accounts.models import UserProfile
from loan.models import Loan, Statement

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'uid', 'luid',  'type_of_customer',  
            'number_of_loans', 'credit_rating', 
            'first_name', 'middle_name', 'last_name', 'gender', 
            'date_of_birth', 'marital_status', 
            'email', 'mobile1',  'nid_number', 
             'passport_number', 'drivers_license_number', 'super_member_code', 
            'residential_address', 'place_of_origin', 'repayment_limit', 
            'has_loan',  'dcc_flagged', 
            
        ]

class LoanSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Loan
        fields = ['ref', 'uid', 'luid', 'amount', 'repayment_amount', 'category', 'funded_category', 'status', 'funding_date', 'number_of_repayments', 'last_repayment_amount', 'last_repayment_date', 'number_of_defaults', 'last_default_date', 'last_default_amount', 'days_in_default', 'total_arrears', 'total_outstanding', 'aging_category' ]

class StatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statement
        fields = ['ref', 'uid', 'luid', 'loanref', 'date', 'statement', 'credit', 'debit', 'balance']