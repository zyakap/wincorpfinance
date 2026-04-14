from django.conf import settings
from accounts.models import UserProfile
from loan.models import Loan, LoanFile
from message.functions import email_admin, send_email

import datetime
from decimal import Decimal
import string
import random
import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect

#read excel
from http.client import HTTPResponse
#import pandas as pd

from admin1.models import AdminSettings, Location
from accounts.models import User, UserProfile, StaffProfile
from message.models import Message, MessageLog
from loan.models import Loan, LoanFile, Statement

#EMAIL SETTINGS
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.html import strip_tags
#admin sender email
from admin1.models import AdminSettings
sender = settings.DEFAULT_SENDER_EMAIL




from django.contrib import messages

def request_approval(loan):
    loanfile = LoanFile.objects.get(loan=loan)
    userprofile = loan.owner
    domain = settings.DOMAIN

    if loanfile.application_form_url and loanfile.terms_conditions_url and loanfile.stat_dec_url and loanfile.irr_sd_form_url and loanfile.bank_statement_url and loanfile.payslip1_url and loanfile.payslip2_url and loanfile.work_confirmation_letter_url:
        loan.status = 'UNDER REVIEW'
        loan.save()
        email_admin(userprofile, sub=f'Loan Application - {loan.ref} - READY FOR APPROVAL', gr='Hi,',msg='Loan application is ready for Approval. Please review the application and make a decision.', cta='yes', btnlab='View Loan', btnlink=f'{settings.DOMAIN}/admin/loans/{loan.ref}/')
        send_email(userprofile, sub=f'Loan Application {loan.ref} - UNDER REVIEW', gr=f'Hi {userprofile.first_name},', msg='Your loan application is now under review for approval.', cta='yes', btn_lab='View Loan', b_link=f'{settings.DOMAIN}/loan/myloan/{loan.ref}/')
        print("IT CAME THIS FAR")
        return True


def default_calculator():

    default_amount = settings.DEFAULT_INTEREST

    return default_amount


def complete_loan(request, loan):

    userprofile = UserProfile.objects.get(pk=loan.owner.id)
    userprofile.has_loan = False
    userprofile.save()

    loan.funded_category = 'COMPLETED'
    loan.status = 'COMPLETED'
    loan.total_outstanding = 0
    loan.principal_loan_receivable = 0
    loan.ordinary_interest_receivable = 0
    loan.default_interest_receivable = 0
    loan.save()


    #send email to user
    subject = f'Congratulations! {loan.ref} is COMPLETE'
    ''' if header_cta == 'yes' '''
    cta_label = 'View Loan'
    cta_link = f'{settings.DOMAIN}/loan/myloan/{loan.ref}/'

    greeting = f'Hi {loan.owner.first_name}'
    message = 'We are glad to advise you that your loan is now completed.'
    message_details = f'We thank you for borrowing from us. You have been a good customer\
                        and we look forward to lend to you again whenever you need our services.'

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
        'user': userprofile,
        'domain': settings.DOMAIN,
    })
    
    #recipients
    email_list_one = [userprofile.email, 'admin@trupngfinance.com.pg']
    email_list_two = settings.ADMIN_EMAILS
    email_list  = email_list_one + email_list_two

    text_content = strip_tags(email_content)
    email = EmailMultiAlternatives(subject,text_content,sender,email_list)
    email.attach_alternative(email_content, "text/html")
    
    try: 
        email.send()
        messages.success(request, f'Loan Completion Note sent to {loan.owner.first_name} {loan.owner.last_name} successfully.')
    except:
        messages.error(request, 'Loan Completion notice not sent.', extra_tags='danger')

    return 1


