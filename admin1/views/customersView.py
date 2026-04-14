import datetime
import re
import requests
from decimal import Decimal
from weakref import ref
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from pyparsing import empty
from socket import gaierror
from accounts.models import User, UserProfile, StaffProfile, SMEProfile
from loan.models import Loan, LoanFile, Statement, Payment, PaymentUploads
from loan.forms import PaymentForm
from admin1.forms import AdminSettingsForm

from django.contrib.sites.shortcuts import get_current_site

#EMAIL SETTINGS
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.html import strip_tags
#admin sender email
from admin1.models import AdminSettings, Location
sender = settings.DEFAULT_SENDER_EMAIL

#Class Based Views
from django.views.generic.base import View
from wkhtmltopdf.views import PDFTemplateResponse

from django.db.models import Sum, Q

from django.conf import settings
from accounts.functions import admin_check
from dcc.functions import check_client_in_dcc, get_loans_for_client, get_transactions_for_client
domain = settings.DOMAIN

from dcc.serializers import LoanSerializer, StatementSerializer

################ 
# START OF CODE
################

@admin_check
def customers(request):
    
    #### DEFINE CLIENT PENDING CKECK REQUIREMENT HERE:
    
    pending_users = UserProfile.objects.exclude(activation=1, requirement_check='COMPLETED')
    
    for user in pending_users:
        if user.repayment_limit != 0:
            user.requirement_check == 'COMPLETED'
            
    
    #### DEFINE CLIENT PENDING: END
    
    
    loans = Loan.objects.prefetch_related('owner').filter(owner__user__staff=0)
    
    customers = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0).all()
    
    customers_all = customers
    customers_withloan = customers.filter(number_of_loans__gt=0).all()
    customers_pending = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_flagged = customers.filter(user__dcc_flagged=1).all()
    customers_suspended = customers.filter(user__suspended=1).all()
    
    customers_with_default = customers.filter(user__defaulted=1).all()
    customers_in_recovery = customers.filter(in_recovery=1).all()
    
    
    public_ca = customers.filter(sector='PUBLIC').all()
    public_cwl = customers.filter(number_of_loans__gt=0, sector='PUBLIC').all()
    public_cwd = customers.filter(user__defaulted=1, sector='PUBLIC').all()
    public_cir = customers.filter(in_recovery=1, sector='PUBLIC').all()
    
    private_ca = customers.filter(sector='PRIVATE').all()
    private_cwl = customers.filter(number_of_loans__gt=0, sector='PRIVATE').all()
    private_cwd = customers.filter(user__defaulted=1, sector='PRIVATE').all()
    private_cir = customers.filter(in_recovery=1, sector='PRIVATE').all()
    
    married_customers = customers.filter(marital_status='MARRIED').all()
    single_customers = customers.filter(marital_status='SINGLE').all()
    other_marital_customers = customers.exclude(marital_status='SINGLE').exclude(marital_status='MARRIED').all()
    
    male_customers = customers.filter(gender='MALE').all()
    female_customers = customers.filter(gender='FEMALE').all()
    working_customers = customers.exclude(employer='NA',job_title='NA').all()
    not_working_customers = customers.filter(employer='NA',job_title='NA').all()
    with_sme_customers = customers.filter(has_sme=1).all()
    without_sme_customers = customers.filter(has_sme=0).all()

    print(not_working_customers)
    
    if customers.count() != 0:
        married = round((married_customers.count()/customers.count())*100.0, 1)
        single = round((single_customers.count()/customers.count())*100.0, 1)
        other_marital = round((other_marital_customers.count()/customers.count())*100.0, 1)
        male = round((male_customers.count()/customers.count())*100.0, 1)
        female = round((female_customers.count()/customers.count())*100.0, 1)
        working = round((working_customers.count()/customers.count())*100.0, 1)
        not_working = round((not_working_customers.count()/customers.count())*100.0, 1)
        with_sme = round((with_sme_customers.count()/customers.count())*100.0, 1)
        without_sme = round((without_sme_customers.count()/customers.count())*100.0, 1)
    else:
        married = 0
        single = 0
        other_marital = 0
        male = 0
        female = 0
        working = 0
        not_working = 0
        with_sme = 0
        without_sme = 0
    
    today = datetime.date.today() 
    
    et18 = today - datetime.timedelta(days=(18*365))
    tf24 = today - datetime.timedelta(days=(365*24))
    tf25 = today - datetime.timedelta(days=(365*24)) - datetime.timedelta(days=1)
    t30 = today - datetime.timedelta(days=(365*30))
    to31 = today - datetime.timedelta(days=(365*30)) - datetime.timedelta(days=1)
    f40 = today - datetime.timedelta(days=(365*40))
    fo41 = today - datetime.timedelta(days=(365*40)) - datetime.timedelta(days=1)
    f50 = today - datetime.timedelta(days=(365*50))
    fo51 = today - datetime.timedelta(days=(365*50)) - datetime.timedelta(days=1)
    h100 = today - datetime.timedelta(days=(365*99))
    
    customers_1824 = customers.filter(date_of_birth__gte=tf24, date_of_birth__lte=et18,)
    customers_2530 = customers.filter(date_of_birth__gte=t30, date_of_birth__lte=tf25,)
    customers_3140 = customers.filter(date_of_birth__gte=f40, date_of_birth__lte=to31,)
    customers_4150 = customers.filter(date_of_birth__gte=f50, date_of_birth__lte=fo41,)
    customers_51100 = customers.filter(date_of_birth__lte=fo51)
    
    if customers.count() != 0:
        customers_1824P = round((customers_1824.count()/customers.count())*100.0, 1)
        customers_2530P = round((customers_2530.count()/customers.count())*100.0, 1)
        customers_3140P = round((customers_3140.count()/customers.count())*100.0, 1)
        customers_4150P = round((customers_4150.count()/customers.count())*100.0, 1)
        customers_51100P = round((customers_51100.count()/customers.count())*100.0, 1) 
    else:
        customers_1824P = 0
        customers_2530P = 0
        customers_3140P = 0
        customers_4150P = 0
        customers_51100P = 0 
    
    customers_1824M = customers_1824.filter(gender="MALE")
    customers_2530M = customers_2530.filter(gender="MALE")
    customers_3140M = customers_3140.filter(gender="MALE")
    customers_4150M = customers_4150.filter(gender="MALE")
    customers_51100M = customers_51100.filter(gender="MALE")
    
    customers_1824FM = customers_1824.filter(gender="FEMALE")
    customers_2530FM = customers_2530.filter(gender="FEMALE")
    customers_3140FM = customers_3140.filter(gender="FEMALE")
    customers_4150FM = customers_4150.filter(gender="FEMALE")
    customers_51100FM = customers_51100.filter(gender="FEMALE")
    
    if customers.count() != 0:
        publicsectorpercent = round((public_ca.count()/customers.count())*100.0, 1) 
        privatesectorpercent = round((private_ca.count()/customers.count())*100.0, 1)
        nasector = 100.0 - publicsectorpercent - privatesectorpercent
    else:
        publicsectorpercent = 0 
        privatesectorpercent = 0
        nasector = 0
    
    userprovinces = customers.exclude(province='Not Specified')
    provinces = {}
    
    for user in userprovinces:
        province = user.province
        if province in provinces:
            provinces[province] += 1
        else:
            provinces[province] = 1
   
    province_label = []
    province_data = []
    province_data_count = len(provinces)
    
    for k,v in provinces.items():
        province_label.append(k)
        province_data.append(v)

    resuserprovinces = customers.exclude(residential_province='Not Specified')
    resprovinces = {}
    
    for user in resuserprovinces:
        resprovince = user.residential_province
        if resprovince in resprovinces:
            resprovinces[resprovince] += 1
        else:
            resprovinces[resprovince] = 1
   
    resprovince_label = []
    resprovince_data = []
    resprovince_data_count = len(resprovinces)
    
    for k,v in resprovinces.items():
        resprovince_label.append(k)
        resprovince_data.append(v)
    
    #customers by location 
    loccuslabel = []
    loccus = []
   
    locations = Location.objects.all()
   
    for location in locations:
        loccuscount = UserProfile.objects.filter(location=location, activation=1).exclude(category='STAFF').count()
        if loccuscount != 0:
            loccus.append(float(loccuscount))
        else:
            loccus.append(0)
            
        loccuslabel.append(f'{location.name}, {loccuscount}')
    
    context = {
        'nav' : 'customers',
        'loans': loans,
        'customers_all' : customers_all,
        'customers_withloan' : customers_withloan,
        'customers_pending': customers_pending,
        'customers_flagged' :  customers_flagged,
        'customers_suspended' : customers_suspended,
        'customers_with_default': customers_with_default,
        'customers_in_recovery':customers_in_recovery,
        'public_ca': public_ca,
        'public_cwl':public_cwl,
        'public_cwd': public_cwd,
        'public_cir':public_cir,
        'private_ca': private_ca,
        'private_cwl':private_cwl,
        'private_cwd': private_cwd,
        'private_cir':private_cir, 
        'married': married,
        'single': single,
        'other_marital': other_marital,
        'male': male,
        'female': female,
        'working': working,
        'not_working': not_working,
        'with_sme': with_sme,
        'without_sme': without_sme,
        
        'customers_1824P':customers_1824P,
        'customers_2530P':customers_2530P,
        'customers_3140P':customers_3140P,
        'customers_4150P':customers_4150P,
        'customers_51100P':customers_51100P,
        
        'customers_1824M':customers_1824M,
        'customers_2530M':customers_2530M,
        'customers_3140M':customers_3140M,
        'customers_4150M':customers_4150M,
        'customers_51100M':customers_51100M,
        
        'customers_1824FM':customers_1824FM,
        'customers_2530FM':customers_2530FM,
        'customers_3140FM':customers_3140FM,
        'customers_4150FM':customers_4150FM,
        'customers_51100FM':customers_51100FM,
        
        'publicsectorpercent': publicsectorpercent,
        'privatesectorpercent': privatesectorpercent,
        'nasector': nasector ,
        
        'province_label':province_label,
        'province_data': province_data, 
        'province_data_count': province_data_count,
        
        'resprovince_label':resprovince_label,
        'resprovince_data': resprovince_data, 
        'resprovince_data_count': resprovince_data_count,
        
        'loccuslabel': loccuslabel,
        'loccus': loccus,
    }
    
    return render(request, 'customers.html', context )


