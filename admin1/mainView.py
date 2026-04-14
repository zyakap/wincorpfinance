import datetime
from django.utils import timezone
import re
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from pyparsing import empty
from socket import gaierror
from accounts.models import User, UserProfile
from loan.models import Loan, Statement, Payment, PaymentUploads

from .forms import AdminSettingsForm
from .models import AdminSettings

from django.contrib.sites.shortcuts import get_current_site

#EMAIL SETTINGS
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.html import strip_tags
#admin sender email
from admin1.models import AdminSettings
sender = settings.DEFAULT_SENDER_EMAIL

#Class Based Views
from django.views.generic.base import View
from wkhtmltopdf.views import PDFTemplateResponse

from django.db.models import Sum

from accounts.functions import admin_check

#########################
####   PAGES
#########################

@admin_check
def messages_admin(request):
    
    return render(request, 'messages_admin.html', {'nav': 'messages_admin'})

@admin_check
def support_system_admin(request):
    
    return render(request, 'support_system_admin.html', {'nav': 'support_system_admin'})

def admin_instructions(request):
    return render(request, 'admin_instructions.html', {'nav': 'admin_instructions'})

#########################
####   SETTINGS
#########################

@admin_check
def admin_dashboard(request):
    
    today = datetime.datetime.now()
    day = datetime.datetime.now().day
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year
    format = '%Y-%m-%d'
    
    if day in range(1,8):
        startdate = f'{year}-{month}-1'
        enddate = f'{year}-{month}-7'
        start_date = datetime.datetime.strptime(startdate, format)
        end_date = datetime.datetime.strptime(enddate, format)
    elif day in range(8,15):
        startdate = f'{year}-{month}-8'
        enddate = f'{year}-{month}-14'
        start_date = datetime.datetime.strptime(startdate, format)
        end_date = datetime.datetime.strptime(startdate, format)
    elif day in range(15, 22):
        startdate = f'{year}-{month}-15'
        enddate = f'{year}-{month}-21'
        start_date = datetime.datetime.strptime(startdate, format)
        end_date = datetime.datetime.strptime(startdate, format)
    else:
        if month in (1,3,5,7,8,10,12):
            startdate = f'{year}-{month}-22'
            enddate = f'{year}-{month}-31'
            start_date = datetime.datetime.strptime(startdate, format)
            end_date = datetime.datetime.strptime(startdate, format)
        elif month == 2:
            startdate = f'{year}-{month}-22'
            enddate = f'{year}-{month}-28'
            start_date = datetime.datetime.strptime(startdate, format)
            end_date = datetime.datetime.strptime(startdate, format)
        else:
            startdate = f'{year}-{month}-22'
            enddate = f'{year}-{month}-30'
            start_date = datetime.datetime.strptime(startdate, format)
            end_date = datetime.datetime.strptime(startdate, format)

    
    # transactions
    totalpayments = Payment.objects.filter(date__gte=start_date, date__lte=end_date).aggregate(sum=Sum('amount'))['sum']   
    totalexpected = Loan.objects.filter(next_payment_date__gte=start_date, next_payment_date=end_date).aggregate(sum=Sum('repayment_amount'))['sum'] 
    totaldefaults = Statement.objects.filter(date__gte=start_date, date__lte=end_date, type="DEFAULT").aggregate(sum=Sum('credit'))['sum']   
    payment_uploads_count = PaymentUploads.objects.filter(status="UPLOADED").count()
    
    #loans
    loans_funded = Loan.objects.filter(category='FUNDED', funding_date__gte=start_date, funding_date__lte=end_date)
    total_loans_funded = loans_funded.aggregate(sum=Sum('amount'))['sum']
    total_expected_interest = loans_funded.aggregate(sum=Sum('interest'))['sum']
    loans_pending = Loan.objects.filter(category='PENDING')
    totalpending = loans_pending.aggregate(sum=Sum('amount'))['sum']
    loans_pending_funding = Loan.objects.filter(category='PENDING', status='APPROVED')
    totalpending_funding = loans_pending_funding.aggregate(sum=Sum('amount'))['sum']


     #for new dashboard
    pending_loans = loans_pending_funding[:3]
    pending_loans_count = loans_pending_funding.count()
    awaiting_tc_loans = loans_pending.filter(status='AWAITING T&C').count()
    under_review_loans = loans_pending.filter(status='UNDER REVIEW').count()
    on_hold_loans = loans_pending.filter(status='ON HOLD').count()
    approved_loans = loans_pending.filter(status='APPROVED').count()
   
    print('PRINTING ATC LOANS:')
    print(awaiting_tc_loans)
    print(under_review_loans)
    print(on_hold_loans)
    print(approved_loans)
  

    atcllabel = f'Awaiting T&C'
    urllabel = f'Under Review'
    ohllabel = f'On Hold'
    allabel = f'Approved'
 
    
    

    pendingloanlabels =[atcllabel,
                urllabel,
                ohllabel,
                allabel,
         
                ]

    pendingloansdata = [awaiting_tc_loans,
            under_review_loans,
            on_hold_loans,
            approved_loans,
      
            ]

    #funded loans breakup
    fundedloans = Loan.objects.filter(category='FUNDED')
    arfloans = fundedloans.filter(funded_category='ACTIVE', status="RUNNING").count()
    adfloans = fundedloans.filter(funded_category='ACTIVE', status="DEFAULTED").count()
    rfloans = fundedloans.filter(funded_category='RECOVERY').count()
    bfloans = fundedloans.filter(funded_category='BAD').count()
    print('FUNDED LOANS:::')
    print(fundedloans)

    arfloansl = f'Running'
    adfloansl = f'Defaulted'
    rfloansl = f'In Recovery'
    bfloansl = f'Bad'
    
    arfloanslabels =[arfloansl,
                adfloansl,
                rfloansl,
                bfloansl,
                ]

    arfloansdata =[arfloans,
                adfloans,
                rfloans,
                bfloans,
                ]
    


    
    logins = UserProfile.objects.filter(login_timestamp__gte=start_date, login_timestamp__lte=end_date).count()
    registered = UserProfile.objects.filter(created_at__gte=start_date, created_at__lte=end_date).count()
    pending_activation =  UserProfile.objects.filter(activation=0).count()
    defaulted_customers = UserProfile.objects.filter(in_recovery=1).count()

    pending_activation_list = UserProfile.objects.filter(activation=0)[:3]
    
    
    day1 = start_date
    day2 = start_date + datetime.timedelta(days=1)
    day3 = start_date + datetime.timedelta(days=2)
    day4 = start_date + datetime.timedelta(days=3)
    day5 = start_date + datetime.timedelta(days=4)
    day6 = start_date + datetime.timedelta(days=5)
    day7 = start_date + datetime.timedelta(days=6)
    
    days = [day1, day2, day3, day4, day5, day6, day7]
   
    pays = []
    apps = []
    logs = []
    weekdays = []
    for day in days:
        cwkstarttime = datetime.datetime.combine(day, datetime.datetime.min.time())
        cwkendtime = datetime.datetime.combine(day, datetime.datetime.max.time())
        pays.append(Payment.objects.filter(date=day).count())
        apps.append(Loan.objects.filter(application_date = day).count())
        logs.append(UserProfile.objects.filter(login_timestamp__gte=cwkstarttime, login_timestamp__lte=cwkendtime).count())

        weekdays.append(day.strftime('%A')[0:3])
    
    prevwkstart = start_date - datetime.timedelta(days=7)
    prevwkend = start_date - datetime.timedelta(days=1)
    
    cwkstarttime = datetime.datetime.combine(start_date, datetime.datetime.min.time())
    cwkendime = datetime.datetime.combine(end_date, datetime.datetime.max.time())
    pwkstarttime = datetime.datetime.combine(prevwkstart, datetime.datetime.min.time())
    pwkendime = datetime.datetime.combine(prevwkend, datetime.datetime.max.time())
    
    appscurwk = Loan.objects.filter(application_date__gte = start_date, application_date__lte=end_date).count()
    payscurwk = Payment.objects.filter(date__gte=start_date, date__lte=end_date).count()
    logscurwk = UserProfile.objects.filter(login_timestamp__gte=cwkstarttime, login_timestamp__lte=cwkendime).count()
    appsprevwk = Loan.objects.filter(application_date__gte = prevwkstart, application_date__lte=prevwkend).count()
    paysprevwk = Payment.objects.filter(date__gte=prevwkstart, date__lte=prevwkend).count()
    logsprevwk = UserProfile.objects.filter(login_timestamp__gte=pwkstarttime, login_timestamp__lte=pwkendime).count()  
    
    appspercentthiswk = 0
    payspercentthiswk = 0
    logspercentthiswk = 0
    
    if 0 != appscurwk or 0 != appsprevwk:
        appspercentthiswk = (appscurwk-appsprevwk/(appscurwk+appsprevwk)) * 100.0
    if 0 != payscurwk or 0 != paysprevwk:
        payspercentthiswk = (payscurwk-paysprevwk/(payscurwk+paysprevwk)) * 100.0
    if 0 != logscurwk or 0 != logsprevwk:
        logspercentthiswk = (logscurwk-logsprevwk/(logscurwk+logsprevwk)) * 100.0
    
    print(payspercentthiswk)
    
    
    try:
        latestpayment = Payment.objects.order_by('-date')[0].date
        paydaysago = today - latestpayment
    except:
        paydaysago = '0'
    
    try:
        latestloan = Loan.objects.order_by('-funding_date')[0].funding_date
        loandaysago = today - latestloan
    except:
        loandaysago = '0'
    
    try:
        latestcustomer = UserProfile.objects.order_by('-login_timestamp')[0].login_timestamp
    except:
        latestcustomer = 0
    
        
    context = {
        
        'nav': 'admin_dashboard',
        'totalpayments': totalpayments,
        'totalexpected': totalexpected,
        'totaldefaults': totaldefaults,
        'payment_uploads': payment_uploads,
        'loans_funded': loans_funded,
        'total_loans_funded': total_loans_funded,
        'total_expected_interest':total_expected_interest,
        'loans_pending': loans_pending,
        'totalpending': totalpending,
        'loans_pending_funding': loans_pending_funding,
        'totalpending_funding': totalpending_funding,
        'logins': logins,
        'registered': registered,
        'pending_activation': pending_activation,
        'defaulted_customers': defaulted_customers,   
        'pays': pays,
        'apps': apps,
        'logs': logs,
        'weekdays': weekdays, 
        'appspercentthiswk': appspercentthiswk,
        'payspercentthiswk': payspercentthiswk,
        'logspercentthiswk': logspercentthiswk,
        'paydaysago': paydaysago,
        'loandaysago': loandaysago,
        'latestcustomer': latestcustomer,

        'pending_loans': pending_loans,
        'pendingloanlabels': pendingloanlabels,
        'pendingloansdata' : pendingloansdata,

        'arfloanslabels': arfloanslabels,
        'arfloansdata' : arfloansdata,
        'pending_loans_count': pending_loans_count,
        'pending_activation_list': pending_activation_list,
        'payment_uploads_count': payment_uploads_count,
   
    }
    
    
    
   
    
    return render(request, 'admin_dashboard.html', context )

