import os
import datetime
import random
import logging
from django.shortcuts import render

#read excel
from http.client import HTTPResponse
import pandas as pd

#from cgi import FieldStorage
#from distutils.command.upload import upload

from socket import gaierror
from decimal import Decimal
from django.conf import settings
#from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect


from accounts.models import UserProfile
from loan.models import Loan, Statement, Payment
from admin1.models import AdminSettings
from message.models import Message, MessageLog

#from django.http import HttpResponse
from loan.forms import LoanApplicationForm, PaymentUploadForm
from loan.forms import PaymentForm
#from .models import UserProfile
from django.contrib import messages

from .functions import id_generator, create_payment

#TOKENIZER

from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode
from loan.tokens import loan_tc_agreement_token
from django.core.files.storage import FileSystemStorage

#EMAIL SETTINGS
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
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

from staff.forms import CreateLoanForm


from accounts.functions import login_check, check_staff

User = get_user_model() 
user = User()

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import subprocess

domain = settings.DOMAIN



#pdfs on the fly
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

@login_check
def loan_application(request):
    owner = UserProfile.objects.get(user_id=request.user.id)
    try:
        if Loan.objects.get(owner=owner, category="FUNDED", funded_category="ACTIVE"):
            messages.error(request, f"You already have an active loan. Please contact {settings.SUPPORT_EMAIL}", extra_tags="warning")
            return redirect('dashboard')
        if Loan.objects.get(owner=owner, category="FUNDED", funded_category="RECOVERY"):
            messages.error(request, f"You already have a loan in recovery. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
            return redirect('dashboard')
        if Loan.objects.get(owner=owner, category="FUNDED", funded_category="BAD"):
            messages.error(request, f"You already have a bad loan with us. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
            return redirect('dashboard')
        if Loan.objects.get(owner=owner, category="FUNDED", funded_category="BAD"):
            messages.error(request, f"You already have a bad loan with us. Please contact {settings.SUPPORT_EMAIL}", extra_tags="danger")
            return redirect('dashboard')
        if Loan.objects.get(owner=owner, category="PENDING", status="UNDER REVIEW"):
            messages.error(request, f"You already have a pending loan under review. Cancel that if you wish to apply for a new one.", extra_tags="warning")
            return redirect('myloans')
        if Loan.objects.get(owner=owner, category="PENDING", status="APPROVED"):
            messages.error(request, f"You already have a pending loan approved. Cancel that if you wish to apply for a new one.", extra_tags="warning")
            return redirect('myloans')
    except:
        pass

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
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('dashboard')
    
    usr = request.user
    uid = usr.id
    loanref_prefix = loan_setting.loanref_prefix
    user = UserProfile.objects.get(user_id=uid)
    upid = user.id
    interest_type = loan_setting.interest_type
    #calculating_interest
    if user.category == "STAFF":
        interest_rate = float(0.15)
    if user.category == "MEMBER":
        interest_rate = float(0.24)
    else:
        interest_rate = float(loan_setting.interest_rate)/100
    
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
            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.save()

            loan.owner_id = upid
            loan.type = form.cleaned_data['type']
            loan.amount = form.cleaned_data['amount']
            num_fns = form.cleaned_data['number_of_fortnights']
            
            if num_fns < 1 or num_fns > 26:
                loan.delete()
                messages.error(request, "Number of fortnights must be between 1 and 26.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.number_of_fortnights = num_fns
            start_of_payment = form.cleaned_data['repayment_start_date']
            now = datetime.date.today()
            after_fourteen_days = now + datetime.timedelta(days=14)
            
            """ if start_of_payment < now:
                loan.delete()
                messages.error(request, "The Start Date can not be in past. The date must be from now and 14 days.", extra_tags='danger')
                return redirect('loan_application') """
            
            if start_of_payment > after_fourteen_days:
                loan.delete()
                messages.error(request, "The Start Date can not be after 14 days from now. The date must be between now and 14 days.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.repayment_start_date = start_of_payment
            loan.save()
            
            #calculating_interest
            
            selected_fns = loan.number_of_fortnights
            amt = float(loan.amount)
            term_year = 1
            fortnights = 26 * term_year
            fortnight_interest_rate = ((1.0+ interest_rate)**(1.0/12.0))-1.0
            fir = float(fortnight_interest_rate) + 1
            nt = fortnights
            exp = fir ** float(nt)
            denominator = exp -1 
            pmt = ( amt * fortnight_interest_rate * exp ) / denominator
            
            app_fee = 0.01 * amt
            loan_amt_int = pmt * fortnights
            loan_amt_int_fees = loan_amt_int + app_fee
            fortnightly_repayment = loan_amt_int_fees / selected_fns

            total_to_be_paid = loan_amt_int_fees
            interest_to_be_paid = loan_amt_int - amt
            
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
            loan.repayment_amount = rounded_repayment_amount
            loan.total_loan_amount = rounded_total_to_be_paid
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

            email_subject=f'Required Signed Documents for Loan - { final_ref }'
            
            # HTML EMAIL
            html_content = render_to_string("custom/email_temp_general.html", {
                'subject': email_subject,
                'greeting': f'Hi {user.first_name}',
                'cta': 'yes',
                'cta_btn1_label': 'UPLOAD SIGNED DOCUMENTS',
                'cta_btn1_link': f'{settings.DOMAIN}/loan/myloan/{loan.ref}/',
                'message': f'Kindly find attached the Pre-filled Loan Application, Terms and Conditions, Statutory Declaration and the Irreovocable Salary Deduction Authority forms for your loan application.',
                'message_details': f'Please read through the documents and sign them. Once signed, please scan each signed document and upload them to complete your loan application. Loan decision will only be made once all these documents are signed and uploaded.',
                'user': usr,
                'userprofile': user,
                'loan': loan,
                'domain': settings.DOMAIN,
                'uid': urlsafe_base64_encode(force_bytes(usr.pk)),
                'token': loan_tc_agreement_token.make_token(usr),
            })
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(email_subject, text_content, settings.EMAIL_HOST_USER,[user.email, 'admin@trupngfinance.com.pg'])
            email.attach_alternative(html_content, "text/html")
            
            """ email.attach(pdf_attachment1)
            email.attach(pdf_attachment2)
            email.attach(pdf_attachment3)
            email.attach(pdf_attachment4) """

            #clear existing loans that were not agreed to
            loans = Loan.objects.filter(owner_id=uid, tc_agreement='tct')

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
        
    return render(request, 'loan_application_form.html', { 'nav':'loan_application', 'form': form, "repayment_limit": repayment_limit, 'interest_rate': interest_rate, 'user': user })

               
@check_staff
def payment(request, loan_ref):
    
    loan = Loan.objects.get(ref=loan_ref)
    loid = loan.owner.id
    user = UserProfile.objects.get(pk=loid)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            
            ref = loan
            date = form.cleaned_data['date']
            amount = form.cleaned_data['amount']
            mode = form.cleaned_data['mode']
            statement = form.cleaned_data['statement']
            
            paymnt = Payment.objects.create(owner = user, loanref=ref, date=date, amount=amount, mode=mode, statement=statement)
            stat = Statement.objects.create(owner = user, loanref=ref, date=date, debit=amount, statement=statement)
            
            num_payments = loan.number_of_repayments
            
            p_count = num_payments + 1
            paymnt.ref = f'{loan_ref}P{p_count}'
            paymnt.p_count = p_count
            paymnt.save()
            
            all_statements = Statement.objects.filter(loanref=loan).all().count()
            
            stat.s_count = all_statements
            stat.ref = f'{loan_ref}SP{stat.s_count}' 
            stat.type = 'PAYMENT'
            stat.save()
            
            ramount = loan.repayment_amount 
            
            app_fee_non_rounded = loan.application_fee / loan.number_of_fortnights
            interest_non_rounded = loan.interest / loan.number_of_fortnights
            
            app_fee = round(app_fee_non_rounded,2)
            interest = round(interest_non_rounded,2)
            
            edi = loan.default_interest_receivable
            arrears = loan.total_arrears
            balance = loan.total_outstanding
            
            tol_pos = Decimal(0.99) 
            tol_neg = Decimal(-0.99)
            
            tol_neg_amount = ramount + tol_neg
            tol_pos_amount = ramount + tol_pos
            
            # Check if amount is equal to repayment amount 
            
            if tol_neg_amount<amount<tol_pos_amount:
                
                if edi != 0.00 and edi < amount:
                    loan_amount = amount - (app_fee + interest + edi)
                    
                    stat.default_interest_collected = edi
                    stat.loan_amount = loan_amount
                    stat.application_fee = app_fee
                    stat.interest = interest
                    stat.arrears = arrears
                    stat.balance = balance - amount
                    stat.save()
                
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.default_interest_paid += edi
                    loan.default_interest_receivable = 0.00
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.status = 'RUNNING'
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, Default Interest Offset Done')
                    
                    return redirect('loans')
                
                if edi != 0.00 and edi > amount:
                    
                    loan_amount = 0
                    edi_remainder = edi - amount 
                    stat.interest_on_default = edi_remainder
                    stat.default_interest_collected = amount
                    stat.balance = balance - amount
                    stat.arrears = arrears
                    stat.save()
                    
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += loan_amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.default_interest_paid += amount
                    loan.default_interest_receivable -= amount
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, Default Interest REDUCED and remainder brought forward')
                    
                    return redirect('loans')

                if edi == 0.00:
                    
                    loan_amount = amount - (app_fee + interest)
                    
                    stat.loan_amount = loan_amount
                    stat.application_fee = app_fee
                    stat.interest = interest
                    stat.arrears = arrears
                    stat.balance = balance - amount
                    stat.save()
                
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.interest_remaining -= interest
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, NO Default Interest to Offset')
                       
                    return redirect('loans')
                    
            
            if tol_neg_amount>amount:
                
                if edi != 0.00 and edi < amount:
                    
                    loan_amount = amount - (app_fee + interest + edi)
                    
                    stat.default_interest_collected = edi
                    stat.loan_amount = loan_amount
                    stat.application_fee = app_fee
                    stat.interest = interest
                    stat.arrears = arrears
                    stat.balance = balance - amount
                    stat.save()
                
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.default_interest_paid += edi
                    loan.default_interest_receivable = 0.00
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.status = 'RUNNING'
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, Default Interest Offset Done')
                    
                    return redirect('loans')
                
                if edi != 0.00 and edi > amount:
                    
                    loan_amount = 0
                    edi_remainder = edi - amount 
                    stat.interest_on_default = edi_remainder
                    stat.default_interest_collected = amount
                    stat.balance = balance - amount
                    stat.arrears = arrears
                    stat.save()
                    
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += loan_amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.default_interest_paid += amount
                    loan.default_interest_receivable -= amount
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, Default Interest REDUCED and remainder brought forward')
                    
                    return redirect('loans')

                if edi == 0.00:
                    
                    loan_amount = amount - (app_fee + interest)
                    
                    stat.loan_amount = loan_amount
                    stat.application_fee = app_fee
                    stat.interest = interest
                    stat.arrears = arrears
                    stat.balance = balance - amount
                    stat.save()
                
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.interest_remaining -= interest
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, NO Default Interest to Offset')
                       
                    return redirect('loans')
                
                
                return redirect('loans')
            if tol_pos_amount<amount:
            
                if edi != 0.00 and edi < amount:
                    
                    loan_amount = amount - (app_fee + interest + edi)
                    
                    stat.default_interest_collected = edi
                    stat.loan_amount = loan_amount
                    stat.application_fee = app_fee
                    stat.interest = interest
                    stat.arrears = arrears
                    stat.balance = balance - amount
                    stat.save()
                
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.default_interest_paid += edi
                    loan.default_interest_receivable = 0.00
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.status = 'RUNNING'

                    

                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, Default Interest Offset Done')
                    
                    return redirect('loans')
                
                if edi != 0.00 and edi > amount:
                    
                    loan_amount = 0
                    edi_remainder = edi - amount 
                    stat.interest_on_default = edi_remainder
                    stat.default_interest_collected = amount
                    stat.balance = balance - amount
                    stat.arrears = arrears
                    stat.save()
                    
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += loan_amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.default_interest_paid += amount
                    loan.default_interest_receivable -= amount
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, Default Interest REDUCED and remainder brought forward')
                    
                    return redirect('loans')

                if edi == 0.00:
                    
                    loan_amount = amount - (app_fee + interest)
                    
                    stat.loan_amount = loan_amount
                    stat.application_fee = app_fee
                    stat.interest = interest
                    stat.arrears = arrears
                    stat.balance = balance - amount
                    stat.save()
                
                    loan.last_repayment_amount = amount
                    loan.last_repayment_date = date
                    loan.number_of_repayments += 1
                    loan.total_paid += amount
                    loan.amount_remaining = loan.total_loan_amount - loan.total_paid
                    loan.interest_remaining -= interest
                    loan.total_outstanding = stat.balance
                    loan.next_payment_date = date + datetime.timedelta(days=14)
                    loan.save()
                    
                    repay_dates = loan.repayment_dates.split(',')
                    print(repay_dates)
                    str_date = str(date)
                    print(str_date)
                    
                    if str(date) in repay_dates:
                        new_dates = repay_dates.delete(str(date))
                        loan.repayment_dates = new_dates.join(',')
                        loan.next_payment_date = date + datetime.timedelta(days=14)
                        loan.save()
                        messages.success(request, 'Repayment Date Updated')
                    
                    messages.success(request, 'Loan Updated, NO Default Interest to Offset')
                       
                    return redirect('loans')
                
        return redirect('loans')
            
    else:
        form = PaymentForm()        
    
    return render(request, 'payment.html', { 'loan_ref': loan_ref, 'form': form })


@check_staff
def create_loan(request):
    

    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('dashboard')

    if request.method == 'POST':
        form = CreateLoanForm(request.POST)
        if form.is_valid():

            owner = form.cleaned_data['owner']
            location = form.cleaned_data['location']
            loantype = form.cleaned_data['type']
            amount = form.cleaned_data['amount']
            num_fns = form.cleaned_data['number_of_fortnights']

            repayment_start_date = form.cleaned_data['repayment_start_date']
            user = owner
            loanref_prefix = loan_setting.loanref_prefix
            upid = user.id
            first_name = user.first_name
            last_name = user.last_name
            rand = random.randint(0,9)
            refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
            repayment_limit = user.repayment_limit
            
            if repayment_limit == 0.0:
                messages.error(request, 'Repayment limit for this user is not set yet, please view user and set it from profile action.', extra_tags='info')
                return redirect('userloans')
            
            if loan_setting.credit_check == 'YES':
                if not user.active:
                    return redirect('inactive')
                if user.defaulted:
                    return redirect('defaulted')
                if user.suspended:
                    return redirect('suspended')
                if user.dcc_flagged:
                    return redirect('dcc_flagged')
                if user.cdb_flagged:
                    return redirect('cdb_flagged')

            loan = Loan.objects.create(ref = refx, officer=request.user, owner=owner, location=location, type=loantype, amount=amount)
            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'

            loan.ref = final_ref
            loan.save()

            if num_fns < 1 or num_fns > 26:
                loan.delete()
                messages.error(request, "Number of fortnights must be between 1 and 26.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.number_of_fortnights = num_fns
            
            start_of_payment = repayment_start_date
            
            now = datetime.date.today()
            after_fourteen_days = now + datetime.timedelta(days=14)
            
            """   if start_of_payment < now:
                loan.delete()
                messages.error(request, "The Start Date can not be in past. The date must be from now and 14 days.", extra_tags='danger')
                return redirect('loan_application') """
            
            if start_of_payment > after_fourteen_days:
                loan.delete()
                messages.error(request, "The Start Date can not be after 14 days from now. The date must be between now and 14 days.", extra_tags='danger')
                return redirect('loan_application')
            
            loan.repayment_start_date = start_of_payment
            loan.save()

            #calculating_interest
            if user.category == "STAFF":
                interest_rate = float(0.15)
            if user.category == "MEMBER":
                interest_rate = float(0.24)
            else:
                interest_rate = float(loan_setting.interest_rate)/100
            
            selected_fns = loan.number_of_fortnights
            amt = float(loan.amount)
            term_year = 1
            fortnights = 26 * term_year
            fortnight_interest_rate = ((1.0+ interest_rate)**(1.0/12.0))-1.0
            fir = float(fortnight_interest_rate) + 1
            nt = fortnights
            exp = fir ** float(nt)
            denominator = exp -1 
            pmt = ( amt * fortnight_interest_rate * exp ) / denominator
            
            app_fee = 0.01 * amt
            loan_amt_int = pmt * fortnights
            loan_amt_int_fees = loan_amt_int + app_fee
            fortnightly_repayment = loan_amt_int_fees / selected_fns
            total_to_be_paid = loan_amt_int_fees
            interest_to_be_paid = loan_amt_int - amt

            rounded_interest = round(interest_to_be_paid,2)
            rounded_repayment_amount = round(fortnightly_repayment,2)     
            rounded_total_to_be_paid = round(total_to_be_paid, 2)

            if repayment_limit is None:
                loan.delete()
                messages.error(request, 'Repayment Limit is not set yet. Please advise admin to set that first.', extra_tags="danger")
                return redirect('userloans')

            if fortnightly_repayment > repayment_limit:
                loan.delete()
                messages.error(request, f'The repayment amount of K{rounded_repayment_amount} for this loan is greater than the user\'s personal repayment limit of K{repayment_limit}. Please apply again within repayment limit.', extra_tags='danger')
                return redirect('userloans') 

            loan.interest = rounded_interest
            loan.repayment_frequency = 'FORTNIGHLTY'
            loan.category = 'PENDING'
            loan.status = 'AWAITING T&C'
            loan.repayment_amount = rounded_repayment_amount
            loan.application_fee = app_fee
            loan.total_loan_amount = rounded_total_to_be_paid

            loan.save()
        
            messages.success(request, "Loan application has been created successfully...")
            
            return redirect('userloans_unfinished')
    else:
        form = CreateLoanForm()
        
    return render(request, 'create_loan.html', { 'nav':'loans', 'form': form })        
    

@check_staff
def make_default_entry(request, loanref):

    if request.method == 'POST':
        
        dateinput = request.POST.get('date')
        date = datetime.datetime.strptime(dateinput, '%Y-%m-%d').date()
        loan = Loan.objects.get(ref=loanref)
        owner = loan.owner
        repayamt = loan.repayment_amount
        dint = Decimal(0.2)*repayamt
        bal = loan.total_outstanding
        bal_int = loan.total_outstanding + dint
        arrears = loan.total_arrears + repayamt

        stat = Statement.objects.create(owner=owner, loanref=loan, date=date, default_amount=repayamt, interest_on_default=dint,loan_amount=bal, balance=bal_int, arrears=arrears)

        stat.s_count += 1
        stat.ref = f'{loanref}SD{stat.s_count}'
        stat.statement = 'Default' 
        stat.type = 'DEFAULT'
        stat.save()

        loan.status = 'DEFAULTED'
        loan.last_default_date = date
        loan.number_of_defaults += 1
        loan.last_default_amount = repayamt
        loan.days_in_default = 0
        loan.total_arrears += repayamt
        loan.default_interest_receivable = dint
        loan.total_outstanding += dint
        loan.save()
        
        messages.success(request, "Loan Statement was updated with Default.")
        return redirect('userloans')

    return render(request, 'make_default.html', {'nav': 'userloans', })

@check_staff
def add_existing_loan(request):

    try:
        loan_setting = AdminSettings.objects.get(settings_name='setting1')
    except: 
        messages.error(request, f"Loan Administrator needs to update their settings first. Please contact issues@{domain}.com", extra_tags="danger")
        return redirect('staff_dashboard')

    try: 
        if request.method == 'POST' and request.FILES['uploadedloans']:      
            uploadedloans = request.FILES['uploadedloans']
            fs = FileSystemStorage()
            filename = fs.save(uploadedloans.name, uploadedloans)
            uploaded_file_url = fs.url(filename)
            full_path = settings.DOMAIN + uploaded_file_url        
            loanexceldata = pd.read_excel(full_path)
            dbframe = loanexceldata

            for dbframe in dbframe.itertuples():
                first_name = dbframe.firstName
                last_name = dbframe.lastName
                employer = dbframe.employer
                loan_type = dbframe.loanType
                funded_category = dbframe.fundedCategory
                status = dbframe.status
                loan_amount = dbframe.loanAmount
                total_interest = dbframe.totalInterest
                application_fee = dbframe.applicationFee
                total_loan = dbframe.totalLoan
                number_of_fortnights = dbframe.numberOfFortnights
                start_deduction_date = dbframe.startDeductionDate
                end_deduction_date = dbframe.endDeductionDate
                repayment_amount = dbframe.repaymentAmount
                funding_date = dbframe.fundingDate
                
                #creating the user and userprofile

                randomid = id_generator(3).lower()
                random_email = f'{first_name[0]}{last_name[0]}{first_name[-1]}'.lower()
                password = f'{random_email}{randomid}'

                email = f'{random_email}@{settings.DOMAIN_DNS}'
                try:
                    user = User.objects.create_user(email=email, is_active=True, is_confirmed=True, password=password)
                    user.active=True
                    user.confirmed=True
                    user.save()
                except:
                    user = User.objects.get(email=email)

                #Creating the UserProfile
                try:
                    userprofile = UserProfile.objects.create(user=user, first_name=first_name, last_name=last_name, email=email, employer=employer, officer=request.user.id)
                    userprofile.save()
                except:
                    userprofile = UserProfile.objects.get(user=user)
                    userprofile.first_name = first_name
                    userprofile.last_name = last_name
                    userprofile.email = email
                    userprofile.employer = employer
                    userprofile.officer = request.user.id
                    userprofile.save()

                try:
                    prefix = loan_setting.loanref_prefix
                except:
                    prefix = 'LMX'
                
                year = str(datetime.datetime.today().year)[2:]
                month = datetime.datetime.today().month
                uid = userprofile.id
                userprofile.uid = f'{prefix}{year}{month}{uid}'
                userprofile.save()
                
                try:
                    messagelog = MessageLog.objects.create(user=userprofile)
                    messagelog.save()
                except:
                    print('messagelog not created')
                    pass
                
                #Create the Loan

                loanref_prefix = loan_setting.loanref_prefix
                upid = user.id
                first_name = userprofile.first_name
                last_name = userprofile.last_name
                rand = random.randint(0,9)
                refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
                #set repayment limit
                userprofile.activation = 1
                userprofile.repayment_limit = Decimal(repayment_amount)+ Decimal(100.0)
                userprofile.save()
                #staff_location
                location = UserProfile.objects.get(user=request.user).location

                loan = Loan.objects.create(ref=refx, officer=request.user, owner=userprofile, location=location, type=loan_type, amount=loan_amount,
                                        application_fee=application_fee, interest=total_interest, total_loan_amount=total_loan, repayment_frequency='FORTNIGHTLY',
                                        number_of_fortnights=number_of_fortnights, category="FUNDED", funded_category=funded_category, status=status, tc_agreement="YES",
                                        tc_agreement_timestamp=funding_date, funding_date=funding_date, repayment_start_date=start_deduction_date, expected_end_date=end_deduction_date,
                                        repayment_amount=repayment_amount, total_outstanding=total_loan)
                loan_id = loan.id
                str_loan_id = str(loan_id)
                finalref_first_part = refx[:-1]
                final_ref = f'{finalref_first_part}{str_loan_id}'
                loan.ref = final_ref
                loan.classification = 'OLD'
                loan.save()

                #create the loan statement
                statement = Statement.objects.create(owner=userprofile, ref = f'{final_ref}F', loanref = loan, type="OTHER", statement="Loan Funded", credit=loan.amount, loan_amount=loan.amount, interest=loan.interest, application_fee=loan.application_fee, balance=loan.total_loan_amount, date = funding_date)
                statement.save()

                messages.success(request, f"Loan for {first_name} {last_name} has been created successfully...")
                
            return redirect('userloans_all')
    
    except:
        messages.error(request, f"You did not upload any file...", extra_tags="danger") 
        return render(request, 'import_existing_loans.html',{'nav': 'add_existing_loan'})  

    return render(request, 'import_existing_loans.html',{'nav': 'add_existing_loan'})


@check_staff
def add_existing_loan_statement(request):
    loans = Loan.objects.filter(category='FUNDED', classification='OLD')
    return render(request, 'existing_loans.html',{'nav': 'add_existing_loan_statement', 'loans': loans})

@check_staff
def upload_statement(request, loanref):
    loan = Loan.objects.get(ref=loanref)
    owner = loan.owner 
    repayment_amount = loan.repayment_amount

    try:
        if request.method == 'POST' and request.FILES['uploadedstatement']:
            uploadedstatement = request.FILES['uploadedstatement']
            fs = FileSystemStorage()
            filename = fs.save(uploadedstatement.name, uploadedstatement)
            uploaded_file_url = fs.url(filename)
            full_path = settings.DOMAIN + uploaded_file_url        
            statementexceldata = pd.read_excel(full_path)
            dbframe = statementexceldata

            for dbframe in dbframe.itertuples():
                date = dbframe.date
                comment = dbframe.comment
                mode = dbframe.mode
                debit = dbframe.debit
                credit = dbframe.credit

                if debit == 0 and credit == 0:
                    default_interest = Decimal(0.2) * repayment_amount
                    loan.last_default_date = date
                    loan.number_of_defaults += 1
                    loan.last_default_amount = repayment_amount
                    if loan.total_arrears < loan.total_outstanding:
                        loan.total_arrears += repayment_amount
                    else:
                        loan.total_arrears = loan.total_outstanding
                    loan.total_outstanding += default_interest
                    loan.status = 'DEFAULTED'
                    loan.save()

                    stat = Statement.objects.create(owner=owner, ref = f'{loanref}D{loan.number_of_defaults}', loanref = loan, type="DEFAULT", statement=comment, debit=0, credit=0, arrears=loan.total_arrears, balance=loan.total_outstanding, date = date, default_amount=repayment_amount, interest_on_default=default_interest)
                    stat.save()
                    #if this is finished, go to next statement
                    continue
                
                elif debit == 0 and credit > 0:
                    loan.total_outstanding += credit
                    loan.save()
                    stat = Statement.objects.create(owner=owner, ref = f'{loanref}OF', loanref = loan, type="OTHER", statement=comment, credit=credit, balance=loan.total_outstanding, date=date)
                    stat.save()
                    #if this is finished, go to next statement
                    continue

                elif debit > 0 and credit == 0:
                    
                    try:
                        stat, loan = create_payment(loanref, debit, date, mode=mode, statement=comment)
                        stat.save()
                        loan.save()
                        continue
                    except BaseException as e:
                        logging.error(f'Error creating statement for {loanref}: ' + str(e))
                        return redirect('userloans')
                else:
                    messages.error(request, f"There are some 'FORMAT ERROR' in the Excel spreadsheet you uploaded. Check for correct formating of all cells.", extra_tags="danger")
                    return render(request, 'upload_statement.html',{'nav': 'add_existing_loan_statement', 'loan': loan})
                    
            messages.success(request, f"All Statement for {loanref} has been uploaded & created successfully...")
            return render(request, 'upload_statement.html',{'nav': 'add_existing_loan_statement', 'loan': loan})
        
    except:
        messages.error(request, f"You did not upload any file...", extra_tags="danger") 
        return render(request, 'upload_statement.html',{'nav': 'add_existing_loan_statement', 'loan': loan})

    return render(request, 'upload_statement.html',{'nav': 'add_existing_loan_statement', 'loan': loan})