@admin_check
def customers_all(request):
    
    referrer = request.META['HTTP_REFERER']
    
    customers = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0).all()
    
    customers_all = customers
    customers_withloan = customers.filter(number_of_loans__gt=0).all()
    customers_pending = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_flagged = customers.filter(user__dcc_flagged=1).all()
    customers_suspended = customers.filter(user__suspended=1).all()
    
    if request.method=='POST':
        
        if request.POST.get('cuscat') and request.POST.get('sectype') and request.POST.get('loanopt'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')  
            loanopt = request.POST.get('loanopt')  
            
            if sectype == 'PUBLIC':
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='MEMBER')
                        
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )  
                               
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='NON-MEMBER') 
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                                
                            }
                        
                        return render(request, 'customers_all.html', context )  
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )
                    
            elif sectype == 'PRIVATE':
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='MEMBER')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )

            else:
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_all.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='MEMBER')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_all.html', context )
   
        elif request.POST.get('cuscat') and request.POST.get('sectype'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')    
            
            if sectype == 'PUBLIC':
                
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    return render(request, 'customers_all.html', context )    
                       
                elif cuscat == 'NON-MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='NON-MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                            
                        }
                    
                    return render(request, 'customers_all.html', context )  
                else:
                    customers_filtered = customers.filter(sector='PUBLIC', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )
            
            elif sectype == 'PRIVATE':
                
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='NON-MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )   
                else:
                    customers_filtered = customers.filter(sector='PRIVATE', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )
            
            else: 
               
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='NON-MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )   
                else:
                    customers_filtered = customers.filter(sector='NA', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'sectype': sectype,
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )
            
        elif request.POST.get('cuscat') and request.POST.get('loanopt'):
            
            cuscat = request.POST.get('cuscat')  
            loanopt = request.POST.get('loanopt')  
             
            if loanopt == 'withloan':
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'loanopt': 'WITH LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_all.html', context )  
                            
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                             'cuscat': cuscat, 'loanopt': 'WITH LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                            
                        }
                    
                    return render(request, 'customers_all.html', context )  
                else:
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                             'cuscat': cuscat, 'loanopt': 'WITH LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_all.html', context )
            else:
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(number_of_loans=0, category='MEMBER') 
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                             'cuscat': cuscat, 'loanopt': 'WITHOUT LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(number_of_loans=0, category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'loanopt': 'WITHOUT LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )   
                else:
                    customers_filtered = customers.filter(number_of_loans=0, category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'cuscat': cuscat, 'loanopt': 'WITHOUT LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )
        
        elif request.POST.get('sectype') and request.POST.get('loanopt'):

            sectype = request.POST.get('sectype')  
            loanopt = request.POST.get('loanopt')  
            
            if sectype == 'PUBLIC':
                
                if loanopt == 'withloan':
                        
                    customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'sectype': sectype, 'loanopt': 'WITH LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_all.html', context )  
                               
                else:
                    
                    customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )                       
                    
            elif sectype == 'PRIVATE':
                
                if loanopt == 'withloan':
                    
                    customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'sectype': sectype, 'loanopt': 'WITH LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_all.html', context )                       
                
                else:
                   
                    customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )                        
                    
            else:
                
                if loanopt == 'withloan':
                    
                    customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'sectype': sectype, 'loanopt': 'WITH LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_all.html', context )                       
                    
                else:
                    
                    customers_filtered = customers.filter(sector='NA', number_of_loans=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                            'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                            'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_all.html', context )                        

        elif request.POST.get('cuscat'):
            
            cuscat = request.POST.get('cuscat')   
                
            if cuscat == 'MEMBER':
                
                customers_filtered = customers.filter(category='MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'cuscat': cuscat,
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':customers_filtered,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                return render(request, 'customers_all.html', context )    
                    
            elif cuscat == 'NON-MEMBER':
                
                customers_filtered = customers.filter(category='NON-MEMBER') 
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'cuscat': cuscat,
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':customers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,    
                    }
                
                return render(request, 'customers_all.html', context )  
            
            else:
                customers_filtered = customers.filter(category='STAFF')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'cuscat': cuscat,
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_all.html', context )        
          
        elif request.POST.get('sectype'):

            sectype = request.POST.get('sectype')  
            
            if sectype == 'PUBLIC':
                        
                customers_filtered = customers.filter(sector='PUBLIC')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'sectype': sectype,
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':customers_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_all.html', context )                      
                    
            elif sectype == 'PRIVATE':
                    
                customers_filtered = customers.filter(sector='PRIVATE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'sectype': sectype,
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':customers_filtered,
                        'public_filtered':0,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_all.html', context )                                           
                    
            else:
                    
                customers_filtered = customers.filter(sector='NA') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'sectype': sectype,
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':0,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_all.html', context )                       
        
        elif request.POST.get('loanopt'):
  
            loanopt = request.POST.get('loanopt')  
                
            if loanopt == 'withloan':
                    
                customers_filtered = customers.filter(number_of_loans__gt=0)
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'loanopt': 'WITH LOAN',
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                
                return render(request, 'customers_all.html', context )  
                            
            else:
                
                customers_filtered = customers.filter(number_of_loans=0) 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                context = {
                        'nav' : 'customers_all', 'filter': 'on', 'referrer': referrer,
                        'loanopt': 'WITHOUT LOAN',
                        'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':0,
                        'withoutl_filtered':customers_filtered,
                    }
                
                return render(request, 'customers_all.html', context )                       
                            
    customers_filtered = customers
    members_filtered = customers.filter(category='MEMBER')  
    nonmembers_filtered = customers.filter(category='NON-MEMBER')
    private_filtered = customers.filter(sector='PRIVATE')
    public_filtered = customers.filter(sector='PUBLIC')
    withl_filtered = customers.filter(number_of_loans__gt=0)
    withoutl_filtered = customers.filter(number_of_loans=0)

    context = {
        'nav' : 'customers_all',
        'customers_all' : customers_all,
        'customers_withloan' : customers_withloan,
        'customers_pending': customers_pending,
        'customers_flagged' :  customers_flagged,
        'customers_suspended' : customers_suspended,
        'customers_filtered':customers_filtered,
        'members_filtered':members_filtered,
        'nonmembers_filtered':nonmembers_filtered,
        'private_filtered':private_filtered,
        'public_filtered':public_filtered,
        'withl_filtered':withl_filtered,
        'withoutl_filtered':withoutl_filtered,
        
    }
    
    return render(request, 'customers_all.html', context )
   