@admin_check
def admin_settings(request):
    
    try:
        setting1 = AdminSettings.objects.get(settings_name="setting1")
        initial_data = {
            'interest_type': setting1.interest_type,
            'interest_rate': setting1.interest_rate,
            'loanref_prefix': setting1.loanref_prefix,
            'admin_email_addresses': setting1.admin_email_addresses,
            'default_from_email': setting1.default_from_email,
            'support_email': setting1.support_email,
            'approval_credit_threshold': setting1.approval_credit_threshold,
            'credit_check': setting1.credit_check,
            'percentage_of_gross': setting1.percentage_of_gross,
            'processing_fee': setting1.processing_fee,
            'processing_amount': setting1.processing_amount,
            
        }
    except:
        initial_data = {
            'interest_rate': 0,
            'loanref_prefix': 'iSL',
        }
        
    
    if request.method == 'POST':
        form = AdminSettingsForm(request.POST)
        if form.is_valid():
            try:
                setting1 = AdminSettings.objects.get(settings_name="setting1")
            except: 
                AdminSettings.objects.create(settings_name = 'setting1', interest_rate = 00.00)
                setting1 = AdminSettings.objects.get(settings_name="setting1")
            
            setting1.interest_type = form.cleaned_data['interest_type']
            setting1.save()
            setting1.interest_rate = form.cleaned_data['interest_rate']
            setting1.save()
            setting1.loanref_prefix = form.cleaned_data['loanref_prefix']
            setting1.save()
            if form.cleaned_data['admin_email_addresses']:
                setting1.admin_email_addresses = form.cleaned_data['admin_email_addresses']
                setting1.save()
            setting1.default_from_email = form.cleaned_data['default_from_email']
            setting1.save()
            setting1.support_email = form.cleaned_data['support_email']
            setting1.save()
            
            setting1.approval_credit_threshold = form.cleaned_data['approval_credit_threshold']
            setting1.save()
            setting1.credit_check = form.cleaned_data['credit_check']
            setting1.save()
            setting1.percentage_of_gross = form.cleaned_data['percentage_of_gross']
            setting1.save()
            setting1.processing_fee = form.cleaned_data['processing_fee']
            setting1.save()
            setting1.processing_amount = form.cleaned_data['processing_amount']
            setting1.save()
            
            messages.success(request, f"Admin Settings have been updated.")
            return redirect('admin_settings')
    else:
        form = AdminSettingsForm(initial=initial_data)
    
    return render(request, 'settings.html', {'form': form})

