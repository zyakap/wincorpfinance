
import datetime
import decimal
import random
import math
from decimal import Decimal
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site

from django.db.models import Sum
from message.models import Message, MessageLog

from loan.models import Loan, LoanFile, Statement, Payment, PaymentUploads
from loan.forms import PaymentForm
from admin1.forms import AdminSettingsForm

from accounts.models import User, UserProfile, StaffProfile, SMEProfile 
from staff.forms import ( MemberInfoForm, PersonalInfoForm, ContactInfoForm, AddressInfoForm, UserUploadForm, 
    WorkUploadForm, BankAccountInfoForm, EmployerInfoUpdateForm, JobInfoUpdateForm, UploadRequirementsByStaffForm,
    LoanStatementUploadForm, SMEProfileForm, SMEUploadsForm, SMEBankInfoForm, RequiredUploadForm, CreateSMEProfileForm, CreateLoanForm
)

from loan.functions import request_approval

#TOKENIZER
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode
#from .tokens import loan_tc_agreement_token
from django.core.files.storage import FileSystemStorage

from .functions import id_generator, complete_loan, fund_additional_loan
from .forms import AddAdditionalLoanForm, AddNewLoanForm

from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.html import strip_tags

from django.db.models import Q

#admin sender email
from admin1.models import AdminSettings, Location
sender = settings.DEFAULT_SENDER_EMAIL

#FILES UPLOAD
from django.core.files.storage import FileSystemStorage
from accounts.functions import login_check, admin_check, check_staff, fileuploader, loanfileuploader, testloanfileuploader

domain = settings.DOMAIN
domain_dns = settings.DOMAIN_DNS

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import subprocess

import pandas as pd

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

from custom.functions import repayment, combination_check, upload_existing_loans, upload_existing_statement

from .functions import direct_loan_update_function, create_new_loan_from_upload, upload_payments_function
############### 
# START OF CODE
###############




#########################
####   PAGES
#########################

def home(request):
    return render(request, 'website/home.html', {'nav': 'home'})

def about(request):
    return render(request, 'website/about.html', {'nav': 'about'})

def contact(request):
    return render(request, 'website/contact.html', {'nav': 'contact'})

def dcc(request):
    return render(request, 'website/dcc.html', {'nav': 'dcc'})

def demo(request):
    return render(request, 'website/demo.html', {'nav': 'demo'})

def how_to_videos(request):
    return render(request, 'website/how_to_videos.html', {'nav': 'how_to_videos'})

def clients(request):
    return render(request, 'website/clients.html', {'nav': 'clients'})

@check_staff
def custom_functions(request):
    return render(request, 'functions/custom_functions.html', {'nav': 'custom_functions'})

@check_staff
def direct_loan_update(request):
    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('staff_dashboard')

    #try: 
    if request.method == 'POST' and request.FILES['uploadedloans']:      
        uploadedloans = request.FILES['uploadedloans']
        fs = FileSystemStorage()
        filename = fs.save(uploadedloans.name, uploadedloans)
        uploaded_file_url = fs.url(filename)
        full_path = settings.DOMAIN + uploaded_file_url        
        loanexceldata = pd.read_excel(full_path)
        direct_loan_update_function(request, loanexceldata)
        messages.success(request, f"DONE", extra_tags="info") 
    
    
    #except:
    #    messages.error(request, f"You did not upload any file...", extra_tags="danger") 
    #    return render(request, 'import_existing_loans.html',{'nav': 'add_existing_loan'})  

    return render(request, 'functions/import_existing_loans.html',{'nav': 'add_existing_loan'})