@admin_check
def customers_withloan(request):
    
    referrer = request.META['HTTP_REFERER']
    
    customers = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0, number_of_loans__gt=0).all()
    customers_allx = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0).all()
    
    customers_all = customers_allx
    customers_withloan = customers_allx.filter(number_of_loans__gt=0).all()
    customers_pending = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_flagged = customers_allx.filter(user__dcc_flagged=1).all()
    customers_suspended = customers_allx.filter(user__suspended=1).all()
    
    
    if request.method=='POST':
        
        if request.POST.get('cuscat') and request.POST.get('sectype'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')    
            
            if sectype == 'PUBLIC':
                
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='MEMBER')
                    
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )  
                            
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='PUBLIC', category='NON-MEMBER') 
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                            
                        }
                    
                    return render(request, 'customers_withloan.html', context )  
                else:
                    customers_filtered = customers.filter(sector='PUBLIC', category='STAFF')
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )
            
            elif sectype == 'PRIVATE':
                
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='MEMBER') 
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )   
                else:
                    customers_filtered = customers.filter(sector='PRIVATE', category='STAFF')
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )
            
            else:
                
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='MEMBER') 
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )   
                else:
                    customers_filtered = customers.filter(sector='NA', category='STAFF')
                    context = {
                            'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_withloan.html', context )
             
        elif request.POST.get('cuscat'):
            
            cuscat = request.POST.get('cuscat')   
                
            if cuscat == 'MEMBER':
                
                customers_filtered = customers.filter(category='MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':customers_filtered,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                return render(request, 'customers_withloan.html', context )    
                    
            elif cuscat == 'NON-MEMBER':
                
                customers_filtered = customers.filter(category='NON-MEMBER') 
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':customers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,    
                    }
                
                return render(request, 'customers_withloan.html', context )  
            
            else:
                customers_filtered = customers.filter(category='STAFF')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                
                return render(request, 'customers_withloan.html', context )        
          
        elif request.POST.get('sectype'):

            sectype = request.POST.get('sectype')  
            
            if sectype == 'PUBLIC':
                        
                customers_filtered = customers.filter(sector='PUBLIC')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                
                context = {
                        'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':customers_filtered,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                
                return render(request, 'customers_withloan.html', context )                      
                    
            elif sectype == 'PRIVATE':
                    
                customers_filtered = customers.filter(sector='PRIVATE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                
                context = {
                        'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':customers_filtered,
                        'public_filtered':0,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                
                return render(request, 'customers_withloan.html', context )                                           
                    
            else:
                    
                customers_filtered = customers.filter(sector='NA') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                
                context = {
                        'nav' : 'customers_withloan', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':0,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                
                return render(request, 'customers_withloan.html', context )                       
        
                      
    customers_filtered = customers
    members_filtered = customers.filter(category='MEMBER')  
    nonmembers_filtered = customers.filter(category='NON-MEMBER')
    private_filtered = customers.filter(sector='PRIVATE')
    public_filtered = customers.filter(sector='PUBLIC')    

    context = {
        'nav' : 'customers_withloan',
        'customers_all' : customers_all,
        'customers_withloan' : customers_withloan,
        'customers_pending': customers_pending,
        'customers_flagged' :  customers_flagged,
        'customers_suspended' : customers_suspended,
        'customers_filtered':customers_filtered,
        'members_filtered':members_filtered,
        'nonmembers_filtered':nonmembers_filtered,
        'private_filtered':private_filtered,
        'public_filtered':public_filtered,
        'withl_filtered':customers_filtered,
        'withoutl_filtered':0,
        
    }
    
    return render(request, 'customers_withloan.html', context )

@admin_check
def customers_pending(request):
    
    referrer = request.META['HTTP_REFERER']
    
    customers = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_allx = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0).all()
    
    customers_all = customers_allx
    customers_withloan = customers_allx.filter(number_of_loans__gt=0).all()
    customers_pending = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_flagged = customers_allx.filter(user__dcc_flagged=1).all()
    customers_suspended = customers_allx.filter(user__suspended=1).all()
    
    
    if request.method=='POST':
        
        if request.POST.get('cuscat') and request.POST.get('sectype') and request.POST.get('reqcheck'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')  
            reqcheck = request.POST.get('reqcheck')  
            
            if sectype == 'PUBLIC':
                
                if reqcheck == 'COMPLETED':
                    if cuscat == 'MEMBER':
                        
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED', category='MEMBER')
                        
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )  
                               
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED', category='NON-MEMBER') 
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                                
                            }
                        
                        return render(request, 'customers_pending.html', context )  
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED', category='STAFF')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE', category='MEMBER') 
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE', category='STAFF')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )
                    
            elif sectype == 'PRIVATE':
                
                if reqcheck == 'COMPLETED':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED', category='MEMBER') 
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED', category='STAFF')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE', category='MEMBER')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE', category='STAFF')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )

            else:
                
                if reqcheck == 'COMPLETED':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED', category='MEMBER') 
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED', category='STAFF')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE', category='MEMBER')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE', category='STAFF')
                        context = {
                                'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending.html', context )
   
        elif request.POST.get('cuscat') and request.POST.get('sectype'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')    
            
            if sectype == 'PUBLIC':
                
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='MEMBER')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    return render(request, 'customers_pending.html', context )    
                       
                elif cuscat == 'NON-MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='NON-MEMBER') 
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                            
                        }
                    
                    return render(request, 'customers_pending.html', context )  
                else:
                    customers_filtered = customers.filter(sector='PUBLIC', category='STAFF')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )
            
            elif sectype == 'PRIVATE':
                
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='MEMBER') 
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='NON-MEMBER')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )   
                else:
                    customers_filtered = customers.filter(sector='PRIVATE', category='STAFF')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )
            
            else: 
               
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='MEMBER') 
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='NON-MEMBER')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )   
                else:
                    customers_filtered = customers.filter(sector='NA', category='STAFF')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )
            
        elif request.POST.get('cuscat') and request.POST.get('reqcheck'):
            
            cuscat = request.POST.get('cuscat')  
            reqcheck = request.POST.get('reqcheck')  
             
            if reqcheck == 'COMPLETED':
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(requirement_check = 'COMPLETED', category='MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending.html', context )  
                            
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(requirement_check = 'COMPLETED', category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                            
                        }
                    
                    return render(request, 'customers_pending.html', context )  
                else:
                    customers_filtered = customers.filter(requirement_check = 'COMPLETED', category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending.html', context )
            else:
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(requirement_check = 'INCOMPLETE', category='MEMBER') 
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )   
                else:
                    customers_filtered = customers.filter(requirement_check = 'INCOMPLETE', category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )
        
        elif request.POST.get('sectype') and request.POST.get('reqcheck'):

            sectype = request.POST.get('sectype')  
            reqcheck = request.POST.get('reqcheck')  
            
            if sectype == 'PUBLIC':
                
                if reqcheck == 'COMPLETED':
                        
                    customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED')
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending.html', context )  
                               
                else:
                    
                    customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE') 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )                       
                    
            elif sectype == 'PRIVATE':
                
                if reqcheck == 'COMPLETED':
                    
                    customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED') 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending.html', context )                       
                
                else:
                   
                    customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE')
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )                        
                    
            else:
                
                if reqcheck == 'COMPLETED':
                    
                    customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED') 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending.html', context )                       
                    
                else:
                    
                    customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE')
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending.html', context )                        

        elif request.POST.get('cuscat'):
            
            cuscat = request.POST.get('cuscat')   
                
            if cuscat == 'MEMBER':
                
                customers_filtered = customers.filter(category='MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':customers_filtered,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                return render(request, 'customers_pending.html', context )    
                    
            elif cuscat == 'NON-MEMBER':
                
                customers_filtered = customers.filter(category='NON-MEMBER') 
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':customers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,    
                    }
                
                return render(request, 'customers_pending.html', context )  
            
            else:
                customers_filtered = customers.filter(category='STAFF')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending.html', context )        
          
        elif request.POST.get('sectype'):

            sectype = request.POST.get('sectype')  
            
            if sectype == 'PUBLIC':
                        
                customers_filtered = customers.filter(sector='PUBLIC')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                              'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':customers_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending.html', context )                      
                    
            elif sectype == 'PRIVATE':
                    
                customers_filtered = customers.filter(sector='PRIVATE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':customers_filtered,
                        'public_filtered':0,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending.html', context )                                           
                    
            else:
                    
                customers_filtered = customers.filter(sector='NA') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':0,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending.html', context )                       
        
        elif request.POST.get('reqcheck'):
  
            reqcheck = request.POST.get('reqcheck')  
                
            if reqcheck == 'COMPLETED':
                    
                customers_filtered = customers.filter(requirement_check = 'COMPLETED')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                                'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':customers_filtered,
                        'uncheck_filtered':0,
                    }
                
                return render(request, 'customers_pending.html', context )  
                            
            else:
                
                customers_filtered = customers.filter(requirement_check = 'INCOMPLETE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                context = {
                        'nav' : 'customers_pending', 'filter': 'on', 'referrer': referrer,
                               'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':0,
                        'uncheck_filtered':customers_filtered,
                    }
                
                return render(request, 'customers_pending.html', context )                       
                            
    customers_filtered = customers
    members_filtered = customers.filter(category='MEMBER')  
    nonmembers_filtered = customers.filter(category='NON-MEMBER')
    private_filtered = customers.filter(sector='PRIVATE')
    public_filtered = customers.filter(sector='PUBLIC')
    check_filtered = customers.filter(requirement_check = 'COMPLETED')
    uncheck_filtered = customers.filter(requirement_check = 'INCOMPLETE')

    context = {
        'nav' : 'customers_pending',
        'customers_all' : customers_all,
        'customers_withloan' : customers_withloan,
        'customers_pending': customers_pending,
        'customers_flagged' :  customers_flagged,
        'customers_suspended' : customers_suspended,
        'customers_filtered':customers_filtered,
        'members_filtered':members_filtered,
        'nonmembers_filtered':nonmembers_filtered,
        'private_filtered':private_filtered,
        'public_filtered':public_filtered,
        'check_filtered':check_filtered,
        'uncheck_filtered':uncheck_filtered,
        
    }
    
    return render(request, 'customers_pending.html', context )

