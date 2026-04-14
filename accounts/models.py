
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.forms import DecimalField, FileField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django.db import models
from admin1.models import Location

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, is_active=False, is_staff=False, is_admin=False, is_superuser=False, is_confirmed=False, is_defaulted=False, is_suspended=False, is_dcc_flagged=False, is_cdb_flagged=False):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.active = is_active
        user.staff = is_staff
        user.admin = is_admin
        user.is_superuser = is_superuser
        user.confirmed = is_confirmed
        user.defaulted = is_defaulted
        user.suspended = is_suspended
        user.dcc_flagged = is_dcc_flagged
        user.cdb_flagged = is_cdb_flagged
        user.save(using=self._db)
        return user

    def create_staffuser(self, email, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.staff = True
        user.admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    active = models.BooleanField(default=False)
    staff = models.BooleanField(default=False) # a admin user; non super-user
    admin = models.BooleanField(default=False) # a superuser
    updated_at = models.DateTimeField(auto_now=True)
    confirmed = models.BooleanField(default=False)
    defaulted = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    dcc_flagged = models.BooleanField(default=False)
    cdb_flagged = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    
    objects = UserManager()
    
    # notice the absence of a "Password field", that is built in.

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] # Email & Password are required by default.

    def __str__(self):
        return self.email
    
    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        return self.staff

    @property
    def is_admin(self):
        "Is the user a admin member?"
        return self.admin

    @property
    def is_confirmed(self):
        return self.is_confirmed
    
    @property
    def is_defaulted(self):
        return self.defaulted

    @property
    def is_suspended(self):
        return self.suspended
    
    @property
    def is_dcc_flagged(self):
        return self.dcc_flagged

    @property
    def is_cdb_flagged(self):
        return self.cdb_flagged

    def email_user(self, *args, **kwargs):
        send_mail(
        '{}'.format(args[0]),
        '{}'.format(args[1]),
        'dev@webmasta.com.pg',
        [self.email],
        fail_silently=False,
    )