@check_staff
def upload_new_loan(request):
    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('staff_dashboard')

    #try: 
    if request.method == 'POST' and request.FILES['uploadedloans']:      
        uploadedloans = request.FILES['uploadedloans']
        fs = FileSystemStorage()
        filename = fs.save(uploadedloans.name, uploadedloans)
        uploaded_file_url = fs.url(filename)
        full_path = settings.DOMAIN + uploaded_file_url        
        loanexceldata = pd.read_excel(full_path)
        create_new_loan_from_upload(request, loanexceldata)
        messages.success(request, f"DONE", extra_tags="info")
    
    #except:
    #    messages.error(request, f"You did not upload any file...", extra_tags="danger") 
    #    return render(request, 'import_existing_loans.html',{'nav': 'add_existing_loan'})  

    return render(request, 'functions/upload_new_loan.html',{'nav': 'add_existing_loan'})

@check_staff
def upload_payments(request):
    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('staff_dashboard')

    #try: 
    if request.method == 'POST' and request.FILES['uploadedloans']:      
        uploadedloans = request.FILES['uploadedloans']
        fs = FileSystemStorage()
        filename = fs.save(uploadedloans.name, uploadedloans)
        uploaded_file_url = fs.url(filename)
        full_path = settings.DOMAIN + uploaded_file_url        
        loanexceldata = pd.read_excel(full_path)
        upload_payments_function(request, loanexceldata)
        messages.success(request, f"DONE", extra_tags="info")
    
    #except:
    #    messages.error(request, f"You did not upload any file...", extra_tags="danger") 
    #    return render(request, 'import_existing_loans.html',{'nav': 'add_existing_loan'})  

    return render(request, 'functions/upload_payments.html',{'nav': 'add_existing_loan'})


#### from LoanMasta further development

### trupngfinance 