def process_advance_payment(request,loan,stat,amount):
    user = loan.owner
    
    arrears = loan.total_arrears
    balance = loan.total_outstanding
    date = stat.date

    if arrears < amount:
        stat.arrears = 0
        loan.total_arrears = 0
    else:
        stat.arrears = arrears - amount
        loan.total_arrears -= amount
    
    #complete loan
    closing_balance = balance - settings.LOAN_COMPLETION_BALANCE
    if closing_balance < amount:
        completion_response = complete_loan(request, loan)
        if completion_response == 1:
            stat.type="COMPLETE PAYMENT"
            stat.save()
            messages.success(request, 'Loan completed.', extra_tags='info')
            return redirect('staff_dashboard')

    stat.balance = balance - amount
    stat.type = 'PAYMENT'
    stat.save()

    if loan.default_interest_receivable > 0:

        principal_repayment_percentage = (loan.principal_loan_receivable / loan.total_outstanding)
        interest_repayment_percentage = (loan.ordinary_interest_receivable / loan.total_outstanding)
        default_repayment_percentage = (loan.default_interest_receivable / loan.total_outstanding)
        
        principal_repayment = amount * principal_repayment_percentage
        interest_repayment = amount * interest_repayment_percentage
        default_repayment = amount * default_repayment_percentage
        
        loan.principal_loan_receivable -= principal_repayment
        loan.ordinary_interest_receivable -= interest_repayment
        loan.default_interest_receivable -= default_repayment
        
        loan.principal_loan_paid += principal_repayment
        loan.interest_paid += interest_repayment
        loan.default_interest_paid += default_repayment
        loan.save()

        stat.principal_collected = principal_repayment
        stat.interest_collected = interest_repayment
        stat.default_interest_collected = default_repayment
        stat.save()

    else:
        principal_repayment_percentage = (loan.principal_loan_receivable / loan.total_outstanding)
        interest_repayment_percentage = (loan.ordinary_interest_receivable / loan.total_outstanding)
        
        principal_repayment = amount * principal_repayment_percentage
        interest_repayment = amount * interest_repayment_percentage
        
        loan.principal_loan_receivable -= principal_repayment
        loan.ordinary_interest_receivable -= interest_repayment

        loan.principal_loan_paid += principal_repayment
        loan.interest_paid += interest_repayment
        loan.save()

        stat.principal_collected = principal_repayment
        stat.interest_collected = interest_repayment
        stat.save()
    
    loan.last_repayment_amount = amount
    loan.last_repayment_date = date
    loan.number_of_repayments += 1
    loan.total_paid += amount
    loan.total_outstanding -= amount

    # Get the list of repayment dates
    date = datetime.datetime(date.year, date.month, date.day)
    repayment_dates = loan.get_repayment_dates()
    if date >= datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d'):
        repayment_dates.pop(0)
        loan.set_repayment_dates(repayment_dates)
        loan.save()
    print(f'ADVANCE: NEXT REPAYMENT DATE IS: {repayment_dates[0]}')
    loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
    loan.save()

    #extra
    loan.status = "RUNNING"
    loan.last_advance_payment_date = date
    loan.last_advance_payment_amount = amount
    loan.number_of_advance_payments += 1
    #loan.total_arrears -= amount
    loan.total_advance_payment += amount
    if amount > loan.repayment_amount:
        loan.advance_payment_surplus = (amount - loan.repayment_amount)
    else:
        loan.advance_payment_surplus = 0

    loan.save()
    
    #send email to customer
    subject=f'Payment updated for Loan - {loan.ref}'
    message = f'Thank you for Advance Payment of K{round(amount,2)}.'
    message_details = f'Total Outstanding Balance: K{round(loan.total_outstanding, 2)}<br>\
                        Total Arrears: K{round(loan.total_arrears, 2)}'
    status = send_email(user, sub=subject, gr=f'Hi {user.first_name}', msg=message, msg_details=message_details, cta='no', btn_lab='View Statement', b_link=f'{settings.DOMAIN}/loan/mystatements/', msgid=None, attachcheck='no', path='')
    if status == 1:
        messages.success(request, 'Advance payment registered.', extra_tags='info')
    else:
        messages.error(request, 'Payment advise email not sent.', extra_tags='warning')
    
    return redirect('staff_enter_payment')