@admin_check
def locations(request):
    
    return render(request, 'locations.html')

class DownloadApplicationByAdmin(View):
    
    template = 'custom/customer_statement.html'
    
    def get(self, request, *args, **kwargs):
        
        loan_ref = self.kwargs['loanref']
        ##loan_ref = 'iBX1ZY264'
        loan = Loan.objects.get(ref=loan_ref)
        domain = settings.DOMAIN
        uid = loan.owner_id
        user = UserProfile.objects.get(pk=uid)
        usr = User.objects.get(pk=user.user_id)

        statements = Statement.objects.filter(loanref=loan)
        
        now = datetime.datetime.now()
        today = now.strftime("%d/%m/%Y")
        print(today)
        print(now)

        
        last_name_s = user.last_name[-1]
        
        data = {'loan':loan, 'user':user, 'usr': usr, 'last_name_s':last_name_s, 'domain': domain, 'statements': statements, 'today':today }
        
        response = PDFTemplateResponse(
            request=request,
            template = self.template,
            filename = f'{loan.ref}.pdf',
            context = data,
            show_content_in_browser=False,
            cmd_options= {
            
                "zoom":1,
                "viewport-size": "1366 x 513",
                'javascript-delay': 1000,
                'footer-center': '[page]/[topage]',
                "no-stop-slow-scripts": True,
            },
        )
        
        return response


    