@login_check
def propose_new_arrangement(request, running_loan_id, new_loan_id):
    running_loan = Loan.objects.get(id=running_loan_id)
    loan = Loan.objects.get(id=new_loan_id)
    selected_fns = loan.number_of_fortnights
    repayment_limit = running_loan.owner.repayment_limit

    existing_balance = running_loan.total_outstanding
    interest_type = settings.INTEREST_TYPE

    existing_repayment = running_loan.repayment_amount

    remaining_fns = math.ceil(existing_balance / existing_repayment)
    
    fortnightly_repayment = repayment(loan.amount, interest_type, loan.number_of_fortnights)
    new_repayment = existing_repayment + Decimal(fortnightly_repayment)
    


    if Decimal(new_repayment) > repayment_limit:
        messages.error(request, f'The new repayment amount of {new_repayment} is greater than your repayment limit of {repayment_limit}', extra_tags='danger')
        if selected_fns < 10:
            messages.error(request, f'You can try increase the number of fortnights to something more than {int(selected_fns)}.', extra_tags='info')
        else:
            messages.error(request, f'You do not have the capacity to get an additional loan. If you think this was an error, please contact us.', extra_tags='warning')
            
        return redirect('loan_application')

    total_to_be_paid = fortnightly_repayment * selected_fns
    interest_to_be_paid = Decimal(total_to_be_paid) - loan.amount

    combined_total = existing_balance + Decimal(total_to_be_paid)
    new_combined_repayment = Decimal(new_repayment)

    balance_of_fns = remaining_fns
    remainder_of_fns = loan.number_of_fortnights - balance_of_fns

    new_repayment = round(new_repayment,2)
    combined_total = round(combined_total,2)
    new_combined_repayment = round(new_combined_repayment,2)
    fortnightly_repayment = round(fortnightly_repayment,2)

    if request.method == 'POST':
        decision = request.POST.get('decision')
        
        if decision == 'ACCEPT':
            owner = loan.owner
            rounded_interest = round(interest_to_be_paid,2)
            rounded_repayment_amount = round(new_combined_repayment,0)
            rounded_total_to_be_paid = round(total_to_be_paid,0)
            
            loan.interest = rounded_interest
            loan.repayment_frequency = 'FORTNIGHLTY'
            loan.category = 'PENDING'
            loan.status = 'AWAITING T&C'
            loan.location = owner.location
            loan.repayment_amount = rounded_repayment_amount
            loan.total_loan_amount = rounded_total_to_be_paid

            loan.principal_loan_receivable = loan.amount
            loan.ordinary_interest_receivable = loan.interest
            loan.default_interest_receivable = 0
            loan.total_outstanding = Decimal(round(combined_total,2))
            loan.save()

            if settings.LOAN_TYPES != 1:
                messages.error(request, 'Administrator needs to enable loan type on application forms first. Please raise a support ticket for this.', extra_tags="danger")
                return redirect('loan_application')
            else:
                loan.type = 'PERSONAL'
            
            # DCC IDENTIFIERS
            loan.uid = owner.uid
            loan.luid = settings.LUID
            loan.save()

            user = owner
        
            messages.success(request, "Loan application sent successfully. Please check your email to complete the loan application process...")
            
            templatefileloc1 = 'custom/terms_conditions_gen.html'
            templatefileloc2 = 'custom/stat_dec_gen.html'
            templatefileloc3 = 'custom/irsda_gen.html'
            templatefileloc4 = 'custom/loan_application_gen.html'
            pdfddatacontext = {
                'domain': settings.DOMAIN,
                'loan': loan,
                #'interest_rate': loan_setting.interest_rate,
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
            
            email_subject=f'Sign Required Documents for Loan - { loan.ref }'
            
            # HTML EMAIL
            html_content = render_to_string("custom/email_temp_general.html", {
                'subject': email_subject,
                'greeting': f'Hi {user.first_name}',
                'cta': 'yes',
                'cta_btn1_label': 'UPLOAD SIGNED DOCUMENTS',
                'cta_btn1_link': f'{settings.DOMAIN}/loan/myloan/{loan.ref}/',
                'message': f'Kindly find attached the Pre-filled Loan Application form, Terms and Conditions form, Statutory Declaration form and the Irreovocable Salary Deduction Authority form for your loan application.',
                'message_details': f'Please read through the documents and sign them. Once signed, please scan each signed document and upload them to complete your loan application. Loan decision will only be made once all these documents are signed and uploaded.',
                'user': request.user,
                'userprofile': user,
                'loan': loan,
                'domain': settings.DOMAIN,
                
            })
            
            text_content = strip_tags(html_content)
            cc_list = settings.CC_EMAILS
            bcc_list = settings.BCC_EMAILS

            email_list = [user.email, user.work_email]
            email = EmailMultiAlternatives(email_subject, text_content, settings.EMAIL_HOST_USER, email_list,cc=cc_list,bcc=bcc_list)
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
            messages.error(request, 'You have cancelled your loan application.', extra_tags='info')
            loan.delete()
            return redirect('loan_application')

    context = {
        'nav': 'propose_new_arrangement',
        'running_loan': running_loan,
        'loan': loan,
        'existing_balance': existing_balance,
        'existing_repayment': running_loan.repayment_amount,
        'combined_total': combined_total,
        'new_combined_repayment': new_combined_repayment,
        'balance_of_fns':balance_of_fns,
        'new_repayment': fortnightly_repayment,
        'remainder_of_fns': remainder_of_fns
    }
    
    return render(request, 'custom_functions/propose_new_arrangement.html', context)

@check_staff
def propose_new_arrangement_staff(request, running_loan_id, new_loan_id):
    running_loan = Loan.objects.get(id=running_loan_id)
    loan = Loan.objects.get(id=new_loan_id)
    selected_fns = loan.number_of_fortnights
    repayment_limit = running_loan.owner.repayment_limit

    existing_balance = running_loan.total_outstanding
    interest_type = settings.INTEREST_TYPE

    existing_repayment = running_loan.repayment_amount

    remaining_fns = math.ceil(existing_balance / existing_repayment)
 
    fortnightly_repayment = repayment(loan.amount, interest_type, loan.number_of_fortnights)
    new_repayment = existing_repayment + Decimal(fortnightly_repayment)

    if Decimal(new_repayment) > repayment_limit:
        messages.error(request, f'The new repayment amount of {new_repayment} is greater than your repayment limit of {repayment_limit}', extra_tags='danger')
        if selected_fns < 10:
            messages.error(request, f'You can try increase the number of fortnights to something more than {int(selected_fns)}.', extra_tags='info')
        else:
            messages.error(request, f'You do not have the capacity to get an additional loan. If you think this was an error, please contact us.', extra_tags='warning')
            
        return redirect('loan_application')

    total_to_be_paid = fortnightly_repayment * selected_fns
    interest_to_be_paid = Decimal(total_to_be_paid) - loan.amount

    combined_total = existing_balance + Decimal(total_to_be_paid)
    new_combined_repayment = Decimal(new_repayment)

    balance_of_fns = remaining_fns
    remainder_of_fns = loan.number_of_fortnights - balance_of_fns

    if request.method == 'POST':
        decision = request.POST.get('decision')
        
        if decision == 'ACCEPT':
            owner = loan.owner
            rounded_interest = round(interest_to_be_paid,2)
            rounded_repayment_amount = round(new_combined_repayment,2)
            rounded_total_to_be_paid = round(combined_total,2)
            
            loan.interest = rounded_interest
            loan.repayment_frequency = 'FORTNIGHLTY'
            loan.category = 'PENDING'
            loan.status = 'AWAITING T&C'
            loan.location = owner.location
            loan.repayment_amount = rounded_repayment_amount
            loan.total_loan_amount = rounded_total_to_be_paid

            loan.principal_loan_receivable = loan.amount
            loan.ordinary_interest_receivable = loan.interest
            loan.default_interest_receivable = 0
            loan.total_outstanding = loan.total_loan_amount
            loan.save()

            if settings.LOAN_TYPES != 1:
                messages.error(request, 'Administrator needs to enable loan type on application forms first. Please raise a support ticket for this.', extra_tags="danger")
                return redirect('loan_application')
            else:
                loan.type = 'PERSONAL'
            
            # DCC IDENTIFIERS
            loan.uid = owner.uid
            loan.luid = settings.LUID
            loan.save()
            
            return redirect('dashboard')
        else:
            messages.error(request, 'loan Application cancelled.', extra_tags='info')
            return redirect('create_loan')

    context = {
        'nav': 'propose_new_arrangement',
        'running_loan': running_loan,
        'loan': loan,
        'existing_balance': existing_balance,
        'existing_repayment': running_loan.repayment_amount,
        'combined_total': combined_total,
        'new_combined_repayment': new_combined_repayment,
        'balance_of_fns':balance_of_fns,
        'new_repayment': fortnightly_repayment,
        'remainder_of_fns': remainder_of_fns
    }
    
    return render(request, 'custom_functions/propose_new_arrangement_staff.html', context)


@admin_check
def propose_new_arrangement_test(request,):
    #running_loan = RunningLoan.objects.get(id=running_loan_id)
    #loan = Loan.objects.get(id=loan_id)

    #existing_balance = running_loan.total_outstanding
    '''
    fortnightly_repayment = repayment(amt, interest_type, selected_fns)
    total_to_be_paid = fortnightly_repayment * selected_fns
    interest_to_be_paid = total_to_be_paid - amt

    combined_total = existing_balance + total_to_be_paid
    new_combined_repayment = combined_total / selected_fns

    if request.method == 'POST':
        decision = request.POST.get('decision')
        
        if decision == 'ACCEPTED':
            rounded_interest = round(interest_to_be_paid,2)
            loan.interest_to_be_paid = rounded_interest
            loan.save()
            rounded_repayment_amount = round(fortnightly_repayment,2)     
            rounded_total_to_be_paid = round(total_to_be_paid, 2)
    '''
    context = {
        'nav': 'propose_new_arrangement_test',
        ##'running_loan': running_loan,
       # 'loan': loan,
       ## 'existing_balance': existing_balance,
       # 'existing_repayment': running_loan.repayment_amount,
       # 'new_combined_repayment': new_combined_repayment,
    }
    
    return render(request, 'custom_functions/propose_new_arrangement_test.html', context)


@check_staff
def add_additional_loan(request):
    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('dashboard')
    if request.method == 'POST':
        form = AddAdditionalLoanForm(request.POST)
        if form.is_valid():
            owner = form.cleaned_data['owner']
            location = form.cleaned_data['location']
            amount = form.cleaned_data['amount']
            num_fns = form.cleaned_data['number_of_fortnights']
            repayment_start_date = form.cleaned_data['repayment_start_date']
            funding_date = form.cleaned_data['funding_date']
            
            user = owner
            loanref_prefix = loan_setting.loanref_prefix
            upid = user.id
            first_name = user.first_name
            last_name = user.last_name
            rand = random.randint(0,9)
            refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
            repayment_limit = user.repayment_limit

            usr = User.objects.get(pk=user.user_id)
            staff_profile = UserProfile.objects.get(user=request.user)
            staff = StaffProfile.objects.get(user=staff_profile)

            loan = Loan.objects.create(ref = refx, officer=staff, owner=owner, location=location, amount=amount)
            loanfile = LoanFile.objects.create(loan=loan)
            loanfile.save()
            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.uid = user.uid
            loan.luid = settings.LUID
            loan.save()
            
            loan.number_of_fortnights = num_fns
            start_of_payment = repayment_start_date
        
            now = funding_date
            after_fourteen_days = now + datetime.timedelta(days=14)
            
            if start_of_payment < now:
                loan.delete()
                messages.error(request, "The Start Date can not be in past. The date must be from now and 14 days.", extra_tags='danger')
                return redirect('userloans_unfinished')
            
            if start_of_payment > after_fourteen_days:
                loan.delete()
                messages.error(request, "The Start Date can not be after 14 days from now. The date must be between now and 14 days.", extra_tags='danger')
                return redirect('userloans_unfinished')
            
            loan.repayment_start_date = start_of_payment
            loan.funding_date = funding_date
            loan.save()
            #calculating_interest
            selected_fns = loan.number_of_fortnights
            amt = float(loan.amount)

            try:
            #check for existing running loan 
                running_loan = Loan.objects.filter(owner=loan.owner, category="FUNDED", funded_category__in=["ACTIVE", "DEFAULTED"]).last()
            except:
                messages.error(request, "Customer has no running loan, create in normal way.", extra_tags='info')
                return redirect('create_loan')
            
            if running_loan.total_outstanding < settings.LOAN_COMPLETION_BALANCE:
                complete_loan(request, running_loan)
            
            selected_fns = loan.number_of_fortnights
            existing_balance = running_loan.total_outstanding
            interest_type = settings.INTEREST_TYPE
            
            fortnightly_repayment = repayment(loan.amount, interest_type, loan.number_of_fortnights)
            total_to_be_paid = fortnightly_repayment * selected_fns
            interest_to_be_paid = Decimal(total_to_be_paid) - loan.amount

            combined_total = existing_balance + Decimal(total_to_be_paid)
            new_combined_repayment = Decimal(combined_total) / selected_fns

            owner = loan.owner
            rounded_interest = round(interest_to_be_paid,2)
            rounded_repayment_amount = round(new_combined_repayment,2)
            rounded_total_to_be_paid = round(combined_total,2)
            
            loan.interest = rounded_interest
            loan.repayment_frequency = 'FORTNIGHLTY'
            loan.location = owner.location
            loan.repayment_amount = rounded_repayment_amount
            loan.total_loan_amount = rounded_total_to_be_paid

            loan.principal_loan_receivable = loan.amount
            loan.ordinary_interest_receivable = loan.interest
            loan.default_interest_receivable = 0
            loan.total_outstanding = loan.total_loan_amount
            loan.save()

            if settings.LOAN_TYPES != 1:
                messages.error(request, 'Administrator needs to enable loan type on application forms first. Please raise a support ticket for this.', extra_tags="danger")
                return redirect('loan_application')
            else:
                loan.type = 'PERSONAL'
            
            # DCC IDENTIFIERS
            loan.uid = owner.uid
            loan.luid = settings.LUID
            loan.save()

            existing_statements = Statement.objects.filter(loanref=running_loan)
            for statement in existing_statements:
                statement.pk = None  # This will create a new instance instead of updating the existing one
                statement.loanref = loan
                statement.save()

            today = funding_date
            Statement.objects.create(owner=running_loan.owner, ref=f'{running_loan.ref}LE', loanref=running_loan, type="REFINANCE", 
            statement=f"Loan Ended - Balance transfered to new loan {loan.ref}", debit=running_loan.total_outstanding, 
            balance=0.00, date=today, uid=running_loan.owner.uid, luid=settings.LUID)

            running_loan.status = 'COMPLETED'
            running_loan.funded_category = 'COMPLETED'
            existing_balance = running_loan.total_outstanding
            running_loan.total_outstanding = 0.00
            running_loan.save()

            loan.status = 'ACTIVE'
            loan.save()

            #new code:
            new_balance = loan.total_outstanding

            #recalculate repayment dates
            fourteendays = datetime.timedelta(days=14)
            
            repayment_start_date = loan.repayment_start_date
            next_payment_date = repayment_start_date + fourteendays
            next_next = next_payment_date + fourteendays
            
            if today < repayment_start_date:
                first_repayment_date = repayment_start_date
            elif repayment_start_date < today < next_payment_date:
                first_repayment_date =  next_payment_date
            elif next_payment_date < today < next_next:
                first_repayment_date = next_next
            else:
                first_repayment_date = next_next + fourteendays
            
            first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

            repayment_dates_list = [first_repayment_date_str]
            last_date = first_repayment_date
            fns = loan.number_of_fortnights
            while fns > 1:
                new_date = last_date + fourteendays
                new_date_str = new_date.strftime('%Y-%m-%d')
                repayment_dates_list.append(new_date_str)
                last_date = new_date
                fns -= 1
            
            # Serialize the list to a JSON string
            loan.set_repayment_dates(repayment_dates_list)
            loan.category = 'FUNDED'
            loan.funded_category = 'ACTIVE'
            loan.status = 'RUNNING'
            loan.funding_date = today
            loan.next_payment_date = first_repayment_date
            loan.save()
            
            user = UserProfile.objects.get(id=loan.owner.id)
            user.number_of_loans += 1
            user.save()

            if settings.PROCESSING_FEE_CHARGABLE == 'YES':
                loan.processing_fee = settings.PROCESSING_FEE
                loan.save()
                Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="FUNDING", statement="Loan Funded", credit=loan.amount-loan.processing_fee, balance=new_balance, date=today, uid=user.uid, luid=settings.LUID)
                Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="OTHER", statement="Loan Processing Fee", credit=loan.processing_fee, balance=new_balance, date=today, uid=user.uid, luid=settings.LUID)
            else:
                Statement.objects.create(owner=user, ref=f'{loan.ref}ALF', loanref=loan, type="FUNDNG", statement=f"Additional Loan Funded - Balance updated with additional interest of {loan.interest}", credit=loan.amount, balance=new_balance, date=today, uid=user.uid, luid=settings.LUID)

            #### Update loan balances and everything
            loan.classification = 'ADDITIONAL'
            loan.principal_loan_paid += Decimal(running_loan.principal_loan_paid)
            loan.interest_paid += Decimal(running_loan.interest_paid)
            loan.default_interest_paid += Decimal(running_loan.default_interest_paid)
            loan.total_paid += Decimal(running_loan.total_paid)

            loan.fortnights_paid += running_loan.fortnights_paid
            loan.number_of_repayments += running_loan.number_of_repayments
            loan.last_repayment_amount = Decimal(running_loan.last_repayment_amount)
            loan.last_repayment_date = running_loan.last_repayment_date
            loan.number_of_advance_payments += running_loan.number_of_advance_payments
            loan.last_advance_payment_date = running_loan.last_advance_payment_date
            loan.last_advance_payment_amount = Decimal(running_loan.last_advance_payment_amount)
            
            loan.total_advance_payment += float(running_loan.total_advance_payment)
            loan.advance_payment_surplus += float(running_loan.advance_payment_surplus)

            loan.number_of_defaults += running_loan.number_of_defaults
            loan.last_default_date = running_loan.last_default_date
            loan.last_default_amount = Decimal(running_loan.last_default_amount)
            loan.days_in_default += running_loan.days_in_default
            loan.total_arrears += float(running_loan.total_arrears)

            loan.principal_loan_receivable += Decimal(running_loan.principal_loan_receivable)
            loan.ordinary_interest_receivable += Decimal(running_loan.ordinary_interest_receivable)
            loan.default_interest_receivable += Decimal(running_loan.default_interest_receivable)

            loan.opt1 = running_loan.opt1
            loan.opt2 = running_loan.opt2
            loan.opt3 = running_loan.opt3   
            loan.opt4 = running_loan.opt4
            loan.opt5 = running_loan.opt5
            loan.dcc = running_loan.dcc
            loan.notes = running_loan.notes
            loan.save()

            messages.success(request, "Loan ADDED...")
            
            return redirect('custom_functions')
        
            
    else:
        form = AddAdditionalLoanForm()
        
    return render(request, 'functions/add_additional_loan.html', { 'nav':'loans', 'form': form })