class UserProfile(models.Model):
    PROVINCE = [('AROB','AROB'),('CENTRAL','CENTRAL'),('ENGA','ENGA'),('EAST SEPIK','EAST SEPIK'),('EHP','EHP'),('ENB','ENBP'),
    ('HELA','HELA'), ('JIWAKA','JIWAKA'),('MADANG','MADANG'),('MANUS','MANUS'),('MILNE BAY','MILNE BAY'),('MOROBE', 'MOROBE'),('NCD','NCD'),('NEW IRELAND','NEW IRELAND'),('ORO','ORO'),
    ('SHP','SHP'),('SIMBU','SIMBU'), ('WESTERN','WESTERN'), ('WEST SEPIK','WEST SEPIK'), ('WHP','WHP'), ('WNB','WNBP'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uid = models.CharField(max_length=20,null=True, blank=True)
    luid = models.CharField(max_length=20,null=True, blank=True)
    propic = models.FileField('Profile Photo:',null=True, blank=True)
    propic_url = models.CharField(max_length=555, null=True, blank=True)
    category = models.CharField(max_length=12, choices=[('CUSTOMER','CUSTOMER'), ('STAFF','STAFF')], default='CUSTOMER', null=True, blank=True)
    type_of_customer = models.CharField(max_length=12, choices=[('INDIVIDUAL','INDIVIDUAL'),('COMPANY','COMPANY')], default='INDIVIDUAL', null=True, blank=True)
    activation = models.IntegerField(null=True, blank = True, default=0)
    number_of_loans = models.IntegerField(null=True, blank = True, default=0)
    credit_rating = models.DecimalField(max_digits=5, decimal_places=2, null=True, default=100.00)
    alesco_paycode = models.CharField(max_length=20, null=True, blank=True)
    personal_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, default=0.00)
    credit_consent = models.CharField(max_length=3, choices=[('NO','NO'),('YES','YES')], default='NO', null=True, blank=True)
    terms_consent = models.CharField(max_length=3, choices=[('NO','NO'),('YES','YES')], default='NO', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    login_timestamp =  models.DateTimeField(null=True, blank = True)
    first_name = models.CharField(max_length=20)
    middle_name = models.CharField(max_length=20, null=True, blank=True)
    last_name = models.CharField(max_length=20)
    gender = models.CharField(max_length=6, choices=[('MALE','MALE'),('FEMALE','FEMALE')], default='', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    marital_status = models.CharField(max_length=10, choices=[('SINGLE','SINGLE'),('MARRIED','MARRIED'),('DE-FACTO','DE-FACTO'),('DIVORCED','DIVORCED'),('WIDOWED','WIDOWED')], default='', null=True, blank=True)
    
    #contact
    email = models.EmailField(null=True, blank=True)
    mobile1 = models.IntegerField(null=True, blank = True)
    mobile2 = models.IntegerField(null=True, blank = True)
    work_phone = models.IntegerField(blank = True, null=True)
    work_email = models.EmailField(verbose_name='Work Email Address', max_length=50, unique=True, blank = True, null=True)
    
    #personal_ID
    nid = models.FileField(null=True, blank=True)
    nid_number = models.CharField(max_length=20, null=True, blank=True)
    nid_url = models.CharField(max_length=555, null=True, blank=True)
    passport = models.FileField(null=True, blank=True)
    passport_number = models.CharField(max_length=20, null=True, blank=True)
    passport_url = models.CharField(max_length=555, null=True, blank=True)
    drivers_license = models.FileField(null=True, blank=True)
    drivers_license_number = models.CharField(max_length=20, null=True, blank=True)
    drivers_license_url = models.CharField(max_length=555, null=True, blank=True)
    superid = models.FileField(null=True, blank=True)
    super_member_code = models.CharField(max_length=20, null=True, blank=True)
    super_id_url = models.CharField(max_length=555, null=True, blank=True)
    
    #personal_info
    residential_address = models.TextField(max_length=255, null=True, blank=True)
    residential_province = models.CharField(max_length=20, choices=PROVINCE, null=True, blank=True, default="Not Specified")
    place_of_origin = models.TextField(max_length=255, null=True, blank=True)
    province = models.CharField('Province of Origin', max_length=20, choices=PROVINCE, null=True, blank=True, default="Not Specified")
    resident_owner = models.CharField(max_length=10, choices=[('SELF','SELF'),('RELATIVES','RELATIVES'),('RENTAL','RENTAL')], default='',null=True, blank=True)
    
    #employer information
    sector  = models.CharField(max_length=10, choices=[('PUBLIC','PUBLIC'),('PRIVATE','PRIVATE'),('SOE','SOE'),('SME','SME')], default='NA', null=True, blank=True)
    employer = models.CharField(max_length=50,null=True, blank=True, default='')
    job_title = models.CharField(max_length=255,null=True, blank=True, default='')
    office_address = models.TextField(max_length=255, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    pay_frequency = models.CharField(max_length=2, choices=[('FN','FORTNIGHTLY'),('MN','MONTHLY')], default='FN', null=True, blank=True)
    last_paydate = models.DateField(null=True, blank=True)
    gross_pay = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True, default=0)
    
    work_id_number = models.CharField(max_length=20, null=True, blank=True)
    work_id = models.FileField(null=True, blank=True)
    work_id_url = models.CharField(max_length=555, null=True, blank=True)
    
    #bankaccount info
    bank = models.CharField(max_length=10, choices=[('BSP', 'BSP'),('KINA','KINA'),('WESTPAC','WESTPAC')], default='', null=True, blank=True)
    bank_account_name =  models.CharField(max_length=100, null=True, blank=True, default='')
    bank_account_number = models.CharField(max_length=30,null=True, blank = True)
    bank_branch = models.CharField(max_length=30,null=True, blank = True, default='')
   
    repayment_limit = models.DecimalField(verbose_name="Borrower's Limit:", max_digits=8, decimal_places=2, null=True, blank=True, default=0)
    account_requirements_check = models.CharField(max_length=10, choices=[('COMPLETED', 'COMPLETED'),('INCOMPLETE','INCOMPLETE')], default='INCOMPLETE', null=True, blank=True)
    requirement_check = models.CharField(max_length=10, choices=[('COMPLETED', 'COMPLETED'),('INCOMPLETE','INCOMPLETE')], default='INCOMPLETE', null=True, blank=True)
    
    has_loan = models.BooleanField(default=False)
    has_sme = models.BooleanField(default=False)
    in_recovery = models.BooleanField(default=False)
    location = models.ForeignKey(Location, on_delete=models.CASCADE ,null=True, blank=True)
    
    default_flagged = models.BooleanField(default=False)
    dcc_flagged = models.BooleanField(default=False)
    has_arrears = models.BooleanField(default=False)
    dcc = models.CharField(max_length=255,null=True, blank = True, default='')
    modeofregistration = models.CharField(max_length=10, choices=[('SR', 'SR'),('OTC','OTC'),('PU','PU')], default='SR', null=True, blank=True)
    
    opt1 = models.CharField(max_length=255, blank=True, null=True)
    opt2 = models.CharField(max_length=255, blank=True, null=True)
    opt3 = models.CharField(max_length=255, blank=True, null=True)
    opt4 = models.CharField(max_length=255, blank=True, null=True)
    opt5 = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class StaffProfile(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)   
    
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    login_timestamp =  models.DateTimeField(null=True, blank = True)
    sid = models.CharField(max_length=12,null=True, blank=True)
    type_of_staff = models.CharField(max_length=12, choices=[('STAFF','STAFF'),('ADMIN','ADMIN'),('DIRECTOR','DIRECTOR')], default='STAFF', null=True, blank=True)
    category = models.CharField(max_length=12, choices=[('FULL-TIME','FULL-TIME'),('PART-TIME','PART-TIME'), ('GRADUATE','GRADUATE'), ('CONTRACTOR','CONTRACTOR')], default='FULL-TIME', null=True, blank=True)
    position_group = models.CharField(max_length=12, choices=[('WORKER','WORKER'),('SUPERVISOR','SUPERVISOR'), ('MANAGER','MANAGER')], default='', null=True, blank=True)
    position = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'

class SMEProfile(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    ref = models.CharField(max_length=20, null=True, blank=True, default='')
    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE ,null=True, blank=True)
    category = models.CharField(max_length=20, choices=[('SOLE TRADER','SOLE TRADER'),('SME','SME'),('MSME','MSME')], default='nonmember', null=True, blank=True)
    trading_name =  models.CharField(max_length=255, null=True, blank=True, default='')
    registered_name = models.CharField(max_length=255, null=True, blank=True, default='') 
    
    business_address = models.CharField(max_length=255, null=True, blank=True, default='')
    email = models.EmailField(null=True, blank = True)
    phone = models.CharField(max_length=10, null=True, blank=True, default='')
    website = models.CharField(max_length=100, null=True, blank=True, default='')
    
    ipa_registration_number = models.CharField(max_length=20, null=True, blank=True)
    ipa_certificate = models.FileField(null=True, blank=True)
    ipa_certificate_url = models.CharField(max_length=555, null=True, blank=True)
    tin_number = models.CharField(max_length=20, null=True, blank=True)
    tin_certificate = models.FileField(null=True, blank=True)
    tin_certificate_url = models.CharField(max_length=555, null=True, blank=True)
    cash_flow = models.FileField(null=True, blank=True)
    cash_flow_url = models.CharField(max_length=555, null=True, blank=True)
    sme_bank_statement = models.FileField(null=True, blank=True)
    sme_bank_statement_url = models.CharField(max_length=555, null=True, blank=True)
    location_pic = models.FileField(verbose_name="Picture of Business Location", null=True, blank=True)
    location_pic_url = models.CharField(max_length=555, null=True, blank=True)
        
    #Sme bankaccount info
    bank = models.CharField(max_length=255, choices=[('BSP', 'BSP'),('KINA','KINA'),('WESTPAC','WESTPAC')], default='', null=True, blank=True)
    bank_account_name =  models.CharField(max_length=100, null=True, blank =True, default='')
    bank_account_number = models.IntegerField(null=True, blank = True)
    bank_branch = models.CharField(max_length=30,null=True, blank = True, default='')
    bank_standing_order = models.FileField(null=True, blank=True)
    bank_standing_order_url = models.CharField(max_length=555, null=True, blank=True)

    dcc_comment = models.CharField(max_length=255,null=True, blank = True, default='')
    cdb_comment = models.CharField(max_length=255,null=True, blank = True, default='')
    notes = models.TextField(max_length=255, null=True, blank=True)
    
class UserActivityLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    msgq = models.CharField(max_length=255, blank=True, null=True, default="")
    msglog = models.CharField(max_length=1555, blank=True, null=True, default="")
    msgbyemail = models.CharField(max_length=1555, blank=True, null=True, default="")
    supportq = models.CharField(max_length=255, blank=True, null=True, default="")
    supportlog = models.CharField(max_length=1555, blank=True, null=True, default="")
    notificationq = models.CharField(max_length=255, blank=True, null=True, default="")
    notificationlog = models.CharField(max_length=1555, blank=True, null=True, default="")
    last_login = models.DateTimeField(blank=True, null=True)
    loginlog = models.CharField(max_length=1555, blank=True, null=True, default="")