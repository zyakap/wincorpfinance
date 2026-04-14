import json
import datetime
from django.conf import settings
from django.shortcuts import render
from time import sleep
from celery import shared_task
from celery.result import AsyncResult

from accounts.models import UserProfile
from loan.models import Loan, Statement

from wkhtmltopdf.views import PDFTemplateResponse

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
    
#generate pdf on the go
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import subprocess

def generate_pdf(templatefile, data):
    # Load the template
    env = Environment(loader=FileSystemLoader('report/templates'))
    template = env.get_template(templatefile)
    # Render the template with the data
    html = template.render(data)
    result = html
    
    # Create the PDF
    pdf = subprocess.Popen(['wkhtmltopdf', '-', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    pdf_data, _ = pdf.communicate(html.encode('utf-8'))
    #pdf_data = pdf_data.encode('latin1', 'ignore')
    return pdf_data

domain = settings.DOMAIN

from .functions import default_calculator, process_advance_payment, process_default, process_repayment

### CODE STARTS HERE


@shared_task
def download_tc(request, uid, lid):
    domain = settings.DOMAIN
    loan = Loan.objects.get(pk=lid)
    userprofile = UserProfile.objects.get(pk=uid)
    
    data = {'loan':loan, 'user':userprofile, 'domain': domain }
    fname1 = f'{loan.ref}-T&C.pdf',
    template1 = 'custom/termsconditions.html'

    fname2 = f'{loan.ref}-STATDEC.pdf',
    template2 = 'custom/statdec.html'

    fname3 = f'{loan.ref}-STATDEC.pdf', 
    template3 = 'custom/irsd.html'

    response1 = PDFTemplateResponse(
            request=request,
            template = template1,
            filename = fname1[0],
            context = data,
            show_content_in_browser=False,
            cmd_options= {
                'margin-top':10,
                "zoom":1,
                "viewport-size": "1366 x 513",
                'javascript-delay': 1000,
                'footer-center': '[page]/[topage]',
                "no-stop-slow-scripts": True,
            },
        )
    
    response2 = PDFTemplateResponse(
            request=request,                
            template = template2,
            filename = fname2[0],
            context = data,
            show_content_in_browser=False,
            cmd_options= {
                'margin-top':10,
                "zoom":1,
                "viewport-size": "1366 x 513",
                'javascript-delay': 1000,
                'footer-center': '[page]/[topage]',
                "no-stop-slow-scripts": True,
            },)

    response3 = PDFTemplateResponse(
            request=request,
            template = template3,
            filename = fname3[0],
            context = data,
            show_content_in_browser=False,
            cmd_options= {
                'margin-top':10,
                "zoom":1,
                "viewport-size": "1366 x 513",
                'javascript-delay': 1000,
                'footer-center': '[page]/[topage]',
                "no-stop-slow-scripts": True,
            },)       

    print("Loan Associated DOWNLOADs COMPLETED")
    return response1, response2, response3

@shared_task
def payments_expected_today():
    #import datetime
    today = datetime.datetime.today().date()
    print(today)
    loans = Loan.objects.filter(category='FUNDED', funded_category="ACTIVE", next_payment_date=today)
    if loans != None:
        for loan in loans:
            print('REMINDED TODAY')
            print(f'{loan.owner.first_name}: {loan.total_outstanding}')
            loan.reminder1 = 'REMINDED'
            loan.reminder2 = 'UNPAID'
            loan.save()

            #send reminder email

        #send list to admin

    return 1

# reset reminder tag
@shared_task
def default_classification():

    loans = Loan.objects.filter(reminder1='REMINDED')
    print('DEFAULT_CLASS_RAN')

    if loans:

        for loan in loans:
            loan.reminder1 = 'DEFAULTED'
            loan.save()

            print('DEFAULT_CLASS_RAN')

            default_amount = default_calculator()

            loan.amount_remaining += default_amount
            #loan.days_in_default +=  
            loan.last_default_amount = loan.repayment_amount
            loan.last_default_date = loan.next_payment_date
            loan.number_of_defaults += 1
            loan.status = 'DEFAULTED'
            loan.total_arrears += loan.repayment_amount 
            loan.default_interest_receivable += default_amount
            loan.total_outstanding += default_amount
            loan.save()

            #send default email
            userprofile = loan.owner
            
            email_subject=f'DEFAULT ON LOAN - { loan.ref }'
            #
           
            # HTML EMAIL
            html_content = render_to_string("custom/email_temp_general.html", {
                'subject': email_subject,
                'greeting': f'Hi {userprofile.first_name}',
                'cta': 'yes',
                'cta_btn1_label': 'VIEW STATEMENT',
                'cta_btn1_link': f'{settings.DOMAIN}/loan/myloan/{loan.ref}/',
                'message': f'You have defaulted on your loan and a default interest of K{ default_amount } has been added to your loan. This is default No. {loan.number_of_defaults}',
                'message_details': f'This increases your arrears to K{ loan.total_arrears } and your outstanding balance becomes K{ loan.total_outstanding }.',
                'userprofile': userprofile,
                'loan': loan,
                'domain': settings.DOMAIN,
            })
            
            text_content = strip_tags(html_content)

            email_list_one = [userprofile.email, userprofile.work_email, 'admin@trupngfinance.com.pg']
            email_list_two = settings.DEFAULTS_EMAIL
            email_list  = email_list_one + email_list_two

            email = EmailMultiAlternatives(email_subject, text_content, settings.EMAIL_HOST_USER, email_list)
            email.attach_alternative(html_content, "text/html")

            try:
                email.send()
                #messages.success(request, "f'{ userprofile.first_name } { userprofile.last_name } was notified of default.'", extra_tags='info')
            except:
                #messages.error(request, "f'{ userprofile.first_name } { userprofile.last_name } was NOT notified of default.'", extra_tags='danger')
                pass
   
        #send default list to admin 
        
        templatefileloc1 = 'custom/defaults_listing.html'
    
        pdfddatacontext = {
            'domain': settings.DOMAIN,
            'loans': loans,
        }

        pdf_data1 = generate_pdf(templatefileloc1, pdfddatacontext)
        pdf_attachment1 = MIMEApplication(pdf_data1, _subtype='pdf')
        pdf_attachment1.add_header('content-disposition', 'attachment', filename='Defaults_Listing.pdf')
        
        email_subject=f'DEFAULTS LISTING'
        
        # HTML EMAIL
        html_content = render_to_string("custom/email_temp_general.html", {
            'subject': email_subject,
            'greeting': f'Hi',
            'cta': 'yes',
            'cta_btn1_label': 'DEFAULTS LISTING',
            'cta_btn1_link': f'{settings.DOMAIN}/admin1/loans/defaulted/',
            'message': f'Kindly find attached the Pre-filled Loan Application, Terms and Conditions, Statutory Declaration and the Irreovocable Salary Deduction Authority forms for your loan application.',
            'message_details': f'Please read through the documents and sign them. Once signed, please scan each signed document and upload them to complete your loan application. Loan decision will only be made once all these documents are signed and uploaded.',
            'loans': loans,
            'domain': settings.DOMAIN,
        })
        
        text_content = strip_tags(html_content)

        email_list_one = ['admin@trupngfinance.com.pg']
        email_list_two = settings.DEFAULTS_EMAIL
        email_list  = email_list_one + email_list_two
        
        email = EmailMultiAlternatives(email_subject, text_content, settings.EMAIL_HOST_USER, email_list)
        email.attach_alternative(html_content, "text/html")
        
        email.attach(pdf_attachment1)

        try:
            email.send()
            #messages.success(request, "The Terms & Conditions have been emailed to you, Please read, sign if you agree and upload in your requirements section.", extra_tags='info')
        except:
            #messages.error(request, "The Terms & Conditions Agreement email could not be sent, make sure you have internet connection and try apply again.", extra_tags='danger')
            pass

    return 1


@shared_task
def auto_send_repayment_reminder():
    currentdatetime = datetime.datetime.now()
    currentdate = currentdatetime.date()
    print(currentdate)
    loans = Loan.objects.filter(category='FUNDED', funded_category='ACTIVE', next_payment_date=currentdate)
    print(loans)
    if loans:
        print('ENTERED IF')
        for loan in loans:
            print('ENTERED FOR')
            subject = 'LOAN REPAYMENT REMINDER'
            ''' if header_cta == 'yes' '''
            cta_label = ''
            cta_link = ''

            greeting = f'Hi {loan.owner.first_name},'
            message = f'We are kindly reminding you that:'
            message_details = f'Your next repayment of K{round(loan.repayment_amount,2)} is due today. Please make sure to pay on time to avoid a default which will affect your personal credit rating.'

            ''' if cta == 'yes' '''
            cta_btn1_label = 'UPLOAD PAYMENT PROOF'
            cta_btn1_link = f'{settings.DOMAIN}/loan/upload_payment/{loan.ref}/'
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
                'user': loan.owner,
                'domain': domain,
                
            })

            #recipients
            email_list_one = [loan.owner.email,]
            email_list_two = settings.DEFAULTS_EMAIL
            email_list_three = settings.NOTIFICATION_EMAILS
            email_list  = email_list_one + email_list_two + email_list_three

            text_content = strip_tags(email_content)
            email = EmailMultiAlternatives(subject,text_content,sender,email_list)
            email.attach_alternative(email_content, "text/html")
           
            try: 
                print(loan.owner.email)
                email.send()
            except:
                pass
    
    else:
        pass

    return 1

