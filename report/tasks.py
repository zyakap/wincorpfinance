import json
from django.conf import settings
from django.db.models import Sum
from django.shortcuts import render
from time import sleep
from celery import shared_task
from celery.result import AsyncResult

from accounts.models import UserProfile
from loan.models import Loan

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


### CODE STARTS HERE


#@shared_task
def weekly_report():
    
    print("Weekly Report Init")

    templatefileloc1 = 'weekly_report.html'

    activeloans = Loan.objects.filter(category="FUNDED", funded_category="ACTIVE")
    totalbalance = activeloans.aggregate(Sum('total_outstanding'))['total_outstanding__sum']

    
    pdfddatacontext = {
        'totalbalance': totalbalance,
    }

    pdf_data1 = generate_pdf(templatefileloc1, pdfddatacontext)
    pdf_attachment1 = MIMEApplication(pdf_data1, _subtype='pdf')
    pdf_attachment1.add_header('content-disposition', 'attachment', filename='LoanMasta-WeeklyLoansReport.pdf')

    email_subject=f'WEEKLY REPORT FOR LOANS'
    
    # HTML EMAIL
    html_content = render_to_string("custom/email_temp_general.html", {
        'subject': email_subject,
        'greeting': 'Hi',
        'cta': 'yes',
        'cta_btn1_label': 'Login to Dashboard',
        'cta_btn1_link': f'{settings.DOMAIN}/admin/dashboard/',
        'message': f'Kindly find attached the Weekly Report for your Loans.',
        'message_details': f'Please read through the documents and if you need additional insights, you can login to your dashboard and generate additional reports.',
    })
    
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(email_subject, text_content, settings.EMAIL_HOST_USER,[settings.TEST_USER, settings.TEST_RECEIVER ])
    email.attach_alternative(html_content, "text/html")
    
    email.attach(pdf_attachment1)
    
    try:
        email.send()
        print("email_sent")
    except:
        print('Email not sent')


#@shared_task
def monthly_report():
    print("Monthly Report Init")

#@shared_task
def end_of_day_report():
    print("End of Day Report")