@admin_check
def customers_pending_activation(request):
    
    referrer = request.META['HTTP_REFERER']
    
    customers = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0, account_requirements_check='COMPLETED' ).all()
    customers_allx = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0).all()
    
    customers_all = customers_allx
    customers_withloan = customers_allx.filter(number_of_loans__gt=0).all()
    customers_pending = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_flagged = customers_allx.filter(user__dcc_flagged=1).all()
    customers_suspended = customers_allx.filter(user__suspended=1).all()
    
    
    if request.method=='POST':
        
        if request.POST.get('cuscat') and request.POST.get('sectype') and request.POST.get('reqcheck'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')  
            reqcheck = request.POST.get('reqcheck')  
            
            if sectype == 'PUBLIC':
                
                if reqcheck == 'COMPLETED':
                    if cuscat == 'MEMBER':
                        
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED', category='MEMBER')
                        
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )  
                               
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED', category='NON-MEMBER') 
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                                
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )  
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED', category='STAFF')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE', category='MEMBER') 
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE', category='STAFF')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )
                    
            elif sectype == 'PRIVATE':
                
                if reqcheck == 'COMPLETED':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED', category='MEMBER') 
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED', category='STAFF')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE', category='MEMBER')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE', category='STAFF')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )

            else:
                
                if reqcheck == 'COMPLETED':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED', category='MEMBER') 
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED', category='STAFF')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':customers_filtered,
                                'uncheck_filtered':0,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE', category='MEMBER')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE', category='STAFF')
                        context = {
                                'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'check_filtered':0,
                                'uncheck_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_pending_activation.html', context )
   
        elif request.POST.get('cuscat') and request.POST.get('sectype'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')    
            
            if sectype == 'PUBLIC':
                
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='MEMBER')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    return render(request, 'customers_pending_activation.html', context )    
                       
                elif cuscat == 'NON-MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='NON-MEMBER') 
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                            
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )  
                else:
                    customers_filtered = customers.filter(sector='PUBLIC', category='STAFF')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )
            
            elif sectype == 'PRIVATE':
                
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='MEMBER') 
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='NON-MEMBER')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )   
                else:
                    customers_filtered = customers.filter(sector='PRIVATE', category='STAFF')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )
            
            else: 
               
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='MEMBER') 
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='NON-MEMBER')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )   
                else:
                    customers_filtered = customers.filter(sector='NA', category='STAFF')
                    check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                    uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':check_filtered,
                            'uncheck_filtered':uncheck_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )
            
        elif request.POST.get('cuscat') and request.POST.get('reqcheck'):
            
            cuscat = request.POST.get('cuscat')  
            reqcheck = request.POST.get('reqcheck')  
             
            if reqcheck == 'COMPLETED':
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(requirement_check = 'COMPLETED', category='MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )  
                            
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(requirement_check = 'COMPLETED', category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                            
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )  
                else:
                    customers_filtered = customers.filter(requirement_check = 'COMPLETED', category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )
            else:
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(requirement_check = 'INCOMPLETE', category='MEMBER') 
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(requirement_check = 'INCOMPLETE', category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )   
                else:
                    customers_filtered = customers.filter(requirement_check = 'INCOMPLETE', category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )
        
        elif request.POST.get('sectype') and request.POST.get('reqcheck'):

            sectype = request.POST.get('sectype')  
            reqcheck = request.POST.get('reqcheck')  
            
            if sectype == 'PUBLIC':
                
                if reqcheck == 'COMPLETED':
                        
                    customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'COMPLETED')
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )  
                               
                else:
                    
                    customers_filtered = customers.filter(sector='PUBLIC', requirement_check = 'INCOMPLETE') 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                       
                    
            elif sectype == 'PRIVATE':
                
                if reqcheck == 'COMPLETED':
                    
                    customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'COMPLETED') 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                       
                
                else:
                   
                    customers_filtered = customers.filter(sector='PRIVATE', requirement_check = 'INCOMPLETE')
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                        
                    
            else:
                
                if reqcheck == 'COMPLETED':
                    
                    customers_filtered = customers.filter(sector='NA', requirement_check = 'COMPLETED') 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':customers_filtered,
                            'uncheck_filtered':0,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                       
                    
                else:
                    
                    customers_filtered = customers.filter(sector='NA', requirement_check = 'INCOMPLETE')
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'check_filtered':0,
                            'uncheck_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_pending_activation.html', context )                        

        elif request.POST.get('cuscat'):
            
            cuscat = request.POST.get('cuscat')   
                
            if cuscat == 'MEMBER':
                
                customers_filtered = customers.filter(category='MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':customers_filtered,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                return render(request, 'customers_pending_activation.html', context )    
                    
            elif cuscat == 'NON-MEMBER':
                
                customers_filtered = customers.filter(category='NON-MEMBER') 
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':customers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,    
                    }
                
                return render(request, 'customers_pending_activation.html', context )  
            
            else:
                customers_filtered = customers.filter(category='STAFF')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending_activation.html', context )        
          
        elif request.POST.get('sectype'):

            sectype = request.POST.get('sectype')  
            
            if sectype == 'PUBLIC':
                        
                customers_filtered = customers.filter(sector='PUBLIC')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                              'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':customers_filtered,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending_activation.html', context )                      
                    
            elif sectype == 'PRIVATE':
                    
                customers_filtered = customers.filter(sector='PRIVATE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':customers_filtered,
                        'public_filtered':0,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending_activation.html', context )                                           
                    
            else:
                    
                customers_filtered = customers.filter(sector='NA') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                check_filtered = customers_filtered.filter(requirement_check = 'COMPLETED')
                uncheck_filtered = customers_filtered.filter(requirement_check = 'INCOMPLETE')
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':0,
                        'check_filtered':check_filtered,
                        'uncheck_filtered':uncheck_filtered,
                    }
                
                return render(request, 'customers_pending_activation.html', context )                       
        
        elif request.POST.get('reqcheck'):
  
            reqcheck = request.POST.get('reqcheck')  
                
            if reqcheck == 'COMPLETED':
                    
                customers_filtered = customers.filter(requirement_check = 'COMPLETED')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                                'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':customers_filtered,
                        'uncheck_filtered':0,
                    }
                
                return render(request, 'customers_pending_activation.html', context )  
                            
            else:
                
                customers_filtered = customers.filter(requirement_check = 'INCOMPLETE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                context = {
                        'nav' : 'customers_pending_activation', 'filter': 'on', 'referrer': referrer,
                               'reqcheck': reqcheck,
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'check_filtered':0,
                        'uncheck_filtered':customers_filtered,
                    }
                
                return render(request, 'customers_pending_activation.html', context )                       
                            
    customers_filtered = customers
    members_filtered = customers.filter(category='MEMBER')  
    nonmembers_filtered = customers.filter(category='NON-MEMBER')
    private_filtered = customers.filter(sector='PRIVATE')
    public_filtered = customers.filter(sector='PUBLIC')
    check_filtered = customers.filter(requirement_check = 'COMPLETED')
    uncheck_filtered = customers.filter(requirement_check = 'INCOMPLETE')

    context = {
        'nav' : 'customers_pending_activation',
        'customers_all' : customers_all,
        'customers_withloan' : customers_withloan,
        'customers_pending': customers_pending,
        'customers_flagged' :  customers_flagged,
        'customers_suspended' : customers_suspended,
        'customers_filtered':customers_filtered,
        'members_filtered':members_filtered,
        'nonmembers_filtered':nonmembers_filtered,
        'private_filtered':private_filtered,
        'public_filtered':public_filtered,
        'check_filtered':check_filtered,
        'uncheck_filtered':uncheck_filtered,
        
    }
    
    return render(request, 'customers_pending_activation.html', context )
 