def process_repayment(request,loan,stat,amount):
    user = loan.owner
    arrears = loan.total_arrears
    balance = loan.total_outstanding
    date = stat.date

    if arrears < amount:
        stat.arrears = 0
        loan.total_arrears = 0
    else:
        stat.arrears = arrears - amount
        loan.total_arrears -= amount
    
    #complete loan
    closing_balance = balance - settings.LOAN_COMPLETION_BALANCE
    if closing_balance < amount:
        completion_response = complete_loan(request, loan)
        if completion_response == 1:
            stat.type="COMPLETE PAYMENT"
            stat.save()
            messages.success(request, 'Loan completed.', extra_tags='info')
            return redirect('staff_dashboard')
    
    stat.balance = balance - amount
    stat.type = 'PAYMENT'
    stat.save()

    if loan.default_interest_receivable > 0:

        principal_repayment_percentage = (loan.principal_loan_receivable / loan.total_outstanding)
        interest_repayment_percentage = (loan.ordinary_interest_receivable / loan.total_outstanding)
        default_repayment_percentage = (loan.default_interest_receivable / loan.total_outstanding)
        
        principal_repayment = amount * principal_repayment_percentage
        interest_repayment = amount * interest_repayment_percentage
        default_repayment = amount * default_repayment_percentage
        
        loan.principal_loan_receivable -= principal_repayment
        loan.ordinary_interest_receivable -= interest_repayment
        loan.default_interest_receivable -= default_repayment
        
        loan.principal_loan_paid += principal_repayment
        loan.interest_paid += interest_repayment
        loan.default_interest_paid += default_repayment
        loan.save()

        stat.principal_collected = principal_repayment
        stat.interest_collected = interest_repayment
        stat.default_interest_collected = default_repayment
        stat.save()

    else:
        principal_repayment_percentage = (loan.principal_loan_receivable / loan.total_outstanding)
        interest_repayment_percentage = (loan.ordinary_interest_receivable / loan.total_outstanding)
        
        principal_repayment = amount * principal_repayment_percentage
        interest_repayment = amount * interest_repayment_percentage
        
        loan.principal_loan_receivable -= principal_repayment
        loan.ordinary_interest_receivable -= interest_repayment

        loan.principal_loan_paid += principal_repayment
        loan.interest_paid += interest_repayment
        loan.save()

        stat.principal_collected = principal_repayment
        stat.interest_collected = interest_repayment
        stat.save()

    loan.last_repayment_amount = amount
    loan.last_repayment_date = date
    loan.number_of_repayments += 1
    loan.total_paid += amount
    loan.total_outstanding -= amount
    #loan.next_payment_date = date + datetime.timedelta(days=14)
    
    # Get the list of repayment dates
    date = datetime.datetime(date.year, date.month, date.day)
    repayment_dates = loan.get_repayment_dates()
    last_repayment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
    if date >= datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d'):
        repayment_dates.pop(0)
        if len(repayment_dates) == 0:
            #add 14 days to the last repayment date
            new_next_repayment_date = last_repayment_date + datetime.timedelta(days=14)
            repayment_dates.append(new_next_repayment_date.strftime('%Y-%m-%d'))
        loan.set_repayment_dates(repayment_dates)
        loan.save()
    print(f'NORMAL: NEXT REPAYMENT DATE IS: {repayment_dates[0]}')
    loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
    loan.save()
    
    #send email to customer
    subject=f'Payment updated for Loan - {loan.ref}'
    message = f'Thank you for Payment of K{round(amount,2)}.'
    message_details = f'Total Outstanding Balance: K{round(loan.total_outstanding, 2)}<br>\
                        Total Arrears: K{round(loan.total_arrears, 2)}'
    status = send_email(user, sub=subject, gr=f'Hi {user.first_name}', msg=message, msg_details=message_details, cta='no', btn_lab='View Statement', b_link=f'{settings.DOMAIN}/loan/mystatements/', msgid=None, attachcheck='no', path='')
    if status == 1:
        messages.success(request, 'Payment registered.', extra_tags='info')
    else:
            messages.error(request, 'Payment advise email not sent.', extra_tags='warning')

    return redirect('staff_enter_payment')

