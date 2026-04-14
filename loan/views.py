
#from cgi import FieldStorage
#from distutils.command.upload import upload
import datetime
import random
from os import terminal_size
from socket import gaierror
from decimal import Decimal
from django.conf import settings
#from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.test import TransactionTestCase

from accounts.models import UserProfile, StaffProfile
from loan.models import Loan, LoanFile, Statement, PaymentUploads, Payment
from admin1.models import AdminSettings
from django.contrib.sites.shortcuts import get_current_site
#from django.http import HttpResponse
from .forms import LoanApplicationForm, PaymentUploadForm
from loan.forms import PaymentForm
#from .models import UserProfile
from django.contrib import messages

#celery
from .tasks import download_tc


#Class Based Views
from django.views.generic.base import View
from wkhtmltopdf.views import PDFTemplateResponse

#TOKENIZER
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode
from .tokens import loan_tc_agreement_token
from django.core.files.storage import FileSystemStorage

#EMAIL SETTINGS
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.html import strip_tags
from django.template import Template, Context
#admin sender email
from admin1.models import AdminSettings

try:
    settings1 = AdminSettings.objects.get(settings_name='setting1')
    sender = settings1.default_from_email
    admin_receiver = settings1.admin_email_addresses
    test_receiver = settings.TEST_RECEIVER
except:
    sender = settings.DEFAULT_FROM_EMAIL
    admin_receiver = settings.ADMIN_RECEIVER
    test_receiver = settings.TEST_RECEIVER
admin_emails = list(admin_receiver.split(','))
if test_receiver != '':
    admin_emails.append(test_receiver)

from django.conf import settings
sender = settings.DEFAULT_SENDER_EMAIL

from accounts.functions import login_check, check_staff

from custom.functions import repayment, complete_loan, combination_check

from message.functions import send_email, send_email_toworkemail, email_admin

from .functions import process_advance_payment, process_repayment, process_default

User = get_user_model()
user = User()


from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import subprocess

domain = settings.DOMAIN_DNS
domain_full = settings.DOMAIN

from custom.functions import combination_check, fn_limits