@admin_check
def customers_flagged(request):
    
    referrer = request.META['HTTP_REFERER']
    
    customers = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0, user__dcc_flagged=True).all()
    customers_allx = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0).all()
    
    customers_all = customers_allx
    customers_withloan = customers_allx.filter(number_of_loans__gt=0).all()
    customers_pending = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_flagged = customers_allx.filter(user__dcc_flagged=1).all()
    customers_suspended = customers_allx.filter(user__suspended=1).all()
    
    
    if request.method=='POST':
        
        if request.POST.get('cuscat') and request.POST.get('sectype') and request.POST.get('loanopt'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')  
            loanopt = request.POST.get('loanopt')  
            
            if sectype == 'PUBLIC':
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='MEMBER')
                        
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )  
                               
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='NON-MEMBER') 
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                                
                            }
                        
                        return render(request, 'customers_flagged.html', context )  
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )
                    
            elif sectype == 'PRIVATE':
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='MEMBER')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )

            else:
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_flagged.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='MEMBER')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_flagged.html', context )
   
        elif request.POST.get('cuscat') and request.POST.get('sectype'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')    
            
            if sectype == 'PUBLIC':
                
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    return render(request, 'customers_flagged.html', context )    
                       
                elif cuscat == 'NON-MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='NON-MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                            
                        }
                    
                    return render(request, 'customers_flagged.html', context )  
                else:
                    customers_filtered = customers.filter(sector='PUBLIC', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )
            
            elif sectype == 'PRIVATE':
                
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='NON-MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )   
                else:
                    customers_filtered = customers.filter(sector='PRIVATE', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )
            
            else: 
               
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='NON-MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )   
                else:
                    customers_filtered = customers.filter(sector='NA', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )
            
        elif request.POST.get('cuscat') and request.POST.get('loanopt'):
            
            cuscat = request.POST.get('cuscat')  
            loanopt = request.POST.get('loanopt')  
             
            if loanopt == 'withloan':
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_flagged.html', context )  
                            
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                            
                        }
                    
                    return render(request, 'customers_flagged.html', context )  
                else:
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_flagged.html', context )
            else:
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(number_of_loans=0, category='MEMBER') 
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(number_of_loans=0, category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )   
                else:
                    customers_filtered = customers.filter(number_of_loans=0, category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )
        
        elif request.POST.get('sectype') and request.POST.get('loanopt'):

            sectype = request.POST.get('sectype')  
            loanopt = request.POST.get('loanopt')  
            
            if sectype == 'PUBLIC':
                
                if loanopt == 'withloan':
                        
                    customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_flagged.html', context )  
                               
                else:
                    
                    customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                       
                    
            elif sectype == 'PRIVATE':
                
                if loanopt == 'withloan':
                    
                    customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                       
                
                else:
                   
                    customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                              'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                        
                    
            else:
                
                if loanopt == 'withloan':
                    
                    customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                               'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                       
                    
                else:
                    
                    customers_filtered = customers.filter(sector='NA', number_of_loans=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                               'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_flagged.html', context )                        

        elif request.POST.get('cuscat'):
            
            cuscat = request.POST.get('cuscat')   
                
            if cuscat == 'MEMBER':
                
                customers_filtered = customers.filter(category='MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':customers_filtered,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                return render(request, 'customers_flagged.html', context )    
                    
            elif cuscat == 'NON-MEMBER':
                
                customers_filtered = customers.filter(category='NON-MEMBER') 
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':customers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,    
                    }
                
                return render(request, 'customers_flagged.html', context )  
            
            else:
                customers_filtered = customers.filter(category='STAFF')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_flagged.html', context )        
          
        elif request.POST.get('sectype'):

            sectype = request.POST.get('sectype')  
            
            if sectype == 'PUBLIC':
                        
                customers_filtered = customers.filter(sector='PUBLIC')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                               'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':customers_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_flagged.html', context )                      
                    
            elif sectype == 'PRIVATE':
                    
                customers_filtered = customers.filter(sector='PRIVATE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':customers_filtered,
                        'public_filtered':0,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_flagged.html', context )                                           
                    
            else:
                    
                customers_filtered = customers.filter(sector='NA') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':0,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_flagged.html', context )                       
        
        elif request.POST.get('loanopt'):
  
            loanopt = request.POST.get('loanopt')  
                
            if loanopt == 'withloan':
                    
                customers_filtered = customers.filter(number_of_loans__gt=0)
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                              'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                
                return render(request, 'customers_flagged.html', context )  
                            
            else:
                
                customers_filtered = customers.filter(number_of_loans=0) 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                context = {
                        'nav' : 'customers_flagged', 'filter': 'on', 'referrer': referrer,
                                 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':0,
                        'withoutl_filtered':customers_filtered,
                    }
                
                return render(request, 'customers_flagged.html', context )                       
                            
    customers_filtered = customers
    members_filtered = customers.filter(category='MEMBER')  
    nonmembers_filtered = customers.filter(category='NON-MEMBER')
    private_filtered = customers.filter(sector='PRIVATE')
    public_filtered = customers.filter(sector='PUBLIC')
    withl_filtered = customers.filter(number_of_loans__gt=0)
    withoutl_filtered = customers.filter(number_of_loans=0)

    context = {
        'nav' : 'customers_flagged',
        'customers_all' : customers_all,
        'customers_withloan' : customers_withloan,
        'customers_pending': customers_pending,
        'customers_flagged' :  customers_flagged,
        'customers_suspended' : customers_suspended,
        'customers_filtered':customers_filtered,
        'members_filtered':members_filtered,
        'nonmembers_filtered':nonmembers_filtered,
        'private_filtered':private_filtered,
        'public_filtered':public_filtered,
        'withl_filtered':withl_filtered,
        'withoutl_filtered':withoutl_filtered,
        
    }
    
    return render(request, 'customers_flagged.html', context )