@shared_task
def auto_run_defaults():

    loans = Loan.objects.filter(category='FUNDED', funded_category='ACTIVE')

    for loan in loans:
        if (loan.next_payment_date + datetime.timedelta(days=settings.DEFAULT_INTEREST_CALCULATION_MERCY_DAYS)) < datetime.date.today():

            missed_date = loan.next_payment_date
            default_interest = settings.DEFAULT_INTEREST_RATE * loan.repayment_amount
            loan.last_default_date = missed_date
            loan.number_of_defaults += 1
            loan.last_default_amount = loan.repayment_amount
            if loan.total_arrears < loan.total_outstanding:
                loan.total_arrears += loan.repayment_amount
            else:
                loan.total_arrears = loan.total_outstanding
            loan.default_interest_receivable += default_interest
            loan.total_outstanding += default_interest
            loan.status = 'DEFAULTED'

            repayment_dates = loan.get_repayment_dates()
            repayment_dates.pop(0)
            loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0],'%Y-%m-%d')
            loan.set_repayment_dates(repayment_dates)
            loan.save()

            rounded_default_interest = round(default_interest,2)
            rounded_total_outstanding = round(loan.total_outstanding, 2)

            stat = Statement.objects.create(owner=loan.owner, ref=f'{loan.ref}D{loan.number_of_defaults}', loanref=loan, type="DEFAULT", statement="Loan Defaulted", debit=0, credit=default_interest, arrears=loan.total_arrears, balance=loan.total_outstanding, date=missed_date, default_amount=loan.repayment_amount, default_interest=default_interest)
            stat.save()

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
            email_list_one = [user.email,]
            email_list_two = settings.DEFAULTS_EMAIL
            email_list_three = settings.NOTIFICATION_EMAILS
            email_list  = email_list_one + email_list_two + email_list_three

            text_content = strip_tags(email_content)
            email = EmailMultiAlternatives(subject,text_content,sender,email_list)
            email.attach_alternative(email_content, "text/html")
            
            try: 
                email.send()
            except:
                pass
            
    return 1

@shared_task
def auto_send_test_email():
    
    #send email to user
    subject = f'Test Working'
    ''' if header_cta == 'yes' '''
    cta_label = 'View WEBSITE'
    cta_link = f'{settings.DOMAIN}'

    greeting = f'Hi '
    message = 'You have defaulted on your loan repayment.'
    message_details = f'Default Interest Accumulated: K<br>\
                        Number of Defaults: <br>\
                        Total Arrears: K<br>\
                        TOTAL BALANCE: K'

    ''' if cta == 'yes' '''
    cta_btn1_label = 'View WEBSITE'
    cta_btn1_link = f'{settings.DOMAIN}'
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
        'domain': settings.DOMAIN,
    })
    
    #recipients
    email_list_one = ['admin@trupngfinance.com.pg', 'admin@trupngfinance.com.pg']
    email_list_two = settings.DEFAULTS_EMAIL
    email_list  = email_list_one + email_list_two

    text_content = strip_tags(email_content)
    email = EmailMultiAlternatives(subject,text_content,sender,email_list)
    email.attach_alternative(email_content, "text/html")
    
    try: 
        email.send()
    except:
        pass
    
    return 1