def generate_pdf(templatefile, data):
    # Load the template
    env = Environment(loader=FileSystemLoader('custom/templates'))
    template = env.get_template(templatefile)
    # Render the template with the data
    html = template.render(data)
    result = html
    
    # Create the PDF
    pdf = subprocess.Popen(['wkhtmltopdf', '-', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    pdf_data, _ = pdf.communicate(html.encode('utf-8'))
    #pdf_data = pdf_data.encode('latin1', 'ignore')
    return pdf_data


#### GENERAL PAGES #####


class DownloadApplication(View):
    
    template = 'custom/loan_application_gen.html'
    
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
        
        data = {'loan':loan, 
                'user':user, 
                'usr': usr, 
                'loan': loan,
                'last_name_s':last_name_s, 
                'domain': domain, 
                'statements': statements, 
                'domain': settings.DOMAIN,
                'settings': settings,
                'today':today }
        
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

class DownloadStatement(View):
    
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






@login_check
def loan_requirements(request):

    user = UserProfile.objects.get(user_id=request.user.id)
    now = datetime.date.today()

    
    dob = user.date_of_birth
    start = user.start_date
    
    if dob:
        age = round(((now.month - dob.month + (12 * (now.year - dob.year)))/12),2)
    else:
        age = None
    
    if start:
        yef = round(((now.month - start.month + (12 * (now.year - start.year)))/12),2)
    else:
        yef = None

    from django.db.models import Q
    # Combine the two queries into one
    combined_query = Q(owner=user.id) & Q(category='PENDING') & (Q(status='AWAITING T&C') | Q(status='UNDER REVIEW'))
    # Retrieve loans matching the combined query
    combined_loans = Loan.objects.filter(combined_query)
    # Now combined_loans contains loans that satisfy both conditions
    
    if combined_loans:
        try:
            loan = Loan.objects.get(combined_query)
            loanfile = LoanFile.objects.get(loan=loan)
            return render(request, 'loan_requirements.html', {'nav': 'loan_requirements', 'user':user, 'age':age, 'yef':yef, 'loanfile': loanfile })
        except:
            pass

    if user.account_requirements_check == 'INCOMPLETE':
        if yef is not None and yef > 0.9 and user.terms_consent == 'YES' and user.credit_consent == 'YES' and (user.passport_url or user.nid_url) and user.job_title and user.gross_pay > 0 and age is not None and age < 60:
            user.account_requirements_check = 'COMPLETED'
            user.save()
    
    return render(request, 'loan_requirements.html', {'nav': 'loan_requirements', 'user':user, 'age':age, 'yef':yef})

#########################
#LOAN APPLICATION
#########################



@login_check
def loan_application_old(request):
    owner = UserProfile.objects.get(user_id=request.user.id)

    #try:
    #if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="ACTIVE"):
     #   messages.error(request, f"You already have an active loan. Please contact {settings.SUPPORT_EMAIL}", extra_tags="warning")
      #  return redirect('dashboard')
    if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="RECOVERY"):
        messages.error(request, f"You already have a loan in recovery. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
        return redirect('dashboard')
    if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="BAD"):
        messages.error(request, f"You already have a bad loan with us. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
        return redirect('dashboard')
    if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="WOFF"):
        messages.error(request, f"You already have a written-off loan with us. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
        return redirect('dashboard')
    if Loan.objects.filter(owner=owner, category="PENDING", status="AWAITING T&C"):
        messages.error(request, f"You already have a pending loan awaiting your action. Cancel that if you wish to apply for a new one.", extra_tags="warning")
        return redirect('myloans')
    if Loan.objects.filter(owner=owner, category="PENDING", status="UNDER REVIEW"):
        messages.error(request, f"You already have a pending loan under review. Cancel that if you wish to apply for a new one.", extra_tags="warning")
        return redirect('myloans')
    if Loan.objects.filter(owner=owner, category="PENDING", status="APPROVED"):
        messages.error(request, f"You already have a pending loan approved. Cancel that if you wish to apply for a new one.", extra_tags="warning")
        return redirect('myloans')
    #except:
    #    pass

    #redundant?
    owner.loan_statement1_url = None
    owner.loan_statement2_url = None
    owner.loan_statement3_url = None
    owner.bank_standing_order_url = None
    owner.bank_standing_order2_url = None
    owner.terms_conditions_url = None
    owner.application_form_url = None
    owner.stat_dec_url = None
    owner.irr_sd_form_url = None
    owner.super_statement_url = None
    owner.bank_statement_url = None
    owner.save()
    
    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact support@{domain}", extra_tags="danger")
        return redirect('dashboard')
    
    usr = request.user
    uid = usr.id
    loanref_prefix = loan_setting.loanref_prefix
    user = UserProfile.objects.get(user_id=uid)
    upid = user.id
    
    if user.first_name is None or user.first_name == '':
        messages.error(request, f"You need to update your profile with your First Name and Last Name.", extra_tags="warning")
        return redirect('profile')
    if user.last_name is None or user.last_name == '':
        messages.error(request, f"You need to update your profile with your First Name and Last Name.", extra_tags="warning")
        return redirect('profile')
    
    first_name = user.first_name
    last_name = user.last_name
    rand = random.randint(0,9)
    refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
    repayment_limit = user.repayment_limit
    
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            
            if loan_setting.credit_check == 'YES':
                if not usr.active:
                    return redirect('inactive')
                if usr.defaulted:
                    return redirect('defaulted')
                if usr.suspended:
                    return redirect('suspended')
                if usr.dcc_flagged:
                    return redirect('dcc_flagged')
                if usr.cdb_flagged:
                    return redirect('cdb_flagged')
            
            if user.repayment_limit == 0:
                messages.error(request, "Your repayment limit is not set. Please contact us by creating a support ticket", extra_tags="danger")
                return redirect('loan_application')
            if user.activation == 0:
                messages.error(request, "Your account is not activated. Please contact us by creating a support ticket", extra_tags="danger")
                return redirect('loan_application')

            #loan reference
            loan = Loan.objects.create(ref = refx)
            loanfile = LoanFile.objects.create(loan=loan)
            loanfile.save()
            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.save()

            loan.owner_id = upid
            #loan.loan_type = form.cleaned_data['type']
            loan.amount = form.cleaned_data['amount']

            #amount limit check
            if loan.amount < settings.LOAN_MIN_AMOUNT:
                loan.delete()
                messages.error(request, f'Loan amount must be more than K{ settings.LOAN_MIN_AMOUNT }', extra_tags='danger')
                return redirect('loan_application')
            elif loan.amount > settings.LOAN_MAX_AMOUNT:
                loan.delete()
                messages.error(request, f'Loan amount must be less than K{ settings.LOAN_MAX_AMOUNT }', extra_tags='danger')
                return redirect('loan_application')

            num_fns = form.cleaned_data['number_of_fortnights']

            #COMBINATIONS CHECK
            
            max_fn = combination_check(loan.amount, num_fns)
            if max_fn != 0:
                print(f'MAX FN: {max_fn}')
                
                loan.delete()
                messages.error(request, f"Number of fortnights must be between { settings.MIN_FN } and {max_fn} for an amount of K{loan.amount:,.2f}. Please refer to the repayment table below. Click on 'Show Repayment Table'.", extra_tags='danger')
                return redirect('loan_application')
            
            #COMBINATIONS CHECK _END

            if fn_limits(num_fns) != 1:
                loan.delete()
                messages.error(request, f"Number of fortnights must be between {settings.MIN_FN} and {settings.MAX_FN}.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.number_of_fortnights = num_fns
            start_of_payment = form.cleaned_data['repayment_start_date']
            now = datetime.date.today()
            after_fourteen_days = now + datetime.timedelta(days=14)
            
            if start_of_payment < now:
                loan.delete()
                messages.error(request, "The Start Date can not be in past. The date must be from now and 14 days.", extra_tags='danger')
                return redirect('loan_application')
            
            if start_of_payment > after_fourteen_days:
                loan.delete()
                messages.error(request, "The Start Date can not be after 14 days from now. The date must be between now and 14 days.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.repayment_start_date = start_of_payment
            loan.save()
            
            #calculating_interest
            selected_fns = loan.number_of_fortnights
            amt = float(loan.amount)

            interest_type = settings.INTEREST_TYPE

            fortnightly_repayment = repayment(amt, interest_type, selected_fns)
            print('fn_repayment')
            print(fortnightly_repayment)
            total_to_be_paid = fortnightly_repayment * selected_fns
            print('total_to_be_paid')
            print(total_to_be_paid)
            interest_to_be_paid = total_to_be_paid - amt
            print('interest_to_be_paid')
            print(interest_to_be_paid)
            
            rounded_interest = round(interest_to_be_paid,2)
            rounded_repayment_amount = round(fortnightly_repayment,2)     
            rounded_total_to_be_paid = round(total_to_be_paid, 2)
            
            if repayment_limit == 0:
                loan.delete()
                messages.error(request, 'Your repayment Limit is not set yet. Please make sure your payslip is uploaded.', extra_tags="danger")
                return redirect('dashboard')
            
            if fortnightly_repayment > repayment_limit:
                loan.delete()
                messages.error(request, f'The repayment amount of K{rounded_repayment_amount} for this loan is greater than your personal repayment limit of K{repayment_limit}. Please apply again within your repayment limit.', extra_tags='danger')
                return redirect('loan_application') 
            
            loan.interest = rounded_interest
            loan.repayment_frequency = 'FORTNIGHLTY'
            loan.category = 'PENDING'
            loan.status = 'AWAITING T&C'
            loan.location = owner.location
            loan.repayment_amount = rounded_repayment_amount
            loan.total_loan_amount = rounded_total_to_be_paid


            if settings.LOAN_TYPES != 1:
                messages.error(request, 'Administrator needs to enable loan type on application forms first. Please raise a support ticket for this.', extra_tags="danger")
                return redirect('loan_application')
            else:
                loan.loan_type = 'PERSONAL'
            
            # DCC IDENTIFIERS
            loan.uid = user.uid
            loan.luid = settings.LUID
            loan.save()
        
            messages.success(request, "Loan application sent successfully. Please check your email to complete the loan application process...")
            
            templatefileloc1 = 'custom/terms_conditions_gen.html'
            templatefileloc2 = 'custom/stat_dec_gen.html'
            templatefileloc3 = 'custom/irsda_gen.html'
            templatefileloc4 = 'custom/loan_application_gen.html'
            pdfddatacontext = {
                'domain': settings.DOMAIN,
                'loan': loan,
                'interest_rate': loan_setting.interest_rate,
                'user': user,
                'settings': settings
            }

            
            pdf_data1 = generate_pdf(templatefileloc1, pdfddatacontext)
            pdf_attachment1 = MIMEApplication(pdf_data1, _subtype='pdf')
            pdf_attachment1.add_header('content-disposition', 'attachment', filename='Terms_&_Conditions.pdf')
            
            pdf_data2 = generate_pdf(templatefileloc2, pdfddatacontext)
            pdf_attachment2 = MIMEApplication(pdf_data2, _subtype='pdf')
            pdf_attachment2.add_header('content-disposition', 'attachment', filename='Statutory_Declaration.pdf')

            pdf_data3 = generate_pdf(templatefileloc3, pdfddatacontext)
            pdf_attachment3 = MIMEApplication(pdf_data3, _subtype='pdf')
            pdf_attachment3.add_header('content-disposition', 'attachment', filename='IR_Salary_Deduction_Authority.pdf')
            
            pdf_data4 = generate_pdf(templatefileloc4, pdfddatacontext)
            pdf_attachment4 = MIMEApplication(pdf_data4, _subtype='pdf')
            pdf_attachment4.add_header('content-disposition', 'attachment', filename='Loan_Application.pdf')
            
            email_subject=f'Sign Required Documents for Loan - { final_ref }'
            #
            
            # HTML EMAIL
            html_content = render_to_string("custom/email_temp_general.html", {
                'subject': email_subject,
                'greeting': f'Hi {user.first_name}',
                'cta': 'yes',
                'cta_btn1_label': 'UPLOAD SIGNED DOCUMENTS',
                'cta_btn1_link': f'{settings.DOMAIN}/loan/myloan/{loan.ref}/',
                'message': f'Kindly find attached the Pre-filled Loan Application form, Terms and Conditions form, Statutory Declaration form and the Irreovocable Salary Deduction Authority form for your loan application.',
                'message_details': f'Please read through the documents and sign them. Once signed, please scan each signed document and upload them to complete your loan application. Loan decision will only be made once all these documents are signed and uploaded.',
                'user': usr,
                'userprofile': user,
                'loan': loan,
                'domain': settings.DOMAIN,
                'uid': urlsafe_base64_encode(force_bytes(usr.pk)),
                'token': loan_tc_agreement_token.make_token(usr),
            })
            
            text_content = strip_tags(html_content)

            email_list_one = [usr.email, 'dev@webmasta.com.pg']
            email_list_two = settings.APPLICATION_FORM_EMAIL
            email_list  = email_list_one + email_list_two

            
            email = EmailMultiAlternatives(email_subject, text_content, settings.EMAIL_HOST_USER, email_list)
            email.attach_alternative(html_content, "text/html")
            
            email.attach(pdf_attachment1)
            email.attach(pdf_attachment2)
            email.attach(pdf_attachment3)
            email.attach(pdf_attachment4)

            #clear existing loans that were not agreed to
            loans = Loan.objects.filter(owner=owner, tc_agreement='tct')
            print(loans)

            for loanx in loans:
                loanx.delete()
            try:
                email.send()
                loan.tc_agreement = 'tct'
                loan.save()
                messages.success(request, "The Terms & Conditions have been emailed to you, Please read, sign if you agree and upload in your requirements section.", extra_tags='info')
            except:
                messages.error(request, "The Terms & Conditions Agreement email could not be sent, make sure you have internet connection and try apply again.", extra_tags='danger')
                loan.delete()
                return redirect('loan_application')

            return redirect('dashboard')
    else:
        form = form = LoanApplicationForm()
        
    return render(request, 'loan_application_form.html', { 'nav':'loan_application', 'form': form, "repayment_limit": repayment_limit, 'user': user, 'settings': settings })


@login_check
def loan_application(request):
    owner = UserProfile.objects.get(user_id=request.user.id)

    if settings.MULTIPLE_LOANS == 'NO':

        if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="ACTIVE"):
            messages.error(request, f"You already have an active loan. Please contact {settings.SUPPORT_EMAIL}", extra_tags="warning")
            return redirect('dashboard')
        if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="RECOVERY"):
            messages.error(request, f"You already have a loan in recovery. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
            return redirect('dashboard')
        if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="BAD"):
            messages.error(request, f"You already have a bad loan with us. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
            return redirect('dashboard')
        if Loan.objects.filter(owner=owner, category="FUNDED", funded_category="WOFF"):
            messages.error(request, f"You already have a written-off loan with us. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
            return redirect('dashboard')
        if Loan.objects.filter(owner=owner, category="PENDING", status="AWAITING T&C"):
            messages.error(request, f"You already have a pending loan awaiting your action. Cancel that if you wish to apply for a new one.", extra_tags="warning")
            return redirect('myloans')
        if Loan.objects.filter(owner=owner, category="PENDING", status="UNDER REVIEW"):
            messages.error(request, f"You already have a pending loan under review. Cancel that if you wish to apply for a new one.", extra_tags="warning")
            return redirect('myloans')
        if Loan.objects.filter(owner=owner, category="PENDING", status="APPROVED"):
            messages.error(request, f"You already have a pending loan approved. Cancel that if you wish to apply for a new one.", extra_tags="warning")
            return redirect('myloans')                           

    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact support@{domain}", extra_tags="danger")
        return redirect('dashboard')
    
    usr = request.user
    uid = usr.id
    loanref_prefix = loan_setting.loanref_prefix
    user = UserProfile.objects.get(user_id=uid)
    upid = user.id
    
    if user.first_name is None or user.first_name == '':
        messages.error(request, f"You need to update your profile with your First Name and Last Name.", extra_tags="warning")
        return redirect('profile')
    if user.last_name is None or user.last_name == '':
        messages.error(request, f"You need to update your profile with your First Name and Last Name.", extra_tags="warning")
        return redirect('profile')
    
    first_name = user.first_name
    last_name = user.last_name
    rand = random.randint(0,9)
    refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
    repayment_limit = user.repayment_limit
    
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            
            if loan_setting.credit_check == 'YES':
                if not usr.active:
                    return redirect('inactive')
                if usr.defaulted:
                    return redirect('defaulted')
                if usr.suspended:
                    return redirect('suspended')
                if usr.dcc_flagged:
                    return redirect('dcc_flagged')
                if usr.cdb_flagged:
                    return redirect('cdb_flagged')
            
            if user.repayment_limit == 0:
                messages.error(request, "Your repayment limit is not set. Please contact us by creating a support ticket", extra_tags="danger")
                return redirect('loan_application')
            if user.activation == 0:
                messages.error(request, "Your account is not activated. Please contact us by creating a support ticket", extra_tags="danger")
                return redirect('loan_application')

            #loan reference
            loan = Loan.objects.create(ref = refx)
            loanfile = LoanFile.objects.create(loan=loan)
            loanfile.save()
            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.save()

            loan.owner_id = upid
            #loan.type = form.cleaned_data['type']
            loan.amount = form.cleaned_data['amount']

            #amount limit check
            if loan.amount < settings.LOAN_MIN_AMOUNT:
                loan.delete()
                messages.error(request, f'Loan amount must be more than K{ settings.LOAN_MIN_AMOUNT }', extra_tags='danger')
                return redirect('loan_application')
            elif loan.amount > settings.LOAN_MAX_AMOUNT:
                loan.delete()
                messages.error(request, f'Loan amount must be less than K{ settings.LOAN_MAX_AMOUNT }', extra_tags='danger')
                return redirect('loan_application')

            num_fns = form.cleaned_data['number_of_fortnights']

            #COMBINATIONS CHECK
            
            max_fn = combination_check(loan.amount, num_fns)
            if max_fn != 0:
                print(f'MAX FN: {max_fn}')
                
                loan.delete()
                messages.error(request, f"Number of fortnights must be between { settings.MIN_FN } and {max_fn} for an amount of K{loan.amount:,.2f}. Please refer to the repayment table below. Click on 'Show Repayment Table'.", extra_tags='danger')
                return redirect('loan_application')
            
            #COMBINATIONS CHECK _END

            if fn_limits(num_fns) != 1:
                loan.delete()
                messages.error(request, f"Number of fortnights must be between {settings.MIN_FN} and {settings.MAX_FN}.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.number_of_fortnights = num_fns
            start_of_payment = form.cleaned_data['repayment_start_date']
            now = datetime.date.today()
            after_fourteen_days = now + datetime.timedelta(days=14)
            
            if start_of_payment < now:
                loan.delete()
                messages.error(request, "The Start Date can not be in past. The date must be from now and 14 days.", extra_tags='danger')
                return redirect('loan_application')
            
            if start_of_payment > after_fourteen_days:
                loan.delete()
                messages.error(request, "The Start Date can not be after 14 days from now. The date must be between now and 14 days.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.repayment_start_date = start_of_payment
            loan.save()
            
            #calculating_interest
            selected_fns = loan.number_of_fortnights
            amt = float(loan.amount)

            if settings.SYSTEM_TYPE == 'ONE_LOAN_PER_CUSTOMER':
                
                try:
                #check for existing running loan 
                    running_loan = Loan.objects.filter(owner=owner, category="FUNDED", funded_category__in=["ACTIVE", "DEFAULTED"]).last()
                    if running_loan.total_outstanding > settings.LOAN_COMPLETION_BALANCE:
                        return redirect('propose_new_arrangement', running_loan_id=running_loan.id, new_loan_id=loan.id)
                    else:
                        #need to check
                        complete_loan(request, running_loan) 
                except:
                    pass
                    
            interest_type = settings.INTEREST_TYPE
            fortnightly_repayment = repayment(amt, interest_type, selected_fns)
            print('fn_repayment')
            print(fortnightly_repayment)
            total_to_be_paid = fortnightly_repayment * selected_fns
            print('total_to_be_paid')
            print(total_to_be_paid)
            interest_to_be_paid = total_to_be_paid - amt
            print('interest_to_be_paid')
            print(interest_to_be_paid)
            
            rounded_interest = round(interest_to_be_paid,2)
            rounded_repayment_amount = round(fortnightly_repayment,2)     
            rounded_total_to_be_paid = round(total_to_be_paid, 2)
            
            if repayment_limit == 0:
                loan.delete()
                messages.error(request, 'Your repayment Limit is not set yet. Please make sure your payslip is uploaded.', extra_tags="danger")
                return redirect('dashboard')
            
            if fortnightly_repayment > repayment_limit:
                loan.delete()
                messages.error(request, f'The repayment amount of K{rounded_repayment_amount} for this loan is greater than your personal repayment limit of K{repayment_limit}. Please apply again within your repayment limit.', extra_tags='danger')
                return redirect('loan_application') 
            
            loan.interest = rounded_interest
            loan.repayment_frequency = 'FORTNIGHLTY'
            loan.category = 'PENDING'
            loan.status = 'AWAITING T&C'
            loan.location = owner.location
            loan.repayment_amount = rounded_repayment_amount
            loan.total_loan_amount = rounded_total_to_be_paid


            if settings.LOAN_TYPES != 1:
                messages.error(request, 'Administrator needs to enable loan type on application forms first. Please raise a support ticket for this.', extra_tags="danger")
                return redirect('loan_application')
            else:
                loan.type = 'PERSONAL'
            
            # DCC IDENTIFIERS
            loan.uid = user.uid
            loan.luid = settings.LUID
            loan.save()
        
            messages.success(request, "Loan application sent successfully. Please check your email to complete the loan application process...")
            
            templatefileloc1 = 'custom/terms_conditions_gen.html'
            templatefileloc2 = 'custom/stat_dec_gen.html'
            templatefileloc3 = 'custom/irsda_gen.html'
            templatefileloc4 = 'custom/loan_application_gen.html'
            pdfddatacontext = {
                'domain': settings.DOMAIN,
                'loan': loan,
                'interest_rate': loan_setting.interest_rate,
                'user': user,
                'settings': settings
            }

            
            pdf_data1 = generate_pdf(templatefileloc1, pdfddatacontext)
            pdf_attachment1 = MIMEApplication(pdf_data1, _subtype='pdf')
            pdf_attachment1.add_header('content-disposition', 'attachment', filename='Terms_&_Conditions.pdf')
            
            pdf_data2 = generate_pdf(templatefileloc2, pdfddatacontext)
            pdf_attachment2 = MIMEApplication(pdf_data2, _subtype='pdf')
            pdf_attachment2.add_header('content-disposition', 'attachment', filename='Statutory_Declaration.pdf')

            pdf_data3 = generate_pdf(templatefileloc3, pdfddatacontext)
            pdf_attachment3 = MIMEApplication(pdf_data3, _subtype='pdf')
            pdf_attachment3.add_header('content-disposition', 'attachment', filename='IR_Salary_Deduction_Authority.pdf')
            
            pdf_data4 = generate_pdf(templatefileloc4, pdfddatacontext)
            pdf_attachment4 = MIMEApplication(pdf_data4, _subtype='pdf')
            pdf_attachment4.add_header('content-disposition', 'attachment', filename='Loan_Application.pdf')
            
            email_subject=f'Sign Required Documents for Loan - { final_ref }'
            #
            
            # HTML EMAIL
            html_content = render_to_string("custom/email_temp_general.html", {
                'subject': email_subject,
                'greeting': f'Hi {user.first_name}',
                'cta': 'yes',
                'cta_btn1_label': 'UPLOAD SIGNED DOCUMENTS',
                'cta_btn1_link': f'{settings.DOMAIN}/loan/myloan/{loan.ref}/',
                'message': f'Kindly find attached the Pre-filled Loan Application form, Terms and Conditions form, Statutory Declaration form and the Irreovocable Salary Deduction Authority form for your loan application.',
                'message_details': f'Please read through the documents and sign them. Once signed, please scan each signed document and upload them to complete your loan application. Loan decision will only be made once all these documents are signed and uploaded.',
                'user': usr,
                'userprofile': user,
                'loan': loan,
                'domain': settings.DOMAIN,
                'uid': urlsafe_base64_encode(force_bytes(usr.pk)),
                'token': loan_tc_agreement_token.make_token(usr),
            })
            
            text_content = strip_tags(html_content)

            email_list_one = [usr.email, 'dev@webmasta.com.pg']
            email_list_two = settings.APPLICATION_FORM_EMAIL
            email_list  = email_list_one + email_list_two

            
            email = EmailMultiAlternatives(email_subject, text_content, settings.EMAIL_HOST_USER, email_list)
            email.attach_alternative(html_content, "text/html")
            
            email.attach(pdf_attachment1)
            email.attach(pdf_attachment2)
            email.attach(pdf_attachment3)
            email.attach(pdf_attachment4)

            #clear existing loans that were not agreed to
            loans = Loan.objects.filter(owner=owner, tc_agreement='tct')
            print(loans)

            for loanx in loans:
                loanx.delete()
            try:
                email.send()
                loan.tc_agreement = 'tct'
                loan.save()
                messages.success(request, "The Terms & Conditions have been emailed to you, Please read, sign if you agree and upload in your requirements section.", extra_tags='info')
            except:
                messages.error(request, "The Terms & Conditions Agreement email could not be sent, make sure you have internet connection and try apply again.", extra_tags='danger')
                loan.delete()
                return redirect('loan_application')

            return redirect('dashboard')
    else:
        form = form = LoanApplicationForm()
        
    return render(request, 'loan_application_form.html', { 'nav':'loan_application', 'form': form, "repayment_limit": repayment_limit, 'user': user, 'settings': settings })


##############
##  CHECK CREDIT HISTORY
##############

def inactive(request):
    messages.error(request, 'Your account is inactive.', extra_tags='danger')
    return render(request, 'inactive.html' )

def defaulted(request):
    messages.error(request, 'Your account is suspended.', extra_tags='danger')
    return render(request, 'defaulted.html')

def suspended(request):
    messages.error(request, 'Your account is suspended.', extra_tags='danger')
    return render(request, 'suspended.html')

def dcc_flagged(request):
    messages.error(request, 'Your account is flagged in DCC.', extra_tags='danger')
    return render(request, 'dcc_flagged.html')

def cdb_flagged(request):
    messages.error(request, 'Your account is flagged in CDB.', extra_tags='danger')
    return render(request, 'cdb_flagged.html')


######################
#### TERMS & CONDTIONS 
#######################


def agree_to_tc(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and loan_tc_agreement_token.check_token(user,token):
        upid = UserProfile.objects.get(user_id=uid).id
        
        try:
            loan = Loan.objects.filter(owner_id=upid, tc_agreement='tct').get()
        except:
            messages.error(request, 'This loan does not exist, Please apply again.', extra_tags="danger")
            return redirect('loan_application')
        
        return redirect('myloans')
    else:
        return render(request, 'loan_expired.html')    
    

@login_check
def cancel_loan(request, loan_ref):

    loan = Loan.objects.get(ref=loan_ref)
    
    if loan.category == 'APPROVED':
        messages.error(request, 'This loan can not be cancelled because it is already approved.', extra_tags='danger')
        return redirect('myloans')
    elif loan.category == 'RUNNING':
        messages.error(request, 'This loan can not be cancelled because it is a running loan.', extra_tags='danger')
        return redirect('myloans')
    else:
        messages.success(request, f'Loan - { loan.ref} has been cancelled.')
        loan.delete()
    
    return redirect('myloans')


    ### LOAN FUNCTIONS ###


@login_check
def myloans(request):

    user = request.user
    user_profile = UserProfile.objects.get(user_id=user.id)
    
    all_loans = Loan.objects.filter(owner_id=user_profile.id).exclude(funded_category='COMPLETED')
    completed_loans = Loan.objects.filter(owner_id=user_profile.id, funded_category="COMPLETED")
    bad_loans = Loan.objects.filter(owner_id=user_profile.id, funded_category="BAD")
    
    statements = Statement.objects.filter(owner_id=user_profile.id).order_by('-date')[:5]
    
    return render(request, 'my_loans.html', { 'nav':'myloans','all_loans': all_loans , 'completed_loans':completed_loans,'bad_loans':bad_loans, 'statements': statements, 'domain': domain_full, 'user': user_profile })

@login_check
def viewmyloan(request, loan_ref):

    loan = Loan.objects.get(ref=loan_ref)
    print(loan)
    loanfile = LoanFile.objects.get(loan=loan)
    
    uid = loan.owner.id
    user = UserProfile.objects.get(pk=uid)
    usr = User.objects.get(pk=user.user_id)
    usr_email = usr.email
    
    last_name_s = user.last_name[-1]
    
    stat = Statement.objects.filter(loanref=loan)
    
    if request.method=='POST':
        
        if request.POST.get('subject') and request.POST.get('messageofficer'):

            if loan.officer:
                officer_email = loan.officer.email
            else:
                officer_email = f'support@{domain}'
    
            subject = request.POST.get('subject')
            ''' if header_cta == 'yes' '''
            cta_label = ''
            cta_link = ''

            greeting = 'Hi'
            message = f'Message from website regarding: {loan_ref}'
            message_details = request.POST.get('messageofficer')

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
            email = EmailMultiAlternatives(subject,text_content,usr_email,['dev@webmasta.com.pg', officer_email ])
            email.attach_alternative(email_content, "text/html")

            try: 
                email.send()
                messages.success(request, "Message has been forwarded successfully")
                return redirect('pending_loans')
            except:
                messages.error(request, 'Message has not been sent.', extra_tags='danger')
                
            return redirect('view_loan', loan_ref)
        
        else:
            messages.error(request, 'Message has not been sent.', extra_tags='info')
        
    return render(request, 'viewmyloan.html', {'domain': domain_full, 'nav':'myloans','loan':loan, 'user':user, 'usr': usr, 'last_name_s':last_name_s , 'stat': stat, 'loanfile': loanfile })

@login_check
def mystatements(request):

    uid = request.user.id
    user = UserProfile.objects.get(user_id=uid)

    if request.method=="POST":
        
        if request.POST.get('startdate') and request.POST.get('enddate') and request.POST.get('loanref') and request.POST.get('stattype'):
            start_date_entry = request.POST.get('startdate')
            end_date_entry = request.POST.get('enddate')
            ref = request.POST.get('loanref')
            stattype = request.POST.get('stattype')

            start_date = start_date_entry 
            end_date = end_date_entry
            loan_ref = ref

            loan = Loan.objects.get(ref=loan_ref) 

            strip_start_date = start_date.split('-')
            strip_end_date = end_date.split('-')

            date_start_date = datetime.date(int(strip_start_date[0]), int(strip_start_date[1]), int(strip_start_date[2]))
            date_end_date = datetime.date(int(strip_end_date[0]), int(strip_end_date[1]), int(strip_end_date[2]))
            
            if date_start_date > date_end_date:
                messages.error(request, 'End date must be after Start date!')
                return redirect('mystatements')

            statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id, type = stattype, loanref = loan, date__gte=start_date, date__lte=end_date).all()
            loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
            return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})
        
        elif request.POST.get('startdate') and request.POST.get('enddate') and request.POST.get('loanref'):
            start_date_entry = request.POST.get('startdate')
            end_date_entry = request.POST.get('enddate')
            ref = request.POST.get('loanref')

            start_date = start_date_entry 
            end_date = end_date_entry
            loan_ref = ref

            loan = Loan.objects.get(ref=loan_ref)

            strip_start_date = start_date.split('-')
            strip_end_date = end_date.split('-')

            date_start_date = datetime.date(int(strip_start_date[0]), int(strip_start_date[1]), int(strip_start_date[2]))
            date_end_date = datetime.date(int(strip_end_date[0]), int(strip_end_date[1]), int(strip_end_date[2]))
            
            if date_start_date > date_end_date:
                messages.error(request, 'End date must be after Start date!')
                return redirect('mystatements')

            statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id, loanref = loan, date__gte=start_date, date__lte=end_date).all()
            loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
            return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})
        
        elif request.POST.get('startdate') and request.POST.get('enddate') and request.POST.get('stattype'):
            start_date_entry = request.POST.get('startdate')
            end_date_entry = request.POST.get('enddate')
            stattype = request.POST.get('stattype')

            start_date = start_date_entry 
            end_date = end_date_entry

            strip_start_date = start_date.split('-')
            strip_end_date = end_date.split('-')

            date_start_date = datetime.date(int(strip_start_date[0]), int(strip_start_date[1]), int(strip_start_date[2]))
            date_end_date = datetime.date(int(strip_end_date[0]), int(strip_end_date[1]), int(strip_end_date[2]))
            
            if date_start_date > date_end_date:
                messages.error(request, 'End date must be after Start date!')
                return redirect('mystatements')

            statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id, type = stattype, date__gte=start_date, date__lte=end_date).all()
            loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
            return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})
        
        elif request.POST.get('startdate') and request.POST.get('enddate'):
            start_date_entry = request.POST.get('startdate')
            end_date_entry = request.POST.get('enddate')
            
            start_date = start_date_entry
            end_date = end_date_entry

            strip_start_date = start_date.split('-')
            strip_end_date = end_date.split('-')

            date_start_date = datetime.date(int(strip_start_date[0]), int(strip_start_date[1]), int(strip_start_date[2]))
            date_end_date = datetime.date(int(strip_end_date[0]), int(strip_end_date[1]), int(strip_end_date[2]))
            
            if date_start_date > date_end_date:
                messages.error(request, 'End date must be after Start date!')
                return redirect('mystatements')

            statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id, date__gte=start_date, date__lte=end_date).all()
            loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
            
            return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})
        
        elif request.POST.get('loanref') and request.POST.get('stattype'): 
            ref = request.POST.get('loanref')
            stattype = request.POST.get('stattype')
                
            if stattype == 'OTHER':
                statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id,loanref = loan).exclude(type = 'PAYMENT').exclude(type='DEFAULT') 
            else:
                statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id, loanref = loan, type = stattype).all()
            loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
            return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})

        elif request.POST.get('loanref'): 
            ref = request.POST.get('loanref')
            loan = Loan.objects.get(ref=ref)
            statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id, loanref = loan).all()
            loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
            return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})

        elif request.POST.get('stattype'): 
            stattype = request.POST.get('stattype')
            
            if stattype == 'OTHER':
                statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id).exclude(type = 'PAYMENT').exclude(type='DEFAULT') 
            else:
                statements = Statement.objects.prefetch_related('loanref','owner').filter(owner_id=user.id, type = stattype).all()
                
            loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
            return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})

        else:
            messages.error(request, 'You did not select any filter', extra_tags='warning')
            return redirect('mystatements')

    statements = Statement.objects.prefetch_related('owner','loanref').filter(owner_id=user.id)
    loans = Loan.objects.filter(owner_id=user.id, category='APPROVED')
    return render(request, 'mystatements.html', { 'nav':'mystatements','user': user, 'statements': statements,'loans': loans})