@admin_check
def make_default(request, loan_ref):
    
    if not request.user.is_authenticated:
        return redirect('login_user')
    
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.", extra_tags="danger")
        return redirect( 'dashboard')
    
    loan = Loan.objects.get(ref=loan_ref) 
    ref = loan
    date = loan.next_payment_date
    amount = loan.repayment_amount
    balance = loan.total_outstanding
    arrears = loan.total_arrears
    
    stat = Statement.objects.create(loanref=ref, date=date, default_amount=amount, statement='DEFAULT')
    stat.uid = loan.owner.uid
    stat.luid = settings.LUID
    stat.save()
        
    all_statements = Statement.objects.filter(loanref=loan).all().count()     
    stat.s_count = all_statements
    stat.ref = f'{loan_ref}SD{stat.s_count}' 
    stat.save()
    
    int_on_def = Decimal(0.2) * amount
    new_balance = balance + int_on_def
    new_arrears = arrears + amount
    
    stat.interest_on_default = int_on_def
    stat.balance = new_balance
    stat.arrears = new_arrears
    stat.save()
    
    loan.last_default_date = date
    last_default_amount = amount
    loan.number_of_defaults += 1
    loan.total_arrears = new_arrears
    loan.default_interest_receivable += int_on_def
    loan.total_outstanding = new_balance
    loan.next_payment_date = date + datetime.timedelta(days=14)
    loan.category = 'CURRENT-DEFAULTED'
    loan.status = 'DEFAULTED'
    loan.save()
    
    messages.error(request, 'DEFAULT UPDATED SUCCESSFULLY', extra_tags='info')
    
    return redirect('loans')