@check_staff
def add_new_loan(request):
    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('dashboard')
    if request.method == 'POST':
        form = AddNewLoanForm(request.POST)
        if form.is_valid():
            owner = form.cleaned_data['owner']
            location = form.cleaned_data['location']
            amount = form.cleaned_data['amount']
            num_fns = form.cleaned_data['number_of_fortnights']
            repayment_start_date = form.cleaned_data['repayment_start_date']
            funding_date = form.cleaned_data['funding_date']
            
            user = owner
            loanref_prefix = loan_setting.loanref_prefix
            upid = user.id
            first_name = user.first_name
            last_name = user.last_name
            rand = random.randint(0,9)
            refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
            repayment_limit = user.repayment_limit

            usr = User.objects.get(pk=user.user_id)
            staff_profile = UserProfile.objects.get(user=request.user)
            staff = StaffProfile.objects.get(user=staff_profile)

            loan = Loan.objects.create(ref = refx, officer=staff, owner=owner, location=location, amount=amount)
            loanfile = LoanFile.objects.create(loan=loan)
            loanfile.save()
            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.uid = user.uid
            loan.luid = settings.LUID
            loan.save()
            
            loan.number_of_fortnights = num_fns
            start_of_payment = repayment_start_date
        
            now = funding_date
            after_fourteen_days = now + datetime.timedelta(days=14)
            
            loan.repayment_start_date = start_of_payment
            loan.funding_date = funding_date
            loan.save()
            #calculating_interest
            selected_fns = loan.number_of_fortnights
            amt = float(loan.amount)
            
            selected_fns = loan.number_of_fortnights
            
            interest_type = settings.INTEREST_TYPE
            
            fortnightly_repayment = repayment(loan.amount, interest_type, loan.number_of_fortnights)
            total_to_be_paid = fortnightly_repayment * selected_fns
            interest_to_be_paid = Decimal(total_to_be_paid) - loan.amount

            combined_total = Decimal(total_to_be_paid)
            new_combined_repayment = Decimal(combined_total) / selected_fns

            owner = loan.owner
            rounded_interest = round(interest_to_be_paid,2)
            rounded_repayment_amount = round(new_combined_repayment,0)
            rounded_total_to_be_paid = round(combined_total,0)
            
            loan.interest = rounded_interest
            loan.repayment_frequency = 'FORTNIGHLTY'
            loan.location = owner.location
            loan.repayment_amount = rounded_repayment_amount
            loan.total_loan_amount = rounded_total_to_be_paid

            loan.principal_loan_receivable = loan.amount
            loan.ordinary_interest_receivable = loan.interest
            loan.default_interest_receivable = 0
            loan.total_outstanding = loan.total_loan_amount
            loan.save()

            if settings.LOAN_TYPES != 1:
                messages.error(request, 'Administrator needs to enable loan type on application forms first. Please raise a support ticket for this.', extra_tags="danger")
                return redirect('loan_application')
            else:
                loan.type = 'PERSONAL'
            
            # DCC IDENTIFIERS
            loan.uid = owner.uid
            loan.luid = settings.LUID
            loan.save()

            today = funding_date
            loan.status = 'ACTIVE'
            loan.save()

            #new code:
            new_balance = loan.total_outstanding

            #recalculate repayment dates
            fourteendays = datetime.timedelta(days=14)
            
            repayment_start_date = loan.repayment_start_date
            next_payment_date = repayment_start_date + fourteendays
            next_next = next_payment_date + fourteendays
            
            if today < repayment_start_date:
                first_repayment_date = repayment_start_date
            elif repayment_start_date < today < next_payment_date:
                first_repayment_date =  next_payment_date
            elif next_payment_date < today < next_next:
                first_repayment_date = next_next
            else:
                first_repayment_date = next_next + fourteendays
            
            first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

            repayment_dates_list = [first_repayment_date_str]
            last_date = first_repayment_date
            fns = loan.number_of_fortnights
            while fns > 1:
                new_date = last_date + fourteendays
                new_date_str = new_date.strftime('%Y-%m-%d')
                repayment_dates_list.append(new_date_str)
                last_date = new_date
                fns -= 1
            
            # Serialize the list to a JSON string
            loan.set_repayment_dates(repayment_dates_list)
            loan.category = 'FUNDED'
            loan.funded_category = 'ACTIVE'
            loan.status = 'RUNNING'
            loan.funding_date = today
            loan.next_payment_date = first_repayment_date
            loan.save()
            
            user = UserProfile.objects.get(id=loan.owner.id)
            user.number_of_loans += 1
            user.save()

            if settings.PROCESSING_FEE_CHARGABLE == 'YES':
                loan.processing_fee = settings.PROCESSING_FEE
                loan.save()
                Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="FUNDING", statement="Loan Funded", credit=loan.amount-loan.processing_fee, balance=new_balance, date=today, uid=user.uid, luid=settings.LUID)
                Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="OTHER", statement="Loan Processing Fee", credit=loan.processing_fee, balance=new_balance, date=today, uid=user.uid, luid=settings.LUID)
            else:
                Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="FUNDNG", statement=f"Loan Funded", credit=loan.amount, balance=new_balance, date=today, uid=user.uid, luid=settings.LUID)

            #### Update loan balances and everything
            loan.classification = 'NEW'
            loan.save()

            if carry_over_balance > 0:
                loan.total_outstanding += carry_over_balance
                loan.save()
                Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="OTHER", statement=f"Balance carried over from previous loan", credit=carry_over_balance, balance=loan.total_outstanding, date=today, uid=user.uid, luid=settings.LUID)

            messages.success(request, "Loan Created...")
            
            return redirect('custom_functions')
        
            
    else:
        form = AddNewLoanForm()
        
    return render(request, 'functions/add_new_loan.html', { 'nav':'loans', 'form': form })


@check_staff
def end_loan(request):
    if request.method == 'POST':
        loan_ref = request.POST.get('loan_ref')
        description = request.POST.get('statement')
        
        loan = Loan.objects.get(ref=loan_ref)
        user_profile = loan.owner

        today = datetime.date.today()
        
        statement = Statement.objects.create(owner=user_profile, ref=f'{loan_ref}END', 
        loanref=loan, type="OTHER", statement=description, debit=loan.total_outstanding, 
        balance=0.00, date=today,
        uid=user_profile.uid, luid=settings.LUID)
        statement.save()

        loan.status = 'COMPLETED'
        loan.funded_category = 'COMPLETED'
        loan.total_outstanding = 0.00
        loan.save()

        messages.success(request, "Loan Ended!")
        
        return redirect('custom_functions')

    context = {
        'nav': 'end_additional_loan',
    }

    return render(request, 'functions/end_loan.html', context)