@login_check
def upload_payment(request, loan_ref):
    
    loan = Loan.objects.get(ref=loan_ref)
    
    uid = request.user.id
    user = UserProfile.objects.get(user_id=uid)
    
    if request.method == 'POST':
        uploadform = PaymentUploadForm(request.POST)
        
        if uploadform.is_valid():
    
            if 'payment_proof' in request.FILES:
                date_today = datetime.date.today()
                date_ref = date_today.strftime("%d%m%y")
                print(date_ref)
                payment_upload_ref = f'PU{date_ref}{loan_ref}'
                paymentupload = PaymentUploads.objects.create(ref=payment_upload_ref, owner=user, loan=loan)
                paymentupload.save()

                updated_upload_ref = f'{payment_upload_ref}i{paymentupload.id}'

                payment_proof = request.FILES['payment_proof']
                fspayment_proof = FileSystemStorage()
                newpayment_proof_name = f'{user.first_name}_{user.last_name}_PAYMENT_UPLOAD_{updated_upload_ref}_{payment_proof.name}'
                payment_proof_filename = fspayment_proof.save(newpayment_proof_name, payment_proof)
                payment_url = fspayment_proof.url(payment_proof_filename)
                
                type = uploadform.cleaned_data.get('type')

                paymentupload.file_name=payment_proof_filename
                paymentupload.payment_proof_url=payment_url 
                paymentupload.status='UPLOADED' 
                paymentupload.type=type
                paymentupload.ref = updated_upload_ref
                paymentupload.save()

                messages.success(request, 'Payment Uploaded Successfully...')
                
                #### SEND EMAIL TO ADMIN
                
                subject = f'PAYMENT UPLOADED for {loan_ref}'
                ''' if header_cta == 'yes' '''

                greeting = 'Hello'
                message = f'I just uploaded a payment for my loan - {loan_ref}'
                message_details = 'Please check and update my loan balance accordingly.'

                ''' if cta == 'yes' '''
                cta_btn1_label = 'View Upload'
                cta_btn1_link = f'{settings.DOMAIN}{payment_url}'
                cta_btn2_label = 'Register Payment'
                cta_btn2_link = f'{settings.DOMAIN}/loan/payment/{loan_ref}/'

                email_content = render_to_string('custom/email_temp_general.html', {
                
                    'cta': 'yes',
                    'cta_btn2': 'yes',
                    'subject': subject,
                    'greeting': greeting,
                    'message': message,
                    'message_details': message_details,
                    'cta_btn1_link': cta_btn1_link,
                    'cta_btn1_label': cta_btn1_label,
                    'cta_btn2_link': cta_btn2_link,
                    'cta_btn2_label': cta_btn2_label,
                    'user': user,
                    'domain': domain,  
                })
                text_content = strip_tags(email_content)
                email = EmailMultiAlternatives(subject, text_content, user.email, admin_emails)
                email.attach_alternative(email_content, "text/html")

                try: 
                    email.send()
                    messages.success(request, "Loan Administrator has been notified.")
                except:
                    messages.error(request, 'Admin notification send failed, make sure you are connected to the internet.', extra_tags='danger')
                    
                return redirect('myloans')
   
    else:
        uploadform = PaymentUploadForm()
    return render(request, 'upload_payments.html', { 'nav':'myloans','form': uploadform, 'loan':loan})   