@admin_check
def customers_suspended(request):
    
    referrer = request.META['HTTP_REFERER']
    
    customers = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0, user__suspended=True).all()
    customers_allx = UserProfile.objects.select_related('user').filter(activation=1, user__staff=0).all()
    
    customers_all = customers_allx
    customers_withloan = customers_allx.filter(number_of_loans__gt=0).all()
    customers_pending = UserProfile.objects.select_related('user').filter(activation=0, user__staff=0).all()
    customers_flagged = customers_allx.filter(user__dcc_flagged=1).all()
    customers_suspended = customers_allx.filter(user__suspended=1).all()
    
    if request.method=='POST':
        
        if request.POST.get('cuscat') and request.POST.get('sectype') and request.POST.get('loanopt'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')  
            loanopt = request.POST.get('loanopt')  
            
            if sectype == 'PUBLIC':
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='MEMBER')
                        
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )  
                               
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='NON-MEMBER') 
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                                
                            }
                        
                        return render(request, 'customers_suspended.html', context )  
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':customers_filtered,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )
                    
            elif sectype == 'PRIVATE':
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='MEMBER')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':customers_filtered,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )

            else:
                
                if loanopt == 'withloan':
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='MEMBER') 
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )                       
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0, category='STAFF')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':customers_filtered,
                                'withoutl_filtered':0,
                            }
                        
                        return render(request, 'customers_suspended.html', context )
                
                else:
                    if cuscat == 'MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='MEMBER')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':customers_filtered,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )                        
                    elif cuscat == 'NON-MEMBER':
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='NON-MEMBER')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':customers_filtered,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )   
                    else:
                        customers_filtered = customers.filter(sector='NA', number_of_loans=0, category='STAFF')
                        context = {
                                'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                                'customers_withloan' : customers_withloan,
                                'customers_pending': customers_pending,
                                'customers_flagged' :  customers_flagged,
                                'customers_suspended' : customers_suspended,
                                'customers_filtered': customers_filtered,
                                'members_filtered':0,
                                'nonmembers_filtered':0,
                                'private_filtered':0,
                                'public_filtered':0,
                                'withl_filtered':0,
                                'withoutl_filtered':customers_filtered,
                            }
                        
                        return render(request, 'customers_suspended.html', context )
   
        elif request.POST.get('cuscat') and request.POST.get('sectype'):
            
            cuscat = request.POST.get('cuscat') 
            sectype = request.POST.get('sectype')    
            
            if sectype == 'PUBLIC':
                
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    return render(request, 'customers_suspended.html', context )    
                       
                elif cuscat == 'NON-MEMBER':
                    
                    customers_filtered = customers.filter(sector='PUBLIC', category='NON-MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                            
                        }
                    
                    return render(request, 'customers_suspended.html', context )  
                else:
                    customers_filtered = customers.filter(sector='PUBLIC', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )
            
            elif sectype == 'PRIVATE':
                
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='PRIVATE', category='NON-MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )   
                else:
                    customers_filtered = customers.filter(sector='PRIVATE', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )
            
            else: 
               
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='MEMBER') 
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype,
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(sector='NA', category='NON-MEMBER')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )   
                else:
                    customers_filtered = customers.filter(sector='NA', category='STAFF')
                    withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                    withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'sectype': sectype, 
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':withl_filtered,
                            'withoutl_filtered':withoutl_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )
            
        elif request.POST.get('cuscat') and request.POST.get('loanopt'):
            
            cuscat = request.POST.get('cuscat')  
            loanopt = request.POST.get('loanopt')  
             
            if loanopt == 'withloan':
                if cuscat == 'MEMBER':
                    
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_suspended.html', context )  
                            
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                            
                        }
                    
                    return render(request, 'customers_suspended.html', context )  
                else:
                    customers_filtered = customers.filter(number_of_loans__gt=0, category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_suspended.html', context )
            else:
                if cuscat == 'MEMBER':
                    customers_filtered = customers.filter(number_of_loans=0, category='MEMBER') 
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC') 
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':customers_filtered,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                       
                elif cuscat == 'NON-MEMBER':
                    customers_filtered = customers.filter(number_of_loans=0, category='NON-MEMBER')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':customers_filtered,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )   
                else:
                    customers_filtered = customers.filter(number_of_loans=0, category='STAFF')
                    private_filtered = customers_filtered.filter(sector='PRIVATE')
                    public_filtered = customers_filtered.filter(sector='PUBLIC')
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat,  'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':0,
                            'nonmembers_filtered':0,
                            'private_filtered':private_filtered,
                            'public_filtered':public_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )
        
        elif request.POST.get('sectype') and request.POST.get('loanopt'):

            sectype = request.POST.get('sectype')  
            loanopt = request.POST.get('loanopt')  
            
            if sectype == 'PUBLIC':
                
                if loanopt == 'withloan':
                        
                    customers_filtered = customers.filter(sector='PUBLIC', number_of_loans__gt=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                               'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_suspended.html', context )  
                               
                else:
                    
                    customers_filtered = customers.filter(sector='PUBLIC', number_of_loans=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':customers_filtered,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                       
                    
            elif sectype == 'PRIVATE':
                
                if loanopt == 'withloan':
                    
                    customers_filtered = customers.filter(sector='PRIVATE', number_of_loans__gt=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                               'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                       
                
                else:
                   
                    customers_filtered = customers.filter(sector='PRIVATE', number_of_loans=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':customers_filtered,
                            'public_filtered':0,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                        
                    
            else:
                
                if loanopt == 'withloan':
                    
                    customers_filtered = customers.filter(sector='NA', number_of_loans__gt=0) 
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':customers_filtered,
                            'withoutl_filtered':0,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                       
                    
                else:
                    
                    customers_filtered = customers.filter(sector='NA', number_of_loans=0)
                    members_filtered = customers_filtered.filter(category='MEMBER')
                    nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                    context = {
                            'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                 'sectype': sectype, 'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                            'customers_withloan' : customers_withloan,
                            'customers_pending': customers_pending,
                            'customers_flagged' :  customers_flagged,
                            'customers_suspended' : customers_suspended,
                            'customers_filtered': customers_filtered,
                            'members_filtered':members_filtered,
                            'nonmembers_filtered':nonmembers_filtered,
                            'private_filtered':0,
                            'public_filtered':0,
                            'withl_filtered':0,
                            'withoutl_filtered':customers_filtered,
                        }
                    
                    return render(request, 'customers_suspended.html', context )                        

        elif request.POST.get('cuscat'):
            
            cuscat = request.POST.get('cuscat')   
                
            if cuscat == 'MEMBER':
                
                customers_filtered = customers.filter(category='MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':customers_filtered,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                return render(request, 'customers_suspended.html', context )    
                    
            elif cuscat == 'NON-MEMBER':
                
                customers_filtered = customers.filter(category='NON-MEMBER') 
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':customers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,    
                    }
                
                return render(request, 'customers_suspended.html', context )  
            
            else:
                customers_filtered = customers.filter(category='STAFF')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'cuscat': cuscat, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':0,
                        'nonmembers_filtered':0,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_suspended.html', context )        
          
        elif request.POST.get('sectype'):

            sectype = request.POST.get('sectype')  
            
            if sectype == 'PUBLIC':
                        
                customers_filtered = customers.filter(sector='PUBLIC')
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':customers_filtered,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_suspended.html', context )                      
                    
            elif sectype == 'PRIVATE':
                    
                customers_filtered = customers.filter(sector='PRIVATE') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':customers_filtered,
                        'public_filtered':0,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_suspended.html', context )                                           
                    
            else:
                    
                customers_filtered = customers.filter(sector='NA') 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                withl_filtered = customers_filtered.filter(number_of_loans__gt=0)
                withoutl_filtered = customers_filtered.filter(number_of_loans=0)
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'sectype': sectype, 
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':0,
                        'public_filtered':0,
                        'withl_filtered':withl_filtered,
                        'withoutl_filtered':withoutl_filtered,
                    }
                
                return render(request, 'customers_suspended.html', context )                       
        
        elif request.POST.get('loanopt'):
  
            loanopt = request.POST.get('loanopt')  
                
            if loanopt == 'withloan':
                    
                customers_filtered = customers.filter(number_of_loans__gt=0)
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                                'loanopt': 'WITH LOAN',
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':customers_filtered,
                        'withoutl_filtered':0,
                    }
                
                return render(request, 'customers_suspended.html', context )  
                            
            else:
                
                customers_filtered = customers.filter(number_of_loans=0) 
                members_filtered = customers_filtered.filter(category='MEMBER')
                nonmembers_filtered = customers_filtered.filter(category='NON-MEMBER')
                private_filtered = customers_filtered.filter(sector='PRIVATE')
                public_filtered = customers_filtered.filter(sector='PUBLIC')
                context = {
                        'nav' : 'customers_suspended', 'filter': 'on', 'referrer': referrer,
                               'loanopt': 'WITHOUT LOAN',
                                'customers_all' : customers_all,
                        'customers_withloan' : customers_withloan,
                        'customers_pending': customers_pending,
                        'customers_flagged' :  customers_flagged,
                        'customers_suspended' : customers_suspended,
                        'customers_filtered': customers_filtered,
                        'members_filtered':members_filtered,
                        'nonmembers_filtered':nonmembers_filtered,
                        'private_filtered':private_filtered,
                        'public_filtered':public_filtered,
                        'withl_filtered':0,
                        'withoutl_filtered':customers_filtered,
                    }
                
                return render(request, 'customers_suspended.html', context )                       
                            
    customers_filtered = customers
    members_filtered = customers.filter(category='MEMBER')  
    nonmembers_filtered = customers.filter(category='NON-MEMBER')
    private_filtered = customers.filter(sector='PRIVATE')
    public_filtered = customers.filter(sector='PUBLIC')
    withl_filtered = customers.filter(number_of_loans__gt=0)
    withoutl_filtered = customers.filter(number_of_loans=0)

    context = {
        'nav' : 'customers_suspended',
        'customers_all' : customers_all,
        'customers_withloan' : customers_withloan,
        'customers_pending': customers_pending,
        'customers_flagged' :  customers_flagged,
        'customers_suspended' : customers_suspended,
        'customers_filtered':customers_filtered,
        'members_filtered':members_filtered,
        'nonmembers_filtered':nonmembers_filtered,
        'private_filtered':private_filtered,
        'public_filtered':public_filtered,
        'withl_filtered':withl_filtered,
        'withoutl_filtered':withoutl_filtered,
        
    }
    
    return render(request, 'customers_suspended.html', context )