class DownloadLoanStatement(View):
    
    template = 'custom/customer_statement.html'
    
    def get(self, request, *args, **kwargs):
        domain = settings.DOMAIN
        loan_ref = self.kwargs['loanref']
        ##loan_ref = 'iBX1ZY264'
        loan = Loan.objects.get(ref=loan_ref)

        uid = loan.owner_id
        user = UserProfile.objects.get(pk=uid)
        usr = User.objects.get(pk=user.user_id)
        
        last_name_s = user.last_name[-1]

        today = datetime.date.today().strftime('%x')
        
        statements = Statement.objects.filter(loanref=loan)
      
        
        data = {'loan':loan, 'user':user, 'usr': usr, 'last_name_s':last_name_s, 'statements': statements, 'domain': domain, 'today': today }
        
        response = PDFTemplateResponse(
            request=request,
            template = self.template,
            filename = f'{loan.ref}-Statement.pdf',
            context = data,
            show_content_in_browser=False,
            cmd_options= {
                'margin-top':10,
                "zoom":0.8,
                "viewport-size": "1366 x 513",
                'javascript-delay': 1000,
                'footer-center': '[page]/[topage]',
                "no-stop-slow-scripts": True,
            },
        )
        
        return response
    
@admin_check
def reports(request):  

    return render(request, 'reports.html', {'nav': 'reports'})



@admin_check
def transactions(request):
    
    transactions = Statement.objects.prefetch_related('loanref','owner').order_by('-date')
   
    return render(request, 'transactions.html', { 'transactions': transactions })

@admin_check
def statements(request):

    transactions = Statement.objects.prefetch_related('loanref','owner').filter(type='PAYMENT').order_by('-date')
    
    return render(request, 'statements.html', { 'transactions': transactions })

@admin_check
def payments(request):

    transactions = Payment.objects.prefetch_related('loanref','owner').order_by('-date')
    
    return render(request, 'payments.html', { 'transactions': transactions })

@admin_check
def defaults(request):

    transactions = Statement.objects.prefetch_related('loanref','owner').filter(type='DEFAULT').order_by('-date')
    
    return render(request, 'defaults.html', { 'transactions': transactions })

@admin_check
def payment_uploads(request):

    payment_uploads = PaymentUploads.objects.prefetch_related('owner','loan').filter(status="UPLOADED")
    completed_uploads = PaymentUploads.objects.prefetch_related('owner','loan').filter(status="PROCESSED")

    return render(request, 'payment_uploads.html', {'nav': 'payment_uploads', 'payment_uploads': payment_uploads, 'completed_uploads': completed_uploads})

@admin_check
def process_upload(request, ref):

    payment_upload = PaymentUploads.objects.get(ref=ref)
    
    payment_upload.status = 'PROCESSED'
    payment_upload.save()
    messages.success(request, f"Payment upload {ref} has been processed.")

    payment_uploads = PaymentUploads.objects.prefetch_related('owner','loan').filter(status="UPLOADED")
    completed_uploads = PaymentUploads.objects.prefetch_related('owner','loan').filter(status="PROCESSED")


    return render(request, 'payment_uploads.html', {'nav': 'payment_uploads', 'payment_uploads': payment_uploads, 'completed_uploads': completed_uploads})

