from django.conf import settings
from django.db import models

class AdminSettings(models.Model):
    
    settings_name = models.CharField(max_length=30, blank=True, null=True)
    loanref_prefix = models.CharField(verbose_name="Loan Reference Prefix:", max_length=5, help_text="For example, Instabuxx uses 'iBX' in front for all loan refs.", blank=True, null=True)
    admin_email_addresses = models.CharField(verbose_name="Admin Email Addresses:", max_length=250, help_text="Email Addresses that will receive system admin notifications. Enter email addresses separated by a comma. Eg: info@loanmasta.com,admin@loanmasta.com. Make sure there are no spaces after the comma", blank=True, default=settings.EMAIL_HOST_USER)
    default_from_email = models.CharField(verbose_name="Default From Email:", max_length=100, help_text="Email Address that will send all notifications to the user.", blank=True, default=settings.DEFAULT_FROM_EMAIL)
    support_email = models.CharField(verbose_name="Support Email:", max_length=100, help_text="Email Address that will receive all support requests.", blank=True, default=settings.SUPPORT_EMAIL)
    credit_check = models.CharField(verbose_name="Automatic Credit Check:", max_length=255, choices=[('NO','NO - We will decide'),('YES','YES - Automatic')], null=True, blank=True, help_text="If you set this to yes, Loan Application Decision will be made automatically based on your customer credit threshold setting.")
    
    approval_credit_threshold = models.DecimalField(verbose_name="Approval Credit Threshold:", max_digits=5, decimal_places=3, blank=True, null=True, help_text="User's with credit rating above this will have loan applications allowed if credit check is set to automatic.")
    percentage_of_gross = models.DecimalField(verbose_name="Percentage of Gross allowable:", max_digits=5, decimal_places=3, blank=True, null=True)
    interest_type = models.CharField(verbose_name="Interest Type:", max_length=255, choices=[('FIXED','FIXED'),('VARIABLE','VARIABLE'),('CUSTOM','CUSTOM')], null=True, blank=True)
    interest_rate = models.DecimalField(verbose_name="Interest Rate in Percentage:", max_digits=5, decimal_places=3, blank=True, null=True, help_text="If interest is fixed, enter standard interest, eg: 30%. If Interest is variable, enter per term interest. Eg, 1.25% per fortnight")
    processing_fee = models.CharField(verbose_name="Processing Fee:", max_length=255, choices=[('YES','YES'),('NO','NO')], null=True, blank=True, default='NO')
    processing_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    default_interest_rate = models.DecimalField(verbose_name="Default Interest Rate:", max_digits=5, decimal_places=3, blank=True, null=True, help_text="In percentage of repayment amount, say 20 for 20% of repayment amount")

class Location(models.Model):
    
    PROVINCE = [('AROB','AROB'),('CENTRAL','CENTRAL'),('ENGA','ENGA'),('EAST SEPIK','EAST SEPIK'),('EHP','EHP'),('ENB','ENBP'),
    ('HELA','HELA'), ('JIWAKA','JIWAKA'),('MADANG','MADANG'),('MANUS','MANUS'),('MILNE BAY','MILNE BAY'), ('MOROBE', 'MOROBE'),('NCD','NCD'),('NEW IRELAND','NEW IRELAND'),('ORO','ORO'),
    ('SHP','SHP'),('SIMBU','SIMBU'), ('WESTERN','WESTERN'), ('WEST SEPIK','WEST SEPIK'), ('WHP','WHP'), ('WNB','WNBP'),
    ]  
    
    name = models.CharField(max_length=255, blank=True, null=True)
    province = models.CharField(max_length=20, choices=PROVINCE)
    address = models.CharField(max_length=255, blank=True, null=True)
    email= models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.IntegerField(null=True, blank=True)
    
    loans = models.IntegerField(null=True, blank=True, default=0)
    loans_in_default = models.IntegerField(null=True, blank=True, default=0)
    
    funded = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, default=0)
    interest = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, default=0)
    repayment = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, default=0)
    arrears = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, default=0)
    outstanding = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, default=0)
    in_recovery = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, default=0)
    
    customers = models.IntegerField(null=True, blank=True, default=0)
    customers_with_loan = models.IntegerField(null=True, blank=True, default=0)
    customers_in_recovery = models.IntegerField(null=True, blank=True, default=0)
    
    def __str__(self):
        return self.name
    
    