@admin_check
def view_customer(request, uid): 
    
    
    try:
        referrer = f"{request.META['HTTP_REFERER']}"
    except:
        referrer = f"{request.META['HTTP_HOST']}/admin/customers/"
           
    user = UserProfile.objects.get(pk=uid)
    dccuid = user.uid

    #activation checklist
    now = datetime.date.today()
    dob = user.date_of_birth
    start = user.start_date
    if dob:
        age = round(((now.month - dob.month + (12 * (now.year - dob.year)))/12),2)
    else:
        age = 0
    if start:
        yef = round(((now.month - start.month + (12 * (now.year - start.year)))/12),2)
    else:
        yef = 0
    '''
    #dcc
    #dcc
    print('Printing UID')
    print(dccuid)
    client_check = check_client_in_dcc(dccuid)
    print('CLIENT CHECK RESULT:')
    print(client_check)
    if client_check != f'{client_check}':
        client = client_check
        uidresult = client['uid']
        print('client:')
        print(client)

        #loans = get_loans_for_client(uidresult)
        dcc_endpoint = settings.DCC_ENDPOINT
        endpoint = f'http://{dcc_endpoint}/API/get_client_loans/{uidresult}/'
        # Make a GET request to the API endpoint
        print('ENTERING API:')
        print(endpoint)
        try:
            response = requests.get(endpoint, verify=False)
            print('PRINTING RESPONSE')
            print(response)
            if response.status_code == 404:
                loans_from_dcc = []
            else:
                loans_from_dcc = []
            if response.status_code == 200:
                data = response.json()
                print(data)
                if data:
                    serializer = LoanSerializer(data=data, many=True)
                    print(serializer)
                    if serializer.is_valid():
                        print("PRINTING SERIALIZER VALIDATED DATA")
                        print(serializer.validated_data)
                        loans_from_dcc = serializer.validated_data
                    else:
                        loans_from_dcc = []
                else:
                    loans_from_dcc = []
            else:
                loans_from_dcc = []
        except:
            messages.error(request, 'NOT WORKING', extra_tags="danger")
            loans_from_dcc = []

        #transactions = get_transactions_for_client(uidresult)
        dcc_endpoint = settings.DCC_ENDPOINT
        transendpoint = f'http://{dcc_endpoint}/API/get_client_transactions/{uidresult}/'
        # Make a GET request to the API endpoint
        print('ENTERING API:')
        print(endpoint)
        try:
            response = requests.get(transendpoint, verify=False)
            print('PRINTING RESPONSE')
            print(response)
            if response.status_code == 404:
                statements_from_dcc = []
            if response.status_code == 200:
                data = response.json()
                print('PRINTING DATA')
                print(data)
                if data:

                    serializer = StatementSerializer(data=data, many=True)
                    print('PRINTING SERIALIZER:')
                    print(serializer)
                    if serializer.is_valid():
                        print(serializer.validated_data)
                        statements_from_dcc = serializer.validated_data
                else:
                    statements_from_dcc = []

        except:
            messages.error(request, 'NOT WORKING', extra_tags="danger")
            statements_from_dcc = []

        
    else:
        client=[]
        uidresult = []
        loans_from_dcc = []
        statements_from_dcc = []
        if client_check == 'Client is not in DCC Credit Database.':
            messages.error(request, f'{client_check}', extra_tags='info')
        else:
            messages.error(request, f'{client_check}', extra_tags='danger')
    
    
    #print('PRINTING CLIENT UID & LOANS:')
    
    #print(uidresult)
    #print(loans_from_dcc)
    #print(statements_from_dcc)
    '''

    #from django.db.models import Q
    # Combine the two queries into one
    combined_query = Q(owner=user.id) & Q(category='PENDING') & (Q(status='AWAITING T&C') | Q(status='UNDER REVIEW'))
    # Retrieve loans matching the combined query
    combined_loans = Loan.objects.filter(combined_query)
    # Now combined_loans contains loans that satisfy both conditions
    print('Printing Combined Loans:')
    print(combined_loans)
    if combined_loans:
        try:
            loan = Loan.objects.get(combined_query)
            print('Printing Loan')
            print(loan)
            loanfile = LoanFile.objects.get(loan=loan)
            print('Printing LoanFile')
            print(loanfile)
        except:
            loanfile = []
    else:
        loanfile = []
    suser = User.objects.get(id=user.user_id)
    print(suser)
    if user.has_sme == 1:
        smeprofile = SMEProfile.objects.get(owner=user)
    else:
        smeprofile = SMEProfile.objects.filter(owner=user)
   
    all_loans = Loan.objects.filter(owner_id=user).all()
    pending_loans = Loan.objects.filter(owner_id=user,category="PENDING")
    running_loans = Loan.objects.filter(owner_id=user,funded_category="ACTIVE",status="RUNNING")
    defaulted_loans = Loan.objects.filter(owner_id=user,funded_category="ACTIVE",status="DEFAULTED")
    completed_loans = Loan.objects.filter(owner_id=user,funded_category="COMPLETED")
    recovery_loans = Loan.objects.filter(owner_id=user,funded_category="RECOVERY")

    staff_profiles = StaffProfile.objects.all()
    locations = Location.objects.all()

    stafflist = []
    for staff in staff_profiles:
        stafflist.append(f'{staff.user.first_name} {staff.user.last_name}')
    
    locationlist = []
    for location in locations:
        locationlist.append(location.name)

    try:
        officer = StaffProfile.objects.get(id=user.officer)
        officer_fullname = f'{officer.first_name} {officer.last_name}'
    except:
        officer_fullname = "No Officer Assigned"
    
    if request.method == 'POST':
        
        if request.POST.get('subject') and request.POST.get('messageapplicant'):
            
            
    
            subject = request.POST.get('subject')
            ''' if header_cta == 'yes' '''
            cta_label = ''
            cta_link = ''

            greeting = f'Hi {user.first_name}'
            message = f'This is regarding {subject}'
            message_details = request.POST.get('messageapplicant')

            ''' if cta == 'yes' '''
            cta_btn1_label = 'Login into Dashboard'
            cta_btn1_link = f'{settings.DOMAIN}/dashboard/'
            cta_btn2_label = ''
            cta_btn2_link = ''

            ''' if promo == 'yes' '''
            catchphrase = ''
            promo_title = ''
            promo_message = ''
            promo_cta = ''
            promo_cta_link = ''
            
            email_content = render_to_string('custom/email_temp_general.html', {
                'header_cta': 'no',
                'cta': 'no',
                'cta_btn2': 'no',
                'promo': 'no',
                'cta_link': cta_link,
                'cta_label': cta_label,
                'subject': subject,
                'greeting': greeting,
                'message': message,
                'message_details': message_details,
                'cta_btn1_link': cta_btn1_link,
                'cta_btn1_label': cta_btn1_label,
                'cta_btn2_link': cta_btn2_link,
                'cta_btn2_label': cta_btn2_label,
                'catchphrase': catchphrase,
                'promo_title': promo_title,
                'promo_message': promo_message,
                'promo_cta_link': promo_cta_link,
                'promo_cta': promo_cta,
                'user': user,
                'domain': domain,
                
               
                
            })
            
            text_content = strip_tags(email_content)
            email = EmailMultiAlternatives(subject,text_content,sender,['dev@webmasta.com.pg', user.email ])
            email.attach_alternative(email_content, "text/html")
            
            try: 
                email.send()
                messages.success(request, "Message has been forwarded successfully")
                return redirect('view_customer', uid)
            except:
                messages.error(request, 'Message has not been sent.', extra_tags='danger')
                
            return redirect('view_customer', uid)
        
        
        elif request.POST.get('limit'):
            limit = request.POST.get('limit')
            intlimit = int(limit)
            user.repayment_limit = intlimit
            user.save()
            
                
            subject = 'Deduction Limit Set'

            greeting = f'Hi {user.first_name}'
            message = 'A deduction limit has been set on your account.'
            message_details = 'Everytime you wish to apply for a loan, the amount and fortnights combination must give you a repayment amount below this limit.'

            ''' if cta == 'yes' '''
            cta_btn1_label = f'Limit: K{user.repayment_limit}'
            cta_btn1_link = '#'
            cta_btn2_label = 'APPLY'
            cta_btn2_link = f'{settings.DOMAIN}/loan/apply/'

            ''' if promo == 'yes' '''
            catchphrase = 'TIP:'
            promo_title = 'Need a higher limit?'
            promo_message = 'We can increase your limit if your credit score with us improves.'
            promo_cta = 'Read more about Credit Score'
            promo_cta_link = 'http://www.dcc.com.pg'
            
            email_content = render_to_string('custom/email_temp_general.html', {
                
                'cta': 'yes',
                'cta_btn2': 'yes',
                'promo': 'yes',
                'subject': subject,
                'greeting': greeting,
                'message': message,
                'message_details': message_details,
                'cta_btn1_link': cta_btn1_link,
                'cta_btn1_label': cta_btn1_label,
                'cta_btn2_link': cta_btn2_link,
                'cta_btn2_label': cta_btn2_label,
                'catchphrase': catchphrase,
                'promo_title': promo_title,
                'promo_message': promo_message,
                'promo_cta_link': promo_cta_link,
                'promo_cta': promo_cta,
                'user': user,
                'domain': domain,
              
                
            })
            text_content = strip_tags(email_content)
            email = EmailMultiAlternatives(
                subject,
                text_content,
                sender,
                ['dev@webmasta.com.pg', user.email ]
            )
            email.attach_alternative(email_content, "text/html")

            try: 
                email.send()
                messages.success(request, f'Limit sucessfully set to K{ intlimit } and { user.first_name} has been notified of account deduction limit.')
    
            except:
                messages.error(request, f'Limit sucessfully set to K{ intlimit } but { user.first_name} has NOT been notified of account deduction limit.', extra_tags='info')
                
            return redirect('view_customer', uid)
        
        elif request.POST.get('assignlocation'):
            location_name = request.POST.get('assignlocation')
            location = Location.objects.get(name=location_name)
            user.location = location
            user.save()
            messages.success(request, f'{user.first_name} {user.last_name} assigned to {location_name}')
            return redirect('view_customer', uid)


        elif request.POST.get('assignstaff'):
            staff_name = request.POST.get('assignstaff')
            staff_name_split = staff_name.split(' ')
            first_name = staff_name_split[0]
            last_name = staff_name_split[-1]
            staff = StaffProfile.objects.get(first_name=first_name, last_name=last_name)
            user.officer = staff.id
            user.save()
            messages.success(request, f'{first_name} {last_name} assigned to {user.first_name} {user.last_name} successfully.')
            return redirect('view_customer', uid)

        else:
            messages.error(request, 'You did not select anything', extra_tags='warning')
            return redirect('view_customer', uid)

    if pending_loans:
                
        all_loans_filtered = Loan.objects.prefetch_related('owner').filter(owner_id=user).all()
        
        #for pending loans table
        pending = 1
        all_loans_filtered_pending = Loan.objects.prefetch_related('owner').filter(owner_id=user, category="PENDING").all()
        pending_sum = all_loans_filtered_pending.aggregate(sum=Sum('amount'))['sum']
        expected_interests_sum = all_loans_filtered_pending.aggregate(sum=Sum('interest'))['sum']
        expected_repayments_sum = all_loans_filtered_pending.aggregate(sum=Sum('repayment_amount'))['sum']
        
        #for other loans
        others = 1
        all_loans_filtered_withoutpending = Loan.objects.prefetch_related('owner').filter(owner_id=user).exclude(category="PENDING").all()
        funded_sum = all_loans_filtered_withoutpending.aggregate(sum=Sum('amount'))['sum']
        interests_sum = all_loans_filtered_withoutpending.aggregate(sum=Sum('interest'))['sum']
        totalloan_sum = all_loans_filtered_withoutpending.aggregate(sum=Sum('total_loan_amount'))['sum']
        repayments_sum = all_loans_filtered_withoutpending.aggregate(sum=Sum('repayment_amount'))['sum']
        arrears_sum = all_loans_filtered_withoutpending.aggregate(sum=Sum('total_arrears'))['sum']
        defaultinterests_sum = all_loans_filtered_withoutpending.aggregate(sum=Sum('default_interest_receivable'))['sum']
        outstanding_sum = all_loans_filtered_withoutpending.aggregate(sum=Sum('total_outstanding'))['sum']
        
        context = {
                'nav': 'customers',
                'user':user, 
                'smeprofile': smeprofile,
                'pending': pending,
                'others': others,
                'pending_sum': pending_sum,
                'expected_interests_sum': expected_interests_sum,
                'expected_repayments_sum': expected_repayments_sum,
                'all_loans': all_loans,
                'all_loans_filtered': all_loans_filtered,
                'pending_loans': pending_loans,
                'running_loans':running_loans,
                'defaulted_loans': defaulted_loans,
                'completed_loans':completed_loans,
                'recovery_loans':recovery_loans,
                'funded_sum': funded_sum,
                'interests_sum': interests_sum,
                'totalloan_sum': totalloan_sum,
                'repayments_sum': repayments_sum,
                'arrears_sum': arrears_sum,
                'defaultinterests_sum': defaultinterests_sum,
                'outstanding_sum': outstanding_sum,  
                'locationlist': locationlist,
                'stafflist': stafflist, 
                'officer_fullname' : officer_fullname, 
                'loanfile': loanfile,  
                
                'yef': yef,
                'age': age,

                
            }          
    
        return render(request, 'view_customer.html', context) 
                    
    else:
        
        pending = 0
        others = 1
        all_loans_filtered = Loan.objects.prefetch_related('owner').filter(owner_id=user).exclude(category="PENDING").all()
        funded_sum = all_loans_filtered.aggregate(sum=Sum('amount'))['sum']
        interests_sum = all_loans_filtered.aggregate(sum=Sum('interest'))['sum']
        totalloan_sum = all_loans_filtered.aggregate(sum=Sum('total_loan_amount'))['sum']
        repayments_sum = all_loans_filtered.aggregate(sum=Sum('repayment_amount'))['sum']
        arrears_sum = all_loans_filtered.aggregate(sum=Sum('total_arrears'))['sum']
        defaultinterests_sum = all_loans_filtered.aggregate(sum=Sum('default_interest_receivable'))['sum']
        outstanding_sum = all_loans_filtered.aggregate(sum=Sum('total_outstanding'))['sum']
                 
        context = {
                    'nav': 'customers',
                    'suser': suser,
                    'user':user, 
                    'pending': pending,
                    'others': others,
                    'smeprofile': smeprofile,
                    'all_loans': all_loans,
                    'all_loans_filtered': all_loans_filtered,
                    'pending_loans': pending_loans,
                    'running_loans':running_loans,
                    'defaulted_loans': defaulted_loans,
                    'completed_loans':completed_loans,
                    'recovery_loans':recovery_loans,
                    'funded_sum': funded_sum,
                    'interests_sum': interests_sum,
                    'totalloan_sum': totalloan_sum,
                    'repayments_sum': repayments_sum,
                    'arrears_sum': arrears_sum,
                    'defaultinterests_sum': defaultinterests_sum,
                    'outstanding_sum': outstanding_sum,   
                    'locationlist': locationlist,
                    'stafflist': stafflist,
                    'officer_fullname' : officer_fullname,
                    'loanfile': loanfile,
                    
                    'yef': yef,
                    'age': age,
                }          

        return render(request, 'view_customer.html', context)  