@admin_check
def admin_run_defaults(request):

    loans = Loan.objects.filter(category='FUNDED', funded_category='ACTIVE')

    for loan in loans:
        if loan.next_payment_date < datetime.date.today():
            default_interest = settings.DEFAULT_INTEREST_RATE * loan.repayment_amount
            loan.last_default_date = datetime.date.today()
            loan.number_of_defaults += 1
            loan.last_default_amount = loan.repayment_amount
            if loan.total_arrears < loan.total_outstanding:
                loan.total_arrears += loan.repayment_amount
            else:
                loan.total_arrears = loan.total_outstanding
            loan.total_outstanding += default_interest
            loan.status = 'DEFAULTED'
            loan.save()

            rounded_default_interest = round(default_interest,2)
            rounded_total_outstanding = round(loan.total_outstanding, 2)

            stat = Statement.objects.create(owner=loan.owner, ref = f'{loan.ref}D{loan.number_of_defaults}', loanref = loan, type="DEFAULT", statement="Loan Defaulted", debit=0, credit=default_interest, arrears=loan.total_arrears, balance=loan.total_outstanding, date = datetime.date.today(), default_amount=loan.repayment_amount, interest_on_default=default_interest)
            stat.save()

            messages.success(request, f"Default for {loan.ref} has been created successfully...")

            while loan.next_payment_date < datetime.date.today():
                loan.next_payment_date = loan.next_payment_date + datetime.timedelta(days=14)
                loan.save()
                messages.success(request, f"Next Payment Date for {loan.ref} has been updated successfully...")

            user = loan.owner
            #send email to user
            subject = f'{loan.ref} is in DEFAULT'
            ''' if header_cta == 'yes' '''
            cta_label = 'View Loan'
            cta_link = f'{settings.DOMAIN}/loan/myloan/{loan.ref}/'

            greeting = f'Hi {loan.owner.first_name}'
            message = 'You have defaulted on your loan repayment.'
            message_details = f'Default Interest Accumulated: K{rounded_default_interest}<br>\
                                Number of Defaults: {loan.number_of_defaults}<br>\
                                Total Arrears: K{round(loan.total_arrears,2)}<br>\
                                TOTAL BALANCE: K{rounded_total_outstanding}'

            ''' if cta == 'yes' '''
            cta_btn1_label = 'View Loan'
            cta_btn1_link = f'{settings.DOMAIN}/loan/myloan/{loan.ref}/'
            cta_btn2_label = ''
            cta_btn2_link = ''

            ''' if promo == 'yes' '''
            catchphrase = 'FUNDING?'
            promo_title = 'YOU WILL GET A FUNDING ALERT'
            promo_message = 'Once the loan is funded, you will get a funding notice in your email.'
            promo_cta = ''
            promo_cta_link = ''
            
            email_content = render_to_string('custom/email_temp_general.html', {
                'header_cta': 'no',
                'cta': 'yes',
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
            
            #recipients
            email_list_one = [user.email, 'dev@webmasta.com.pg']
            email_list_two = settings.DEFAULTS_EMAIL
            email_list  = email_list_one + email_list_two

            text_content = strip_tags(email_content)
            email = EmailMultiAlternatives(subject,text_content,sender,email_list)
            email.attach_alternative(email_content, "text/html")
            
            try: 
                email.send()
                messages.success(request, f'Loan Default Processed and {loan.owner.first_name} {loan.owner.last_name} notified successfully.')
            except:
                messages.error(request, 'Loan Default notice not sent.', extra_tags='danger')
            
    return redirect('admin_dashboard')
 

    
@admin_check
def create_default(request, loan_ref):
    
    if not request.user.is_authenticated:
        return redirect('login_user')
    
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to view this page.", extra_tags="danger")
        return redirect( 'dashboard')
    
    loan = Loan.objects.get(ref=loan_ref) 
    ref = loan
    date = loan.next_payment_date
    amount = loan.repayment_amount
    balance = loan.total_outstanding
    arrears = loan.total_arrears
    
    stat = Statement.objects.create(loanref=ref, date=date, default_amount=amount, statement='LOAN DEFAULTED')
    stat.uid = loan.owner.uid
    stat.owner = loan.owner
    stat.luid = settings.LUID
    
    stat.save()
        
    all_statements = Statement.objects.filter(loanref=loan).all().count()     
    stat.s_count = all_statements
    stat.ref = f'{loan_ref}SD{stat.s_count}' 
    stat.save()
    
    int_on_def = settings.DEFAULT_INTEREST_RATE * amount
    new_balance = balance + int_on_def
  
    if arrears >= balance:
        new_arrears = new_balance
    else:
        new_arrears = arrears + amount
    
    stat.default_interest = int_on_def
    stat.credit = int_on_def
    stat.balance = new_balance
    stat.arrears = new_arrears
    stat.type = 'DEFAULT'
    stat.save()
    
    loan.last_default_date = date
    last_default_amount = amount
    loan.number_of_defaults += 1
    loan.total_arrears = new_arrears
    loan.default_interest_receivable += int_on_def
    loan.total_outstanding = new_balance
    
    # Get the list of repayment dates
    date = datetime.datetime(date.year, date.month, date.day)
    repayment_dates = loan.get_repayment_dates()
    if date >= datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d'):
        current_last_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
        repayment_dates.pop(0)
        if len(repayment_dates) == 0:
            next_date = current_last_date + datetime.timedelta(days=14)
            repayment_dates.append(next_date.strftime('%Y-%m-%d'))
        loan.set_repayment_dates(repayment_dates)
        loan.save()
    print(f'DEFAULT: NEXT REPAYMENT DATE IS: {repayment_dates[0]}')
    loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
    loan.save()
    
    
    loan.status = 'DEFAULTED'
    loan.save()
    
    messages.error(request, 'DEFAULT UPDATED SUCCESSFULLY', extra_tags='info')
    
    return redirect('view_loan', loan.ref)