def process_default(request,loan,stat,amount):
    shortfall = loan.repayment_amount - amount

    default_interest = shortfall * settings.DEFAULT_INTEREST_RATE
    user = loan.owner
    date = stat.date
    arrears = loan.total_arrears
    balance = loan.total_outstanding

    #complete loan
    closing_balance = balance - settings.LOAN_COMPLETION_BALANCE
    if closing_balance < amount:
        completion_response = complete_loan(request, loan)
        if completion_response == 1:
            stat.type="COMPLETE PAYMENT"
            stat.save()
            messages.success(request, 'Loan completed.', extra_tags='info')
            return redirect('staff_dashboard')

    #save part payment statement
    stat.arrears = arrears + shortfall
    stat.balance = balance - amount
    stat.type = 'PAYMENT'
    stat.save()

    if loan.default_interest_receivable > 0:

        principal_repayment_percentage = (loan.principal_loan_receivable / loan.total_outstanding)
        interest_repayment_percentage = (loan.ordinary_interest_receivable / loan.total_outstanding)
        default_repayment_percentage = (loan.default_interest_receivable / loan.total_outstanding)
        
        principal_repayment = amount * principal_repayment_percentage
        interest_repayment = amount * interest_repayment_percentage
        default_repayment = amount * default_repayment_percentage
        
        loan.principal_loan_receivable -= principal_repayment
        loan.ordinary_interest_receivable -= interest_repayment
        loan.default_interest_receivable -= default_repayment
        
        loan.principal_loan_paid += principal_repayment
        loan.interest_paid += interest_repayment
        loan.total_default_interest_repaid += default_repayment
        loan.save()

        stat.principal_collected = principal_repayment
        stat.interest_collected = interest_repayment
        stat.default_interest_collected = default_repayment
        stat.save()

    else:
        principal_repayment_percentage = (loan.principal_loan_receivable / loan.total_outstanding)
        interest_repayment_percentage = (loan.ordinary_interest_receivable / loan.total_outstanding)
        
        principal_repayment = amount * principal_repayment_percentage
        interest_repayment = amount * interest_repayment_percentage
        
        loan.principal_loan_receivable -= principal_repayment
        loan.ordinary_interest_receivable -= interest_repayment

        loan.principal_loan_paid += principal_repayment
        loan.interest_paid += interest_repayment
        loan.save()

        stat.principal_collected = principal_repayment
        stat.interest_collected = interest_repayment
        stat.save()

    loan.last_repayment_amount = amount
    loan.last_repayment_date = date
    loan.number_of_repayments += 1
    loan.total_paid += amount
    loan.total_outstanding = balance - amount + default_interest
    loan.total_arrears += shortfall
    loan.default_interest_receivable += default_interest
    loan.last_default_date = date

    # Get the list of repayment dates
    date = datetime.datetime(date.year, date.month, date.day)
    repayment_dates = loan.get_repayment_dates()
    if date >= datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d'):
        repayment_dates.pop(0)
        loan.set_repayment_dates(repayment_dates)
        loan.save()
    print(f'DEFAULT: NEXT REPAYMENT DATE IS: {repayment_dates[0]}')
    loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
    loan.save()

    loan.last_default_amount = shortfall
    loan.number_of_defaults += 1
    loan.default_interest_receivable += default_interest
    loan.save()

    default_int_stat = Statement.objects.create(owner=user, type="DEFAULT", loanref=loan, date=date, credit=default_interest, statement="Default Interest",  uid=user.uid, luid=settings.LUID)
    default_int_stat.arrears = stat.arrears
    default_int_stat.balance = stat.balance + default_interest

    default_int_stat.default_amount = shortfall
    default_int_stat.default_interest = default_interest
    default_int_stat.dcc = 'DEFAULTED'
    default_int_stat.save()

    loan.status = 'DEFAULTED'
    loan.save()

    #send email to customer
    subject=f'Payment updated for Loan - {loan.ref}'
    message = f'Thank you for the Payment of K{round(amount,2)}.'
    message_details = f'Total Outstanding Balance: K{round(loan.total_outstanding, 2)}<br>\
                        Total Arrears: K{round(loan.total_arrears, 2)}<br>\
                        <p style="color: red;">Loan classified as DEFAULT</p>.'
    status = send_email(user, sub=subject, gr=f'Hi {user.first_name}', msg=message, msg_details=message_details, cta='no', btn_lab='View Statement', b_link=f'{settings.DOMAIN}/loan/mystatements/', msgid=None, attachcheck='no', path='')
    if status == 1:
        messages.error(request, 'AMOUNT IS LESS THAN REPAYMENT AMOUNT, so loan classified as default with default interest added and user notified', extra_tags='warning')
    else:
        messages.error(request, 'Payment advise email not sent.', extra_tags='warning')
    
    return redirect('staff_enter_payment')
    
def update_defaults(request):
    loans = Loan.objects.filter(status='RUNNING').filter(status='DEFAULT').exclude(status='COMPLETED').exclude(funded_category='COMPLETED')
    today = datetime.datetime.now()
    date_with_allowance = today + datetime.timedelta(days=settings.DEFAULT_INTEREST_CALCULATION_MERCY_DAYS)

    for loan in loans:
        repayment_dates = loan.get_repayment_dates()
        while datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d') < date_with_allowance:

            missed_date = datetime.datetime.strptime(repayment_dates[0],'%Y-%m-%d')
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

            rounded_default_interest = round(loan.default_interest_receivable,2)
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
                'domain': settings.DOMAIN,
            })
            
            #recipients
            email_list_one = [user.email,]
            email_list_two = settings.RECOVERY_EMAILS
            email_list_three = settings.NOTIFICATION_EMAILS
            email_list  = email_list_one + email_list_two + email_list_three

            text_content = strip_tags(email_content)
            email = EmailMultiAlternatives(subject,text_content,sender,email_list)
            email.attach_alternative(email_content, "text/html")
            
            try: 
                email.send()
            except:
                pass
            messages.success(request, f'Default for {loan.ref} for {missed_date.date()} updated.', extra_tags='info')
        
    return redirect('staff_dashboard')