@admin_check
def inform_account_activation(request, uid):
    user = UserProfile.objects.get(pk=uid)

    data_needed = []
    if user.date_of_birth:
        data_needed = data_needed
    else: 
        dob = 'DATE OF BIRTH'
        data_needed.append(dob)
    
    if user.start_date:
        data_needed = data_needed
    else:
        start_date = 'WORK START DATE'
        data_needed.append(start_date)
    
    if user.terms_consent == 'YES':
        data_needed = data_needed
    else:
        terms_consent = 'CONSENT TO TERMS AND CONDITIONS'
        data_needed.append(terms_consent)

    if user.credit_consent == 'YES':
        data_needed = data_needed
    else:
        credit_consent = 'CONSENT TO CREDIT DATA'
        data_needed.append(credit_consent)

    if user.passport_url or user.nid_url:
        data_needed = data_needed
    else:
        urlpn = 'UPLOAD PASSPORT OR NID COPY'
        data_needed.append(urlpn)

    if user.job_title:
        data_needed = data_needed
    else:
        jobtitle = 'JOB TITLE'
        data_needed.append(jobtitle)
    if user.gross_pay == 0:
        grosspay = 'GROSS PAY'
        data_needed.append(grosspay)
    else:
        data_needed = data_needed

    message_string = ''
    for i in data_needed:
        message_string = message_string + i + '<br>'

    subject = "More Information required for PROFILE ACTIVATION"
    ''' if header_cta == 'yes' '''
    cta_label = ''
    cta_link = ''

    greeting = f'Hi {user.first_name},'
    message = f'This is regarding your profile activation. You still need to update your profile with the following required information.'
    message_details = message_string

    ''' if cta == 'yes' '''
    cta_btn1_label = 'Login into Dashboard'
    cta_btn1_link = f'{settings.DOMAIN}/dashboard/'
    cta_btn2_label = ''
    cta_btn2_link = ''

    ''' if promo == 'yes' '''
    catchphrase = ''
    promo_title = ''
    promo_message = ''
    promo_cta = ''
    promo_cta_link = ''
    
    email_content = render_to_string('custom/email_temp_general.html', {
        'header_cta': 'no',
        'cta': 'no',
        'cta_btn2': 'no',
        'promo': 'no',
        'cta_link': cta_link,
        'cta_label': cta_label,
        'subject': subject,
        'greeting': greeting,
        'message': message,
        'message_details': message_details,
        'cta_btn1_link': cta_btn1_link,
        'cta_btn1_label': cta_btn1_label,
        'cta_btn2_link': cta_btn2_link,
        'cta_btn2_label': cta_btn2_label,
        'catchphrase': catchphrase,
        'promo_title': promo_title,
        'promo_message': promo_message,
        'promo_cta_link': promo_cta_link,
        'promo_cta': promo_cta,
        'user': user,
        'domain': domain,
        
        
    })
    
    text_content = strip_tags(email_content)
    email = EmailMultiAlternatives(subject,text_content,sender,['dev@webmasta.com.pg', user.email ])
    email.attach_alternative(email_content, "text/html")

    try: 
        email.send()
        messages.success(request, "Customer has been notified of all missing required information")
        return redirect('view_customer', uid)
    except:
        messages.error(request, 'Message has not been sent.', extra_tags='danger')
        
    return redirect('view_customer', uid)