@login_check
def staff_enter_payment(request):
    
    loans = Loan.objects.filter(category='FUNDED').exclude(funded_category='COMPLETED').exclude(funded_category='WOFF')
    return render(request, 'staff_enter_payment.html', { 'nav': 'userstatements', 'loans':loans, 'domain': domain_full })
                  
@check_staff
def payment(request, loan_ref):

    loan = Loan.objects.get(ref=loan_ref)
    loid = loan.owner.id
    
    user = UserProfile.objects.get(pk=loid)
    staffprofile = UserProfile.objects.get(user=request.user.id)
    officer = StaffProfile.objects.get(user=staffprofile)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            
            ref = loan
            date = form.cleaned_data['date']
            amount = form.cleaned_data['amount']
            mode = form.cleaned_data['mode']
            statement = form.cleaned_data['statement']
            
            payment = Payment.objects.create(owner=user, loanref=ref, date=date, amount=amount, mode=mode, statement=statement, officer=officer)
            stat = Statement.objects.create(owner=user, loanref=ref, date=date, debit=amount, statement=statement, uid=user.uid, luid=settings.LUID)
            
            num_payments = loan.number_of_repayments
            
            p_count = num_payments + 1
            payment.ref = f'{loan_ref}P{p_count}'
            payment.p_count = p_count
            payment.save()
            
            stat.s_count += 1
            stat.ref = f'{loan_ref}SP{stat.s_count}' 
            stat.save()
            
            ramount = loan.repayment_amount
            
            tol_pos = settings.TOTAL_ALLOWABLE_TOEAS
            tol_neg = -settings.TOTAL_ALLOWABLE_TOEAS
            
            tol_neg_amount = ramount + tol_neg
            tol_pos_amount = ramount + tol_pos

            loan.save()
            stat.save()

            if amount < tol_neg_amount:
                payment.type = 'PARTIAL PAYMENT'
                payment.save()
                process_repayment(request, loan, stat, amount)
            elif amount>tol_pos_amount:
                payment.type = 'ADVANCE PAYMENT'
                payment.save()
                process_advance_payment(request, loan, stat, amount)
            else:
                payment.type = 'NORMAL REPAYMENT'
                payment.save()
                print(f'PAYMENT TYPE: {payment.type}')
                process_repayment(request, loan, stat, amount)

        else:
            messages.error(request, 'Payment not entered. Please check the form and try again.', extra_tags='danger')
        return redirect('staff_enter_payment')
            
    else:
        form = PaymentForm()        
    
    return render(request, 'payment.html', { 'loan_ref': loan_ref, 'form': form })
    

##### NEW FUNCTIONS

def repayment_week(request):
    
    import datetime

    date = datetime.date.today()
    weekday = date.weekday()
    print(weekday)

    if weekday <= 2:

        if weekday == 0:
            day_1 = date
            day_2 = date + datetime.timedelta(days=1)
            day_3 = date + datetime.timedelta(days=2)

        if weekday == 1:
            day_1 = date - datetime.timedelta(days=1)
            day_2 = date 
            day_3 = date + datetime.timedelta(days=1)

        if weekday == 2:
            day_1 = date - datetime.timedelta(days=2)
            day_2 = date - datetime.timedelta(days=1)
            day_3 = date 
        
        print(day_1, day_2 ,day_3)

        loans = Loan.objects.filter(next_payment_date__gte=day_1, next_payment_date__lte=day_3)

    loans = Loan.objects.filter(next_payment_date=date)
    
        

    return render(request, 'repayment_week.html', {'loans':loans})