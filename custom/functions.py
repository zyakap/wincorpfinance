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
from .models import LoanHoliday
from admin1.models import AdminSettings, Location
from accounts.models import User, UserProfile, StaffProfile
from message.models import Message, MessageLog
from loan.models import Loan, LoanFile, Statement, Payment
from loan.forms import PaymentForm

from accounts.functions import loanfileuploader

#EMAIL SETTINGS
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.html import strip_tags
#admin sender email
from admin1.models import AdminSettings
sender = settings.DEFAULT_SENDER_EMAIL

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

from accounts.functions import check_staff, admin_check, login_check

# id_generator
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

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
    email_list_one = [userprofile.email, 'dev@webmasta.com.pg']
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

def fn_limits(num_fns):
    fns_range = range(settings.MIN_FN, settings.MAX_FN + 1)
    if num_fns in fns_range:
        return 1
    else:
        return 0



#trupngfinance_combination_check
def combination_check(amount, num_fns):
    max_fortnights = {
        1000: 10,
        1200: 10,
        1400: 10,
        1600: 15,
        1800: 15,
        2000: 20,
        2200: 20,
        2400: 20,
        2600: 22,
        2800: 22,
        3000: 24,
        3200: 24,
        3400: 24,
        3600: 24,
        3800: 24,
        4000: 26,
        4200: 26,
        4400: 26,
        4600: 26,
        4800: 26,
        5000: 26,
        7000: 26,
    }

    max_fn = max_fortnights.get(amount)
    print(f'MAX FN FUNCTION: {max_fn}')
    if max_fn is not None and num_fns not in range(3, max_fn + 1):
        return max_fn
    else:
        return 0

#trupngfinance_repayment   
def repayment(amount, type, fns):

    """Calculate the interest on a loan
    Args:
        amount (float): The amount of the loan
        rate (float): The interest rate per period of the loan in decimal form 
        fns (int): The number of fortnights in the loan term
    Returns:
        pmt (float): The payment for a loan based on constant payments and a constant interest rate
    """
    # Fixed interest rate employs the PMT function in Excel to calculate the interest
    #PMT, one of the financial functions, calculates the payment for a loan based on constant payments and a constant interest rate.
    amount = Decimal(amount)
    fns = Decimal(fns)

    if fns == 1.0 or fns == 2.0:
        interest = amount * settings.INTEREST1
    elif  fns == 3.0 or fns == 4.0:
        interest = amount * settings.INTEREST2
    elif fns > 4.0:
        interest = amount * settings.INTEREST3

    pmt = (interest + amount)/fns
    pmt = float(pmt)
    return pmt

#trupngfinance_existing_payments
def upload_existing_statement(request, statementexceldata):
    dbframe = statementexceldata
    statements = []
    payments = []
    date_columns = dbframe.columns[2:]
    print(f'PRINTING DATE COLUMNS: {date_columns}')

    for _, row in dbframe.iterrows():
        name = row[0]
        print(f'PRINTING NAME: {name}')
        loan_ref = row[1]
        print(f'PRINTING LOAN REF: {loan_ref}')
        
        # Skip if name or loan_ref is NaN
        if pd.isna(name) or pd.isna(loan_ref):
            continue

        date_count = 0
        for date_col in date_columns:
            date_value = row[date_col]
            date_count += 1
            if not pd.isna(date_value) and date_value != 0:
                date_value = Decimal(date_value)
                # Create a new statement entry
                loan = Loan.objects.get(ref=loan_ref)
                loan.total_paid += date_value
                loan.fortnights_paid += 1
                loan.number_of_repayments += 1
                last_repayment_amount = date_value
                last_repayment_date = date_col
                loan.total_outstanding -= date_value
                loan.save()
                s_count = loan.number_of_repayments + loan.number_of_defaults + 1
                s_ref = f'{loan_ref}SP{s_count}'
                s_uid = loan.uid
                s_luid = loan.luid

                statements.append(Statement(
                    ref = s_ref,
                    uid = s_uid,
                    luid = s_luid,
                    owner=loan.owner,  # Set this appropriately
                    loanref=Loan.objects.get(ref=loan_ref),
                    date=date_col,
                    type='PAYMENT',
                    s_count = s_count,
                    statement=f'Payroll Deduction - {date_count}',
                    debit=date_value,
                    credit=0,
                    arrears=0,
                    balance=loan.total_outstanding
                ))

                payments.append(Payment(
                    owner=loan.owner,
                    ref = f'{loan_ref}P{loan.number_of_repayments + 1}',
                    loanref=Loan.objects.get(ref=loan_ref),
                    p_count=loan.number_of_repayments + 1,
                    date=date_col,
                    amount=date_value,
                    type='NORMAL PAYMENT',
                    mode = 'PAYROLL DEDUCTION',
                    statement = f'Payroll Deduction - {date_count}',
                    officer = loan.officer
                ))

    # Bulk create all statements
    Statement.objects.bulk_create(statements)
    Payment.objects.bulk_create(payments)
    messages.success(request, f"Processed {len(statements)} statements and payments.")
    
    return redirect('staff_dashboard')


#trupngfinance
def upload_existing_loans(request, loanexceldata):

    dbframe = loanexceldata
    count_loans = 0
    count_sent=0
    not_sent =0
    for dbframe in dbframe.itertuples():
        
        existing_code = dbframe.code
        first_name = dbframe.first_name
        middle_name = dbframe.middle_name
        last_name = dbframe.last_name
        
        email_address = dbframe.email #not used now
        phone_number = dbframe.phone #not used now
        gender = dbframe.sex
        sector = dbframe.sector
        employer = dbframe.employer
        locationid = dbframe.locationid
        residential_address = dbframe.address
        residential_province = dbframe.province
        officerid = dbframe.relationContactID
        relation_contact_name = dbframe.relationContact #not used now
        personal_interest_rate = dbframe.personal_interest_rate #not used now
        loan_amount = dbframe.loan_amount
        term_fns = dbframe.term_fns
        repayment_amount = dbframe.repayment_amount #not used now
        funding_date = dbframe.funding_date #not used now
        start_deduction_date = dbframe.start_deduction_date  #not used now
        end_deduction_date = dbframe.end_deduction_date #not used now

        PrincipalLoanReceipted = dbframe.PrincipalLoanReceipted
        InterestEarnedReceipted = dbframe.InterestEarnedReceipted
        DefaultInterestReceipted = dbframe.DefaultInterestReceipted

        DefaultInterestReceivableAmount = dbframe.DefaultInterestReceivableAmount
        OrdinaryInterestReceivableAmount = dbframe.OrdinaryInterestReceivableAmount
        PrincipalLoanReceivableAmount = dbframe.PrincipalLoanReceivableAmount
        TotalReceivableAmount = dbframe.TotalReceivableAmount

        turnover_days = dbframe.turnover_days
        aging_category = dbframe.aging_category
        aging_amount = dbframe.aging_amount
        recovery = dbframe.recovery #for user_profile #in_recovery check
        funded_category = dbframe.funded_category
        BoardDecision = dbframe.BoardDecision
        considered_unrecoverable = dbframe.considered_unrecoverable
        YearofBadDebt = dbframe.YearofBadDebt
        days_in_default = dbframe.days_in_default
        interest_c_unrecoverable = dbframe.interest_unrecoverable
        principal_c_unrecoverable = dbframe.principal_unrecoverable
        default_flagged_name = dbframe.Ddefault_Customers
            

        # pre functions
        
        officer_pk = int(officerid)
        officer_profile = StaffProfile.objects.get(pk=officer_pk)
        location_id = int(locationid)

        location = Location.objects.get(pk=location_id)

        if funded_category == 'ACTIVE':
            status = 'RUNNING'
        else:
            status = 'DEFAULTED'
        
        if YearofBadDebt != 'none':
            loannotes = f'Board Decision: {BoardDecision}, Year of Debt - {YearofBadDebt}'
        else:
            loannotes = f'{BoardDecision}'

        as_of_date = datetime.datetime(2024, 9, 29) #company fortnight
        funding_date = datetime.datetime(2024, 9, 29)
        #tc_agreement_timestamp =  datetime.datetime(2024, 6, 5)

        if sector == 'PUBLIC':
            next_payment_date = funding_date + datetime.timedelta(days=3)
        #elif 'SOE'???
        else:
            next_payment_date = funding_date + datetime.timedelta(days=10)
        
        number_of_fortnights = int(term_fns)

        #repayment_Dates
        fourteendays = datetime.timedelta(days=14)
        repayment_start_date = next_payment_date
        
        next_next = next_payment_date + fourteendays
        today = datetime.datetime.now().date()

        if today < repayment_start_date.date():
            first_repayment_date = repayment_start_date
        elif repayment_start_date.date() < today < next_payment_date.date():
            first_repayment_date =  next_payment_date
        elif next_payment_date.date() < today < next_next.date():
            first_repayment_date = next_next
        else:
            first_repayment_date = next_next + fourteendays
        
        first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

        repayment_dates_list = [first_repayment_date_str]
        last_date = first_repayment_date
        fns = number_of_fortnights
        while fns > 1:
            new_date = last_date + fourteendays
            new_date_str = new_date.strftime('%Y-%m-%d')
            repayment_dates_list.append(new_date_str)
            last_date = new_date
            fns -= 1
        # Serialize the list to a JSON string
        #loan.set_repayment_dates(repayment_dates_list)
        
        

        #preprocessing of excel data done here
        #next step is to check if loan and user records exist, update if existing
        #if not create new user and loan records

        try:
            user_profile = UserProfile.objects.get(first_name=first_name, last_name=last_name)
            messages.success(request, f'Member Profile for {user_profile.first_name} {user_profile.last_name} exists!')
        except:
            #creating the user and userprofile
            randomid = id_generator(3).lower()
            random_num = random.randint(1000,9999)
            random_email = f'{first_name[0]}{last_name[0]}{random_num}'.lower()
            password = f'{random_email}{randomid}'
            if email_address == 'none':
                email = f'{random_email}@{settings.DOMAIN_DNS}'
            else:
                email = email_address
            user = User.objects.create_user(email=email, is_active=True, is_confirmed=True, password=password)
            user.active=True
            user.confirmed=True
            user.save()

            if middle_name == 'none':
                user_profile = UserProfile.objects.create(user=user, first_name=first_name, last_name=last_name, activation=1, gender=gender, 
                                                        email=email, employer=employer, sector=sector, location=location, 
                                                        residential_address=residential_address, residential_province=residential_province, credit_consent='YES',
                                                        terms_consent='YES',number_of_loans=1, repayment_limit=1000.00,has_loan=1,
                                                        in_recovery=int(recovery),default_flagged=int(recovery),has_arrears=int(recovery))
                messages.success(request, f'Member Profile for {user_profile.first_name} {user_profile.last_name} created successfully!')
            else:
                user_profile = UserProfile.objects.create(user=user, first_name=first_name, middle_name=middle_name, last_name=last_name, activation=1, gender=gender, 
                                                        email=email, employer=employer, sector=sector, location=location, 
                                                        residential_address=residential_address, residential_province=residential_province, credit_consent='YES',
                                                        terms_consent='YES',number_of_loans=1, repayment_limit=1000.00,has_loan=1,
                                                        in_recovery=int(recovery),default_flagged=int(recovery),has_arrears=int(recovery))
                messages.success(request, f'Member Profile for {user_profile.first_name} {user_profile.last_name} created successfully!')
 
            try:
                prefix = AdminSettings.objects.get(name='settings1').loanref_prefix
            except:
                prefix = settings.PREFIX
            
            user_profile.uid = f'{prefix}{random_num}'
            user_profile.modeofregistration =  'PU'
            user_profile.luid = settings.LUID
            if email_address == 'none':
                user_profile.opt1 = 'none'
                user_profile.save()
            else:
                user_profile.opt1 = email_address
                user_profile.opt2 = password
                user_profile.save()

                #Send new user welcome email
                email_subject=f'Welcome to TruPNG Finance - ONLINE'
            
                # HTML EMAIL
                email_content = render_to_string("custom/email_temp_general.html", {
                    'subject': email_subject,
                    'greeting': f'Hi {user_profile.first_name},',
                    'cta': 'yes',
                    'cta_btn1_label': 'LOGIN',
                    'cta_btn1_link': f'https://trupngfinance.com.pg/accounts/login_user/',
                    'message': f'We are please to inform you that we have transitioned online.',
                    'message_details': f'All our services are now online. You can login to view your statement or apply for a new loan or enquire using our support ticket system.<br><br>Your login details are:<br><br>User: {email_address}<br>Password: {user_profile.opt2}',
                    'user': request.user,
                    'userprofile': user_profile,
                
                    'domain': settings.DOMAIN,
                    
                })

                #########  SENDING EMAIL  #########
                #reply to email
                reply_to_email = 'admin@trupngfinance.com'
                sender = f'TruPNG Finance <admin@trupngfinance.com.pg>'
                cc_list = settings.CC_EMAILS
                bcc_list = settings.BCC_EMAILS
                email_list  = ['zyakap@webmasta.com.pg','admin@trupngfinance.com.pg',]
                
                text_content = strip_tags(email_content)
                email = EmailMultiAlternatives(email_subject,text_content,sender,email_list, cc=cc_list, bcc=bcc_list, reply_to=[reply_to_email])
                email.attach_alternative(email_content, "text/html")

                #attach invoice
                # Attach the generated PDF
                #email.attach(file_name, pdf, 'application/pdf')
                #email.send()
                try:
                    email.send()
                    count_sent += 1 
                    user_profile.opt3 = 'sent'
                    user_profile.save()
                    messages.success(request, f'Email sent to {email_address}')
                except:
                    not_sent += 1
                    user_profile.opt3 = 'not sent'
                    user_profile.save()
                    messages.error(request, f'Email not sent to {email_address}')
                
            user_profile.save()

        #update the user profile
        user_profile.first_name = first_name
        user_profile.last_name = last_name
        if middle_name != 'none':
            user_profile.middle_name = middle_name
        else:
            user_profile.middle_name = None

        user_profile.email = email_address
        user_profile.phone = phone_number
        user_profile.gender = gender 
        user_profile.employer = employer
        user_profile.sector = sector
        user_profile.location = location
        user_profile.residential_address = residential_address
        user_profile.residential_province = residential_province

        if default_flagged_name == 'excl director':
            user_profile.default_flagged = 0
            user_profile.has_arrears = 0
            user_profile.in_recovery = 0
            user_profile.dcc_flagged = 0
            user_profile.dcc = default_flagged_name
        if default_flagged_name != 'none':
            user_profile.default_flagged = 1
            user_profile.has_arrears = 1
            user_profile.in_recovery = 1
            user_profile.dcc_flagged = 1
            user_profile.dcc = default_flagged_name
        
        
        try:
            MessageLog.objects.create(user=user)
        except:
            pass
        
        #check if loan
        try:
            loan = Loan.objects.get(owner=user_profile, existing_code=existing_code)
        except:
            #Create the Loan
            #Pre functions for loan
            #repayment_amount = Decimal(400.00)
            repayment_start_date = next_payment_date
            expected_end_date = next_payment_date + datetime.timedelta(days=(14*(number_of_fortnights-1)))
            
            print(type(PrincipalLoanReceivableAmount))
            loan_principal= Decimal(PrincipalLoanReceivableAmount)
            ordinary_interest = Decimal(OrdinaryInterestReceivableAmount)
            default_interests= Decimal(DefaultInterestReceivableAmount)
            total_receivable = Decimal(TotalReceivableAmount)

            total_loan_amount = loan_principal + ordinary_interest

            loan_principal_repaid = Decimal(PrincipalLoanReceipted)
            interest_paid = Decimal(InterestEarnedReceipted)
            default_interest_paid = Decimal(DefaultInterestReceipted)
            total_paid = loan_principal_repaid + interest_paid + default_interest_paid

            turnover = int(turnover_days)
            total_aging_amount = Decimal(aging_amount)
            unrecoverable = Decimal(considered_unrecoverable)

            #Create Loan
            loanref_prefix = settings.PREFIX
            upid = user_profile.id
            first_name = user_profile.first_name
            last_name = user_profile.last_name
            rand = random.randint(0,9)
            refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
            #set repayment limit
            user_profile.activation = 1
            user_profile.repayment_limit = Decimal(repayment_amount)+ Decimal(100.0)
            user_profile.save()
            
            loan = Loan.objects.create(ref=refx, existing_code=existing_code, owner=user_profile, officer=officer_profile, location=location, 
                                    application_date=as_of_date, amount=loan_principal, interest=ordinary_interest, total_loan_amount=total_loan_amount,
                                    number_of_fortnights=number_of_fortnights,repayment_amount=repayment_amount,category="FUNDED",funded_category=funded_category, status=status,
                                    tc_agreement="YES", tc_agreement_timestamp=as_of_date, funding_date=funding_date,repayment_start_date=repayment_start_date,
                                    expected_end_date=expected_end_date, next_payment_date=next_payment_date,
                                    principal_loan_paid=loan_principal_repaid, interest_paid=interest_paid, default_interest_paid=default_interest_paid,
                                    total_paid=total_paid, principal_loan_receivable=loan_principal, ordinary_interest_receivable=ordinary_interest,
                                    default_interest_receivable=default_interests, total_outstanding=total_receivable,turnover_days=turnover, aging_category=aging_category,
                                    aging_amount=total_aging_amount, considered_unrecoverable=unrecoverable,notes=loannotes)

            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.uid = user_profile.uid
            loan.luid = settings.LUID
            loan.save()

            loanfile = LoanFile.objects.create(loan=loan)
            loanfile.save()

            #create the loan statement
            Statement.objects.create(owner=user_profile, ref = f'{final_ref}F', loanref = loan, 
                                                type="OTHER", statement="Loan Created", credit=loan.amount, 
                                                balance=loan.total_outstanding, date=funding_date)
            
                
        #update the loan

        loan.loan_amount = loan_amount
        loan.number_of_fortnights = number_of_fortnights
        loan.repayment_amount = repayment_amount
        loan.funding_date = funding_date
        loan.funded_category = funded_category
        loan.repayment_start_date = repayment_start_date
        loan.expected_end_date = repayment_start_date + datetime.timedelta(days=(14*(number_of_fortnights-1)))
        
        # Serialize the list to a JSON string
        loan.set_repayment_dates(repayment_dates_list)

        loan.next_payment_date = next_payment_date
        loan.principal_loan_paid = PrincipalLoanReceipted
        loan.interest_paid = InterestEarnedReceipted
        loan.default_interest_paid = DefaultInterestReceipted
        loan.default_interest_receivable = DefaultInterestReceivableAmount
        loan.ordinary_interest_receivable = OrdinaryInterestReceivableAmount
        loan.principal_loan_receivable = PrincipalLoanReceivableAmount
        loan.total_outstanding = TotalReceivableAmount
        loan.turnover_days = turnover_days
        loan.aging_category = aging_category
        loan.aging_amount = aging_amount
        loan.in_recovery = int(recovery)
        loan.default_flagged = int(recovery)
        loan.has_arrears = int(recovery)
        loan.notes = loannotes
        loan.considered_unrecoverable = considered_unrecoverable
        loan.interest_c_unrecoverable = interest_c_unrecoverable
        loan.principal_c_unrecoverable = principal_c_unrecoverable

        if default_flagged_name == 'excl director':
            loan.in_recovery = 0
            loan.default_flagged = 0
            loan.has_arrears = 0
            loan.days_in_default = 0
            loan.total_arrears = 0
        else:
            loan.in_recovery = int(recovery)
            loan.default_flagged = int(recovery)
            loan.has_arrears = int(recovery)
            loan.days_in_default = days_in_default
            loan.total_arrears = aging_amount
        
        loan.save()

        count_loans += 1
        print(f'Count Loans:{count_loans}')
        print(f'COUNT SENT: {count_sent}')
        print(f'NOT SENT: {not_sent}')
        #if count_loans == 10:
        # break
    messages.success(request, f'{count_loans} loans uploaded or updated successfully.')

    return redirect('userloans_all')


#NEW #trupngfinance FUNCTIONS FOR UPLOADING LOANS FROM EXCEL

#trupngfinance
def create_new_loan_from_upload(request, loanexceldata):
    dbframe = loanexceldata
    count_loans = 0
    
    for dbframe in dbframe.itertuples():
        
        transaction_date = dbframe.TransactionDate
        description = dbframe.Description
        amount = dbframe.Amount
        name = dbframe.Client
        employer = dbframe.Company
        percent_interest = dbframe.Rate
        fns = dbframe.Fortnights
        sector = dbframe.Sector
        #notes = dbframe.Notes
        
        #preformat the data to be inserted into the database
        amount = Decimal(amount)
        percent_interest = Decimal(percent_interest)
        fns = int(fns)
        #transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d').date

        #check if customer exists
        #split the name first into first name and last name 
        first_name = name.split()[0]
        if len(name.split()) == 3:
            middle_name = name.split()[1]
            last_name = name.split()[2]
        else:
            last_name = name.split()[1]
            middle_name = None
        
        try:
            user_profile = UserProfile.objects.get(first_name=first_name, last_name=last_name)
            messages.success(request, f'Customer {first_name} {last_name} exists!', extra_tags='info')
        except:
            #creating the user and userprofile
            randomid = id_generator(3).lower()
            random_num = random.randint(1000,9999)
            random_email = f'{first_name[0]}{last_name[0]}{random_num}'.lower()
            password = f'{random_email}{randomid}'

            email = f'{random_email}@{settings.DOMAIN_DNS}'
            email_address = email
            user = User.objects.create_user(email=email, is_active=True, is_confirmed=True, password=password)
            user.active=True
            user.confirmed=True
            user.save()

            location = Location.objects.get(pk=1)

           
            user_profile = UserProfile.objects.create(user=user, first_name=first_name,middle_name=middle_name, last_name=last_name, activation=1,
                                               email=email, employer=employer, sector=sector, location=location, 
                                                        credit_consent='YES',terms_consent='YES',number_of_loans=1, repayment_limit=1000.00,has_loan=1)
            messages.success(request, f'Member Profile for {user_profile.first_name} {user_profile.last_name} created successfully!')
            
 
            try:
                prefix = AdminSettings.objects.get(name='settings1').loanref_prefix
            except:
                prefix = settings.PREFIX
            
            user_profile.uid = f'{prefix}{random_num}'
            user_profile.modeofregistration =  'PU'
            user_profile.luid = settings.LUID
            
            user_profile.opt1 = email_address
            user_profile.opt2 = password
            #set repayment limit
            user_profile.activation = 1
            user_profile.repayment_limit = Decimal(1000.0)

            user_profile.save()

        try:
            loan = Loan.objects.get(owner=user_profile, category='FUNDED')
            messages.success(request, f'Loan for {user_profile.first_name} {user_profile.last_name} exists!', extra_tags='info')

            #pre functions
            number_of_fortnights = fns
            loan_principal = amount
            ordinary_interest = amount * percent_interest
            total_loan_amount = loan_principal + ordinary_interest
            repayment_amount = total_loan_amount / number_of_fortnights
            transaction_date = transaction_date

            #2-oct-govt fortnight
            sector = user_profile.sector
            if sector == 'PUBLIC':
                first_pay_period_date = datetime.datetime(2024, 12, 11)
                next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
                next_next_pay_date = next_pay_date + datetime.timedelta(days=14)  
            else:
                first_pay_period_date = datetime.datetime(2024, 12, 4)
                next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
                next_next_pay_date = next_pay_date + datetime.timedelta(days=14)
            
            if transaction_date < first_pay_period_date:
                start_of_repayment = first_pay_period_date
            elif first_pay_period_date < transaction_date < next_pay_date:
                start_of_repayment = next_pay_date
            elif next_pay_date < transaction_date < next_next_pay_date:
                start_of_repayment = next_next_pay_date
            
            repayment_start_date = start_of_repayment
            expected_end_date = start_of_repayment + datetime.timedelta(days=(14*(number_of_fortnights-1)))
            next_payment_date = start_of_repayment
            funding_date = transaction_date
            loan.save()

            #set repayment dates
            first_repayment_date = loan.repayment_start_date
            first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

            repayment_dates_list = [first_repayment_date_str]
            last_date = first_repayment_date
            fns = number_of_fortnights
            fourteendays = datetime.timedelta(days=14)
            while fns > 1:
                new_date = last_date + fourteendays
                new_date_str = new_date.strftime('%Y-%m-%d')
                repayment_dates_list.append(new_date_str)
                last_date = new_date
                fns -= 1
            # Serialize the list to a JSON string
            loan.set_repayment_dates(repayment_dates_list)
            loan.save()
            
            #update the loan
            loan.application_date = transaction_date
            loan.amount += loan_principal
            loan.interest += ordinary_interest
            loan.total_loan_amount += total_loan_amount
            loan.number_of_fortnights = number_of_fortnights
            loan.repayment_amount = repayment_amount
            loan.funding_date = transaction_date
            loan.repayment_start_date = first_repayment_date
            loan.expected_end_date = first_repayment_date + datetime.timedelta(days=(14*(number_of_fortnights-1)))
            loan.next_payment_date = next_payment_date
            loan.principal_loan_receivable += loan_principal
            loan.ordinary_interest_receivable += ordinary_interest
            loan.total_outstanding += total_loan_amount
            #loan.notes = notes
            loan.save()

            date_of_statement = transaction_date
            #create the loan statement
            Statement.objects.create(
                owner=user_profile, 
                ref = f'{loan.ref}AL',
                loanref = loan,
                type="CREDIT",
                statement=f'Additional Loan', 
                credit=total_loan_amount,                           
                balance=loan.total_outstanding, 
                date=date_of_statement
                )

            #existing_loans_counter += 1
            #print(existing_loans_counter)
            messages.success(request, f'{loan.owner.first_name } {loan.owner.last_name}\'s Loan {loan.ref} has been added', extra_tags='info')
        
        except:
            #create the loan
            loanref_prefix = settings.PREFIX
            upid = user_profile.id
            first_name = user_profile.first_name
            last_name = user_profile.last_name
            rand = random.randint(0,9)
            refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
            
            officer_profile = StaffProfile.objects.get(pk=1)
            location = Location.objects.get(pk=1)

            #pre functions
            number_of_fortnights = int(fns)
            loan_principal = amount
            ordinary_interest = amount * percent_interest
            total_loan_amount = loan_principal + ordinary_interest
            repayment_amount = total_loan_amount / number_of_fortnights

            #2-oct-govt fortnight
            sector = user_profile.sector
            if sector == 'PUBLIC':
                first_pay_period_date = datetime.datetime(2024, 12, 11)
                next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
                next_next_pay_date = next_pay_date + datetime.timedelta(days=14)  
            else:
                first_pay_period_date = datetime.datetime(2024, 12, 4)
                next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
                next_next_pay_date = next_pay_date + datetime.timedelta(days=14)
            
            if transaction_date < first_pay_period_date:
                start_of_repayment = first_pay_period_date
            elif first_pay_period_date < transaction_date < next_pay_date:
                start_of_repayment = next_pay_date
            elif next_pay_date < transaction_date < next_next_pay_date:
                start_of_repayment = next_next_pay_date
            
            repayment_start_date = start_of_repayment
            expected_end_date = start_of_repayment + datetime.timedelta(days=(14*(number_of_fortnights-1)))
            next_payment_date = start_of_repayment
            funding_date = transaction_date

            loan = Loan.objects.create(
                ref=refx, 
                owner=user_profile, 
                officer=officer_profile, 
                location=location,
                amount=loan_principal, 
                interest=ordinary_interest, 
                total_loan_amount=total_loan_amount,
                number_of_fortnights=number_of_fortnights,
                repayment_amount=repayment_amount,
                category="FUNDED",
                funded_category='ACTIVE', 
                status='RUNNING',
                tc_agreement="YES", 
                tc_agreement_timestamp=transaction_date, 
                funding_date=funding_date,
                repayment_start_date=repayment_start_date,
                expected_end_date=expected_end_date, 
                next_payment_date=next_payment_date,
                principal_loan_receivable=loan_principal, 
                ordinary_interest_receivable=ordinary_interest,
                total_outstanding=total_loan_amount,
                notes=description)

            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.uid = user_profile.uid
            loan.luid = settings.LUID
            loan.save()

            #set repayment dates
            first_repayment_date = loan.repayment_start_date
            first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

            repayment_dates_list = [first_repayment_date_str]
            last_date = first_repayment_date
            fns = number_of_fortnights
            fourteendays = datetime.timedelta(days=14)
            while fns > 1:
                new_date = last_date + fourteendays
                new_date_str = new_date.strftime('%Y-%m-%d')
                repayment_dates_list.append(new_date_str)
                last_date = new_date
                fns -= 1
            # Serialize the list to a JSON string
            loan.set_repayment_dates(repayment_dates_list)
            loan.save()

            loanfile = LoanFile.objects.create(loan=loan)
            loanfile.save()

            #create the loan statement
            Statement.objects.create(owner=user_profile, 
            ref = f'{final_ref}F', loanref = loan, 
                type="OTHER", 
                statement="Loan Created", 
                credit=loan.amount,                           
                balance=loan.total_outstanding, date=funding_date)
            
            messages.success(request, f'Loan for {user_profile.first_name} {user_profile.last_name} created successfully!')
        
    return redirect('admin_dashboard')
    
#trupngfinance
def direct_loan_update_function(request, loanexceldata):

    dbframe = loanexceldata
    count_loans = 0
    count_sent=0
    not_sent =0
    for dbframe in dbframe.itertuples():
        
        userprofileID = dbframe.userprofileID
        userprofileID_int = int(userprofileID)

        existing_code = dbframe.code
        first_name = dbframe.first_name
        middle_name = dbframe.middle_name
        last_name = dbframe.last_name
        
        email_address = dbframe.email #not used now
        phone_number = dbframe.phone #not used now
        gender = dbframe.sex
        sector = dbframe.sector
        employer = dbframe.employer
        locationid = dbframe.locationid
        residential_address = dbframe.address
        residential_province = dbframe.province
        officerid = dbframe.relationContactID
        relation_contact_name = dbframe.relationContact #not used now
        personal_interest_rate = dbframe.personal_interest_rate #not used now
        loan_amount = dbframe.loan_amount
        term_fns = dbframe.term_fns
        repayment_amount = dbframe.repayment_amount #not used now
        funding_date = dbframe.funding_date #not used now
        start_deduction_date = dbframe.start_deduction_date  #not used now
        end_deduction_date = dbframe.end_deduction_date #not used now

        PrincipalLoanReceipted = dbframe.PrincipalLoanReceipted
        InterestEarnedReceipted = dbframe.InterestEarnedReceipted
        DefaultInterestReceipted = dbframe.DefaultInterestReceipted

        DefaultInterestReceivableAmount = dbframe.DefaultInterestReceivableAmount
        OrdinaryInterestReceivableAmount = dbframe.OrdinaryInterestReceivableAmount
        PrincipalLoanReceivableAmount = dbframe.PrincipalLoanReceivableAmount
        TotalReceivableAmount = dbframe.TotalReceivableAmount

        turnover_days = dbframe.turnover_days
        aging_category = dbframe.aging_category
        aging_amount = dbframe.aging_amount
        recovery = dbframe.recovery #for user_profile #in_recovery check
        funded_category = dbframe.funded_category
        BoardDecision = dbframe.BoardDecision
        considered_unrecoverable = dbframe.considered_unrecoverable
        YearofBadDebt = dbframe.YearofBadDebt
        days_in_default = dbframe.days_in_default
        interest_c_unrecoverable = dbframe.interest_unrecoverable
        principal_c_unrecoverable = dbframe.principal_unrecoverable
        default_flagged_name = dbframe.Ddefault_Customers
            

        # pre functions
        
        officer_pk = int(officerid)
        officer_profile = StaffProfile.objects.get(pk=officer_pk)
        location_id = int(locationid)

        location = Location.objects.get(pk=location_id)

        if funded_category == 'ACTIVE':
            status = 'RUNNING'
        else:
            status = 'DEFAULTED'
        
        if YearofBadDebt != 'none':
            loannotes = f'Board Decision: {BoardDecision}, Year of Debt - {YearofBadDebt}'
        else:
            loannotes = f'{BoardDecision}'

        as_of_date = datetime.datetime(2024, 9, 29) #company fortnight
        funding_date = datetime.datetime(2024, 9, 29)
        #tc_agreement_timestamp =  datetime.datetime(2024, 6, 5)

        if sector == 'PUBLIC':
            next_payment_date = funding_date + datetime.timedelta(days=3)
        #elif 'SOE'???
        else:
            next_payment_date = funding_date + datetime.timedelta(days=10)
        
        number_of_fortnights = int(term_fns)

        #repayment_Dates
        fourteendays = datetime.timedelta(days=14)
        repayment_start_date = next_payment_date
        
        next_next = next_payment_date + fourteendays
        today = datetime.datetime.now().date()

        if today < repayment_start_date.date():
            first_repayment_date = repayment_start_date
        elif repayment_start_date.date() < today < next_payment_date.date():
            first_repayment_date =  next_payment_date
        elif next_payment_date.date() < today < next_next.date():
            first_repayment_date = next_next
        else:
            first_repayment_date = next_next + fourteendays
        
        first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

        repayment_dates_list = [first_repayment_date_str]
        last_date = first_repayment_date
        fns = number_of_fortnights
        while fns > 1:
            new_date = last_date + fourteendays
            new_date_str = new_date.strftime('%Y-%m-%d')
            repayment_dates_list.append(new_date_str)
            last_date = new_date
            fns -= 1
        
        

        #preprocessing of excel data done here
        #next step is to check if loan and user records exist, update if existing
        #if not create new user and loan records

        try:
            user_profile = UserProfile.objects.get(id=userprofileID_int)
            messages.success(request, f'Member Profile for {user_profile.first_name} {user_profile.last_name} exists!')
        except:
            #creating the user and userprofile
            messages.error(request, f'Member Profile for {user_profile.first_name} {user_profile.last_name} does not exist!')
            return redirect('userloans_all')

        #update the user profile
        user_profile.first_name = first_name
        user_profile.last_name = last_name
        if middle_name != 'none':
            user_profile.middle_name = middle_name
        else:
            user_profile.middle_name = None

        user_profile.email = email_address
        user_profile.phone = phone_number
        user_profile.gender = gender 
        user_profile.employer = employer
        user_profile.sector = sector
        user_profile.location = location
        user_profile.residential_address = residential_address
        user_profile.residential_province = residential_province

        if default_flagged_name == 'excl director':
            user_profile.default_flagged = 0
            user_profile.has_arrears = 0
            user_profile.in_recovery = 0
            user_profile.dcc_flagged = 0
            user_profile.dcc = default_flagged_name
        if default_flagged_name != 'none':
            user_profile.default_flagged = 1
            user_profile.has_arrears = 1
            user_profile.in_recovery = 1
            user_profile.dcc_flagged = 1
            user_profile.dcc = default_flagged_name
        
        
        try:
            MessageLog.objects.create(user=user)
        except:
            pass
        
        #check if loan
        try:
            loan = Loan.objects.get(owner=user_profile, existing_code=existing_code)
        except:
            #Create the Loan
            #Pre functions for loan
            #repayment_amount = Decimal(400.00)
            repayment_start_date = next_payment_date
            expected_end_date = next_payment_date + datetime.timedelta(days=(14*(number_of_fortnights-1)))
            
            print(type(PrincipalLoanReceivableAmount))
            loan_principal= Decimal(PrincipalLoanReceivableAmount)
            ordinary_interest = Decimal(OrdinaryInterestReceivableAmount)
            default_interests= Decimal(DefaultInterestReceivableAmount)
            total_receivable = Decimal(TotalReceivableAmount)

            total_loan_amount = loan_principal + ordinary_interest

            loan_principal_repaid = Decimal(PrincipalLoanReceipted)
            interest_paid = Decimal(InterestEarnedReceipted)
            default_interest_paid = Decimal(DefaultInterestReceipted)
            total_paid = loan_principal_repaid + interest_paid + default_interest_paid

            turnover = int(turnover_days)
            total_aging_amount = Decimal(aging_amount)
            unrecoverable = Decimal(considered_unrecoverable)

            #Create Loan
            loanref_prefix = settings.PREFIX
            upid = user_profile.id
            first_name = user_profile.first_name
            last_name = user_profile.last_name
            rand = random.randint(0,9)
            refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
            #set repayment limit
            user_profile.activation = 1
            user_profile.repayment_limit = Decimal(repayment_amount)+ Decimal(100.0)
            user_profile.save()
            
            loan = Loan.objects.create(ref=refx, existing_code=existing_code, owner=user_profile, officer=officer_profile, location=location, 
                                    application_date=as_of_date, amount=loan_principal, interest=ordinary_interest, total_loan_amount=total_loan_amount,
                                    number_of_fortnights=number_of_fortnights,repayment_amount=repayment_amount,category="FUNDED",funded_category=funded_category, status=status,
                                    tc_agreement="YES", tc_agreement_timestamp=as_of_date, funding_date=funding_date,repayment_start_date=repayment_start_date,
                                    expected_end_date=expected_end_date, next_payment_date=next_payment_date,
                                    principal_loan_paid=loan_principal_repaid, interest_paid=interest_paid, default_interest_paid=default_interest_paid,
                                    total_paid=total_paid, principal_loan_receivable=loan_principal, ordinary_interest_receivable=ordinary_interest,
                                    default_interest_receivable=default_interests, total_outstanding=total_receivable,turnover_days=turnover, aging_category=aging_category,
                                    aging_amount=total_aging_amount, considered_unrecoverable=unrecoverable,notes=loannotes)

            loan_id = loan.id
            str_loan_id = str(loan_id)
            finalref_first_part = refx[:-1]
            final_ref = f'{finalref_first_part}{str_loan_id}'
            loan.ref = final_ref
            loan.uid = user_profile.uid
            loan.luid = settings.LUID
            loan.save()

            loanfile = LoanFile.objects.create(loan=loan)
            loanfile.save()

            #create the loan statement
            Statement.objects.create(owner=user_profile, ref = f'{final_ref}F', loanref = loan, 
                                                type="OTHER", statement="Loan Created", credit=loan.amount, 
                                                balance=loan.total_outstanding, date=funding_date)
            
                
        #update the loan

        loan.loan_amount = loan_amount
        loan.number_of_fortnights = number_of_fortnights
        loan.repayment_amount = repayment_amount
        loan.funding_date = funding_date
        loan.funded_category = funded_category
        loan.repayment_start_date = repayment_start_date
        loan.expected_end_date = repayment_start_date + datetime.timedelta(days=(14*(number_of_fortnights-1)))
        
        # Serialize the list to a JSON string
        loan.set_repayment_dates(repayment_dates_list)

        loan.next_payment_date = next_payment_date
        loan.principal_loan_paid = PrincipalLoanReceipted
        loan.interest_paid = InterestEarnedReceipted
        loan.default_interest_paid = DefaultInterestReceipted
        loan.default_interest_receivable = DefaultInterestReceivableAmount
        loan.ordinary_interest_receivable = OrdinaryInterestReceivableAmount
        loan.principal_loan_receivable = PrincipalLoanReceivableAmount
        loan.total_outstanding = TotalReceivableAmount
        loan.turnover_days = turnover_days
        loan.aging_category = aging_category
        loan.aging_amount = aging_amount
        loan.in_recovery = int(recovery)
        loan.default_flagged = int(recovery)
        loan.has_arrears = int(recovery)
        loan.notes = loannotes
        loan.considered_unrecoverable = considered_unrecoverable
        loan.interest_c_unrecoverable = interest_c_unrecoverable
        loan.principal_c_unrecoverable = principal_c_unrecoverable

        if default_flagged_name == 'excl director':
            loan.in_recovery = 0
            loan.default_flagged = 0
            loan.has_arrears = 0
            loan.days_in_default = 0
            loan.total_arrears = 0
        else:
            loan.in_recovery = int(recovery)
            loan.default_flagged = int(recovery)
            loan.has_arrears = int(recovery)
            loan.days_in_default = days_in_default
            loan.total_arrears = aging_amount
        
        loan.save()

        count_loans += 1
        print(f'Count Loans:{count_loans}')
        print(f'COUNT SENT: {count_sent}')
        print(f'NOT SENT: {not_sent}')
        #if count_loans == 10:
        # break
    messages.success(request, f'{count_loans} loans uploaded or updated successfully.')

    return redirect('userloans_all')    

#trupngfinance upload payment
def upload_payments_function(request,loanexceldata):

    dbframe = loanexceldata
    payment_count_loop = 0
    for dbframe in dbframe.itertuples():
        
        transaction_date = dbframe.TransactionDate
        payment_statement = dbframe.Description
        amount = dbframe.Amount
        name = dbframe.Client
        mode_of_payment = dbframe.Mode
        
        amount = Decimal(amount)
        
        #split the name first into first name and last name 
        first_name = name.split()[0]
        if len(name.split()) == 3:
            middle_name = name.split()[1]
            last_name = name.split()[2]
        else:
            last_name = name.split()[1]
            middle_name = None
        
        try:
            user_profile = UserProfile.objects.get(first_name=first_name, last_name=last_name)
        except:
            messages.error(request,f'{name} - No such person exists.', extra_tags='danger')
            continue
        
        loans = Loan.objects.filter(owner=user_profile, funded_category='ACTIVE').order_by('id')
        #if loans.count() > 1:
        #    messages.error(request, f'{name} has more than one running loan', extra_tags='info')
        #    continue
        if loans.count() == 0:
            messages.error(request, f'{name} has no running loan', extra_tags='info')
            continue
        else:
            loan = loans[0]

        #repayment_Dates is a list of dates when the loan was repaid
        repayment_dates = loan.get_repayment_dates()
        if not loan.repayment_dates:
            messages.error(request, f'{name} has no repayment dates', extra_tags='info')
            continue

        old_next_repayment_date = repayment_dates[0]
        repayment_dates.pop(0)
        if len(repayment_dates) != 0:
            loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
        else:
            if loan.total_outstanding > 0:
                messages.error(request, f'That was the last date for loan of {name} so we added a new date', extra_tags='danger')
                loan.next_payment_date = datetime.datetime.strptime(old_next_repayment_date, '%Y-%m-%d') + datetime.timedelta(days=14)
                loan.save()
                repayment_dates.append(loan.next_payment_date.strftime('%Y-%m-%d'))
                #save the repayment dates in the database
                loan.set_repayment_dates(repayment_dates)
                loan.save()
            else:
                loan.next_payment_date = None
                messages.error(request, f'That was the last date for loan of {name}', extra_tags='danger')
                messages.error(request, f'{name} has no outstanding balance', extra_tags='info')
                continue
        
        
        #save the repayment dates in the database
        loan.set_repayment_dates(repayment_dates)
        loan.save()

        #PREUPDATE THE LOAN
        loan.status = 'RUNNING'
        loan.funded_category = 'ACTIVE'
        percentage_of_principal = loan.principal_loan_receivable/loan.total_outstanding
        percentage_of_interest = loan.ordinary_interest_receivable/loan.total_outstanding
        percentage_of_default_interest = loan.default_interest_receivable/loan.total_outstanding

        principal_component = percentage_of_principal*amount
        interest_component = percentage_of_interest*amount
        default_interest_component = percentage_of_default_interest*amount
         
        loan.principal_loan_paid = principal_component
        loan.interest_paid = interest_component
        loan.default_interest_paid = default_interest_component
        loan.total_paid += amount
        loan.fortnights_paid += 1
        loan.number_of_repayments += 1
        loan.last_repayment_amount = amount
        loan.last_repayment_date = transaction_date
        loan.days_in_default = 0
        loan.principal_loan_receivable = loan.principal_loan_receivable - principal_component
        loan.ordinary_interest_receivable = loan.ordinary_interest_receivable - interest_component
        loan.default_interest_receivable = loan.default_interest_receivable - default_interest_component
        loan.total_outstanding -= amount
        loan.turnover_days = 0
        loan.aging_category = '30LESS'
        loan.aging_amount = 0
        loan.save()

        #STATEMENT cREATION

        #create the loan statement
        statement = Statement.objects.create(
            owner=user_profile, 
            ref = f'{loan.ref}S', 
            loanref = loan, 
            type="PAYMENT", 
            statement=payment_statement, 
            debit=amount,                           
            balance=loan.total_outstanding, 
            date=transaction_date)

        statement.save()
        statement.uid = loan.uid
        statement.luid = loan.luid
        statement.s_count = Statement.objects.filter(owner=user_profile).count() + 1
        statement.ref = f'{loan.ref}S{statement.s_count}'
        statement.principal_collected = principal_component
        statement.interest_collected = interest_component
        statement.default_interest_collected = default_interest_component
        statement.save()

        #PAYMENT CREATION
        payment_count = Payment.objects.filter(owner=user_profile).count() + 1

        payment = Payment.objects.create(
        ref = f'{loan.ref}P{payment_count}', 
        owner = user_profile,
        loanref = loan,
        p_count = payment_count,
        date = transaction_date,
        amount = amount,
        type = 'NORMAL REPAYMENT',
        mode = mode_of_payment,
        statement = payment_statement,
        officer = loan.officer
        )
        payment.save()
        payment_count_loop += 1

        messages.success(request, f'{name}\'s payment uploaded successfully.')
        
    messages.success(request, f'{payment_count_loop} payments uploaded successfully.')
    return redirect('admin_dashboard')

def set_repayment_dates(request):
    loans = Loan.objects.filter(funded_category='ACTIVE', funding_date__gte='2024-10-01').order_by('id')

    for loan in loans:
        
        #set repayment dates
        first_repayment_date = loan.repayment_start_date
        first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')
        fourteendays = datetime.timedelta(days=14)
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
        loan.save()
        print(f'{loan.owner.first_name } {loan.owner.last_name}\'s Loan {loan.ref} has been updated')
        messages.success(request, f'{loan.owner.first_name } {loan.owner.last_name}\'s Loan {loan.ref} has been updated')

    return redirect('userloans_all')

from django.db.models import Q
def add_2_set_repayment_dates(request):
    #loans = Loan.objects.filter(Q(funded_category='ACTIVE') | Q(funded_category='RECOVERY'), updated_at__gte='2024-11-30').order_by('id')[:3]
    #
    loans = Loan.objects.filter(funded_category='ACTIVE', updated_at__gte='2024-11-30').order_by('id')

    for loan in loans:

        # Get the list of repayment dates
        #date = datetime.datetime(date.year, date.month, date.day)
        repayment_dates = loan.get_repayment_dates()
        
        #delete the first element in the list 
        #loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
        if len(repayment_dates) == 0:
            if loan.total_outstanding > 0:
                messages.error(request, f'{loan.owner.first_name } {loan.owner.last_name}\'s Loan {loan.ref} has no repayment dates')
                next_payment_date = loan.next_payment_date
                past_14_days = next_payment_date - datetime.timedelta(days=14)
                repayment_dates.insert(0, next_payment_date.strftime('%Y-%m-%d'))
                repayment_dates.insert(0, past_14_days.strftime('%Y-%m-%d'))
                loan.set_repayment_dates(repayment_dates)
                loan.save()
                messages.error(request, f'{loan.owner.first_name } {loan.owner.last_name}\'s Loan {loan.ref} has been updated with two dates', extra_tags='info')
                
            else:
                messages.error(request, f'{loan.owner.first_name } {loan.owner.last_name}\'s Loan {loan.ref} has no repayment dates. Their loan is complete', extra_tags='dark')
                loan.funded_category = 'COMPLETED'
                loan.save()
                continue

        next_repayment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')

        fourteendays = datetime.timedelta(days=14)
        payment_14_past = next_repayment_date - fourteendays
        payment_28_past = payment_14_past - fourteendays

        repayment_dates.insert(0, payment_14_past.strftime('%Y-%m-%d'))
        repayment_dates.insert(0, payment_28_past.strftime('%Y-%m-%d'))
        
        loan.set_repayment_dates(repayment_dates)
        loan.save()
        
        messages.success(request, f'New: {loan.repayment_dates}')
        print(f'New: {loan.repayment_dates}')
                                                                                
        #messages.success(request, f'{loan.owner.first_name } {loan.owner.last_name}\'s Loan {loan.ref} has been updated')
    return redirect('admin_dashboard')

def classify_loan_complete(request):
    loans = Loan.objects.filter(funded_category__isnull=False).order_by('id')
    count_of_update = 0
    for loan in loans:
        if loan.total_outstanding == 0:
            loan.funded_category = 'COMPLETED'
            loan.status = 'COMPLETED'
            loan.save()
            count_of_update += 1
    messages.success(request, f'{count_of_update} loans have been classified as completed')
    return redirect('admin_dashboard')
    
def generate_password_logins(request):
    users = User.objects.filter(is_superuser=False)
    for user in users:
        user.set_password('password123')
        user.save()
    messages.success(request, 'Password reset for all users')

def consolidate_loans(request):
    
    #all loans belonging to one person is added to have only one loan in the system
    user_profiles = UserProfile.objects.all()
    for user_profile in user_profiles:
        loans = Loan.objects.filter(owner=user_profile).exclude(funded_category='COMPLETED').order_by('id')
        first_name = user_profile.first_name
        last_name = user_profile.last_name
        if loans.count() <= 1:
            messages.error(request, f'{first_name} {last_name} has one or no loan', extra_tags='warning')
            continue
        #create the consolidated loan
        loanref_prefix = settings.PREFIX
        upid = user_profile.id
        7
        rand = random.randint(0,9)
        refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
        
        officer_profile = StaffProfile.objects.get(pk=1)
        location = Location.objects.get(pk=1)

        #pre functions
        number_of_fortnights = 10
        loan_principal = 0
        ordinary_interest = 0
        total_loan_amount = 0
        repayment_amount = 0

        transaction_date = datetime.datetime(2024, 12, 16)
        description = 'Consolidated Loan'

        #2-oct-govt fortnight
        sector = user_profile.sector
        if sector == 'PUBLIC':
            first_pay_period_date = datetime.datetime(2024, 12, 18)
            next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
            next_next_pay_date = next_pay_date + datetime.timedelta(days=14)  
        else:
            first_pay_period_date = datetime.datetime(2024, 12, 25)
            next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
            next_next_pay_date = next_pay_date + datetime.timedelta(days=14)
        
        if transaction_date < first_pay_period_date:
            start_of_repayment = first_pay_period_date
        elif first_pay_period_date < transaction_date < next_pay_date:
            start_of_repayment = next_pay_date
        elif next_pay_date < transaction_date < next_next_pay_date:
            start_of_repayment = next_next_pay_date
        
        repayment_start_date = start_of_repayment
        expected_end_date = start_of_repayment + datetime.timedelta(days=(14*(number_of_fortnights-1)))
        next_payment_date = start_of_repayment
        funding_date = transaction_date

        loan = Loan.objects.create(
            ref=refx, 
            owner=user_profile, 
            officer=officer_profile, 
            location=location,
            amount=loan_principal, 
            interest=ordinary_interest, 
            total_loan_amount=total_loan_amount,
            number_of_fortnights=number_of_fortnights,
            repayment_amount=repayment_amount,
            category="FUNDED",
            funded_category='ACTIVE', 
            status='RUNNING',
            tc_agreement="YES", 
            tc_agreement_timestamp=transaction_date, 
            funding_date=funding_date,
            repayment_start_date=repayment_start_date,
            expected_end_date=expected_end_date, 
            next_payment_date=next_payment_date,
            principal_loan_receivable=loan_principal, 
            ordinary_interest_receivable=ordinary_interest,
            total_outstanding=total_loan_amount,
            considered_unrecoverable=0,
            principal_c_unrecoverable=0,
            interest_c_unrecoverable=0,
            total_arrears=0,
            days_in_default=0,
            last_repayment_amount=0,
            
            number_of_advance_payments=0,
            
            last_advance_payment_amount=0,
            total_advance_payment=0,
            advance_payment_surplus=0,
            number_of_defaults=0,
            
            last_default_amount=0,
            total_paid=0,
            principal_loan_paid=0,
            interest_paid=0,
            default_interest_paid=0,
            fortnights_paid=0,
            number_of_repayments=0,
            notes=description)
        
        loan.save()

        loan_id = loan.id
        str_loan_id = str(loan_id)
        finalref_first_part = refx[:-1]
        final_ref = f'{finalref_first_part}{str_loan_id}C'
        loan.ref = final_ref
        loan.uid = user_profile.uid
        loan.luid = settings.LUID
        loan.save()

        #set repayment dates
        first_repayment_date = loan.repayment_start_date
        first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

        repayment_dates_list = [first_repayment_date_str]
        last_date = first_repayment_date
        fns = number_of_fortnights
        fourteendays = datetime.timedelta(days=14)
        while fns > 1:
            new_date = last_date + fourteendays
            new_date_str = new_date.strftime('%Y-%m-%d')
            repayment_dates_list.append(new_date_str)
            last_date = new_date
            fns -= 1
        # Serialize the list to a JSON string
        loan.set_repayment_dates(repayment_dates_list)
        loan.save()

        loanfile = LoanFile.objects.create(loan=loan)
        loanfile.save()
        existing_loans_counter = 0
        allloans = loans.exclude(pk=loan.id)
        for existing_loan in allloans:
            #update the loan

            loan.uid = user_profile.uid
            loan.luid = settings.LUID
            loan.existing_code = existing_loan.existing_code
            loan.owner = user_profile
            loan.officer = existing_loan.officer
            loan.location = existing_loan.location
            loan.loan_type = existing_loan.loan_type
            loan.classification = existing_loan.classification
            loan.application_date = existing_loan.application_date
            loan.amount += existing_loan.amount
            #loan.processing_fee += existing_loan.processing_fee
            loan.interest += existing_loan.interest
            loan.total_loan_amount += existing_loan.total_loan_amount
            loan.repayment_frequency = existing_loan.repayment_frequency
            loan.number_of_fortnights = existing_loan.number_of_fortnights
            loan.repayment_amount = existing_loan.repayment_amount
            loan.category = existing_loan.category
            loan.funded_category = existing_loan.funded_category
            loan.status = existing_loan.status
            loan.tc_agreement = existing_loan.tc_agreement
            loan.tc_agreement_timestamp = existing_loan.tc_agreement_timestamp
            loan.funding_date = existing_loan.funding_date
            loan.repayment_start_date = existing_loan.repayment_start_date
            loan.expected_end_date = existing_loan.expected_end_date
            loan.repayment_dates = existing_loan.repayment_dates
            loan.next_payment_date = existing_loan.next_payment_date
            loan.principal_loan_receivable += existing_loan.principal_loan_receivable
            loan.ordinary_interest_receivable += existing_loan.ordinary_interest_receivable
            loan.default_interest_receivable += existing_loan.default_interest_receivable
            loan.total_outstanding += existing_loan.total_outstanding
            loan.turnover_days = existing_loan.turnover_days
            loan.aging_category = existing_loan.aging_category
            loan.aging_amount = existing_loan.aging_amount
            #loan.in_recovery = existing_loan.in_recovery
            #loan.default_flagged = existing_loan.default_flagged
            #loan.has_arrears = existing_loan.has_arrears
            print(type(existing_loan.considered_unrecoverable))
            loan.considered_unrecoverable += existing_loan.considered_unrecoverable
            loan.principal_c_unrecoverable += existing_loan.principal_c_unrecoverable
            loan.interest_c_unrecoverable += existing_loan.interest_c_unrecoverable
            loan.recovery_date = existing_loan.recovery_date
            loan.notes = existing_loan.notes
            loan.opt1 = existing_loan.opt1
            loan.opt2 = existing_loan.opt2
            loan.opt3 = existing_loan.opt3
            loan.opt4 = existing_loan.opt4
            loan.opt5 = existing_loan.opt5
            loan.dcc = existing_loan.dcc
            loan.total_arrears += existing_loan.total_arrears
            loan.days_in_default += existing_loan.days_in_default
            loan.last_repayment_amount += existing_loan.last_repayment_amount
            loan.last_repayment_date = existing_loan.last_repayment_date
            loan.number_of_advance_payments += existing_loan.number_of_advance_payments
            loan.last_advance_payment_date = existing_loan.last_advance_payment_date
            loan.last_advance_payment_amount = existing_loan.last_advance_payment_amount
            loan.total_advance_payment += existing_loan.total_advance_payment
            loan.advance_payment_surplus += existing_loan.advance_payment_surplus
            loan.number_of_defaults += existing_loan.number_of_defaults
            loan.last_default_date = existing_loan.last_default_date
            loan.last_default_amount = existing_loan.last_default_amount
            loan.total_paid += existing_loan.total_paid
            loan.principal_loan_paid += existing_loan.principal_loan_paid
            loan.interest_paid += existing_loan.interest_paid
            loan.default_interest_paid += existing_loan.default_interest_paid
            loan.fortnights_paid += existing_loan.fortnights_paid
            loan.number_of_repayments += existing_loan.number_of_repayments
            loan.save()

            if existing_loan.funding_date:
                date_of_statement = existing_loan.funding_date
            else:
                date_of_statement = transaction_date

            #create the loan statement
            Statement.objects.create(
                owner=user_profile, 
                ref = f'{existing_loan.ref}C',
                loanref = loan, 
                type="OTHER", 
                statement=f'LOAN - {existing_loan.ref } - CONSOLIDATED', 
                credit=existing_loan.total_outstanding,                           
                balance=loan.total_outstanding, 
                date=date_of_statement
                )

            existing_loanfile = LoanFile.objects.get(loan=existing_loan)

            loanfile.application_form_url = existing_loanfile.application_form_url
            loanfile.terms_conditions_url = existing_loanfile.terms_conditions_url
            loanfile.stat_dec_url = existing_loanfile.stat_dec_url
            loanfile.irr_sd_form_url = existing_loanfile.irr_sd_form_url
            loanfile.work_confirmation_letter_url = existing_loanfile.work_confirmation_letter_url
            loanfile.payslip1_url = existing_loanfile.payslip1_url
            loanfile.payslip2_url = existing_loanfile.payslip2_url
            loanfile.loan_statement1_url = existing_loanfile.loan_statement1_url
            loanfile.loan_statement2_url = existing_loanfile.loan_statement2_url
            loanfile.loan_statement3_url = existing_loanfile.loan_statement3_url
            loanfile.bank_statement_url = existing_loanfile.bank_statement_url
            loanfile.super_statement_url = existing_loanfile.super_statement_url
            loanfile.bank_standing_order_url = existing_loanfile.bank_standing_order_url
            loanfile.funding_receipt_url = existing_loanfile.funding_receipt_url
            loanfile.save()
            existing_loans_counter += 1
            print(existing_loans_counter)

            existing_loanfile.delete()
            existing_loan.delete()
            
            messages.success(request, f'{existing_loan.owner.first_name } {existing_loan.owner.last_name}\'s Loan {existing_loan.ref} has been consolidated', extra_tags='info')
        
        messages.success(request, f'{existing_loan.owner.first_name } {existing_loan.owner.last_name}\'s Loans {existing_loan.ref} has been consolidated', extra_tags='info')

    return redirect('admin_dashboard')
            
def targeted_consolidate_loans(request, first_name_part, last_name_part):
    first_name_part = first_name_part
    last_name_part = last_name_part
    #all loans belonging to one person is added to have only one loan in the system
    user_profiles = UserProfile.objects.filter(first_name__icontains=first_name_part, last_name__icontains=last_name_part)
    all_loans = []
    for user_profile in user_profiles:
        loans = Loan.objects.filter(owner=user_profile).filter(category='FUNDED').exclude(funded_category='COMPLETED').order_by('id')
        for loan in loans:
            all_loans.append(loan)
    
    

    if len(all_loans) <= 1:
        messages.error(request, f'{first_name} {last_name} has one or no loan', extra_tags='warning')
        return redirect('admin_dashboard')

    user_profile = user_profiles[0]

    first_name = user_profile.first_name
    last_name = user_profile.last_name
    
    #create the consolidated loan
    loanref_prefix = settings.PREFIX
    upid = user_profile.id
    
    rand = random.randint(0,9)
    refx = f'{loanref_prefix}{upid}{first_name[0]}{last_name[0]}{rand}'
    
    officer_profile = StaffProfile.objects.get(pk=1)
    location = Location.objects.get(pk=1)

    #pre functions
    number_of_fortnights = 10
    loan_principal = 0
    ordinary_interest = 0
    total_loan_amount = 0
    repayment_amount = 0

    transaction_date = datetime.datetime(2024, 12, 16)
    description = 'Consolidated Loan'

    #2-oct-govt fortnight
    sector = user_profile.sector
    if sector == 'PUBLIC':
        first_pay_period_date = datetime.datetime(2024, 12, 18)
        next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
        next_next_pay_date = next_pay_date + datetime.timedelta(days=14)  
    else:
        first_pay_period_date = datetime.datetime(2024, 12, 25)
        next_pay_date = first_pay_period_date + datetime.timedelta(days=14)
        next_next_pay_date = next_pay_date + datetime.timedelta(days=14)
    
    if transaction_date < first_pay_period_date:
        start_of_repayment = first_pay_period_date
    elif first_pay_period_date < transaction_date < next_pay_date:
        start_of_repayment = next_pay_date
    elif next_pay_date < transaction_date < next_next_pay_date:
        start_of_repayment = next_next_pay_date
    
    repayment_start_date = start_of_repayment
    expected_end_date = start_of_repayment + datetime.timedelta(days=(14*(number_of_fortnights-1)))
    next_payment_date = start_of_repayment
    funding_date = transaction_date

    loan = Loan.objects.create(
        ref=refx, 
        owner=user_profile, 
        officer=officer_profile, 
        location=location,
        amount=loan_principal, 
        interest=ordinary_interest, 
        total_loan_amount=total_loan_amount,
        number_of_fortnights=number_of_fortnights,
        repayment_amount=repayment_amount,
        category="FUNDED",
        funded_category='ACTIVE', 
        status='RUNNING',
        tc_agreement="YES", 
        tc_agreement_timestamp=transaction_date, 
        funding_date=funding_date,
        repayment_start_date=repayment_start_date,
        expected_end_date=expected_end_date, 
        next_payment_date=next_payment_date,
        principal_loan_receivable=loan_principal, 
        ordinary_interest_receivable=ordinary_interest,
        total_outstanding=total_loan_amount,
        considered_unrecoverable=0,
        principal_c_unrecoverable=0,
        interest_c_unrecoverable=0,
        total_arrears=0,
        days_in_default=0,
        last_repayment_amount=0,
        
        number_of_advance_payments=0,
        
        last_advance_payment_amount=0,
        total_advance_payment=0,
        advance_payment_surplus=0,
        number_of_defaults=0,
        
        last_default_amount=0,
        total_paid=0,
        principal_loan_paid=0,
        interest_paid=0,
        default_interest_paid=0,
        fortnights_paid=0,
        number_of_repayments=0,
        notes=description)
    
    loan.save()

    loan_id = loan.id
    str_loan_id = str(loan_id)
    finalref_first_part = refx[:-1]
    final_ref = f'{finalref_first_part}{str_loan_id}C'
    loan.ref = final_ref
    loan.uid = user_profile.uid
    loan.luid = settings.LUID
    loan.save()

    #set repayment dates
    first_repayment_date = loan.repayment_start_date
    first_repayment_date_str = first_repayment_date.strftime('%Y-%m-%d')

    repayment_dates_list = [first_repayment_date_str]
    last_date = first_repayment_date
    fns = number_of_fortnights
    fourteendays = datetime.timedelta(days=14)
    while fns > 1:
        new_date = last_date + fourteendays
        new_date_str = new_date.strftime('%Y-%m-%d')
        repayment_dates_list.append(new_date_str)
        last_date = new_date
        fns -= 1
    # Serialize the list to a JSON string
    loan.set_repayment_dates(repayment_dates_list)
    loan.save()

    loanfile = LoanFile.objects.create(loan=loan)
    loanfile.save()
    existing_loans_counter = 0
    #allloans = loans.exclude(pk=loan.id)
    for existing_loan in all_loans:
        #update the loan

        loan.uid = user_profile.uid
        loan.luid = settings.LUID
        loan.existing_code = existing_loan.existing_code
        loan.owner = user_profile
        loan.officer = existing_loan.officer
        loan.location = existing_loan.location
        loan.loan_type = existing_loan.loan_type
        loan.classification = existing_loan.classification
        loan.application_date = existing_loan.application_date
        loan.amount += existing_loan.amount
        #loan.processing_fee += existing_loan.processing_fee
        loan.interest += existing_loan.interest
        loan.total_loan_amount += existing_loan.total_loan_amount
        loan.repayment_frequency = existing_loan.repayment_frequency
        loan.number_of_fortnights = existing_loan.number_of_fortnights
        loan.repayment_amount = existing_loan.repayment_amount
        loan.category = existing_loan.category
        loan.funded_category = existing_loan.funded_category
        loan.status = existing_loan.status
        loan.tc_agreement = existing_loan.tc_agreement
        loan.tc_agreement_timestamp = existing_loan.tc_agreement_timestamp
        loan.funding_date = existing_loan.funding_date
        loan.repayment_start_date = existing_loan.repayment_start_date
        loan.expected_end_date = existing_loan.expected_end_date
        loan.repayment_dates = existing_loan.repayment_dates
        loan.next_payment_date = existing_loan.next_payment_date
        loan.principal_loan_receivable += existing_loan.principal_loan_receivable
        loan.ordinary_interest_receivable += existing_loan.ordinary_interest_receivable
        loan.default_interest_receivable += existing_loan.default_interest_receivable
        loan.total_outstanding += existing_loan.total_outstanding
        loan.turnover_days = existing_loan.turnover_days
        loan.aging_category = existing_loan.aging_category
        loan.aging_amount = existing_loan.aging_amount
        #loan.in_recovery = existing_loan.in_recovery
        #loan.default_flagged = existing_loan.default_flagged
        #loan.has_arrears = existing_loan.has_arrears
        print(type(existing_loan.considered_unrecoverable))
        loan.considered_unrecoverable += existing_loan.considered_unrecoverable
        loan.principal_c_unrecoverable += existing_loan.principal_c_unrecoverable
        loan.interest_c_unrecoverable += existing_loan.interest_c_unrecoverable
        loan.recovery_date = existing_loan.recovery_date
        loan.notes = existing_loan.notes
        loan.opt1 = existing_loan.opt1
        loan.opt2 = existing_loan.opt2
        loan.opt3 = existing_loan.opt3
        loan.opt4 = existing_loan.opt4
        loan.opt5 = existing_loan.opt5
        loan.dcc = existing_loan.dcc
        loan.total_arrears += existing_loan.total_arrears
        loan.days_in_default += existing_loan.days_in_default
        loan.last_repayment_amount += existing_loan.last_repayment_amount
        loan.last_repayment_date = existing_loan.last_repayment_date
        loan.number_of_advance_payments += existing_loan.number_of_advance_payments
        loan.last_advance_payment_date = existing_loan.last_advance_payment_date
        loan.last_advance_payment_amount = existing_loan.last_advance_payment_amount
        loan.total_advance_payment += existing_loan.total_advance_payment
        loan.advance_payment_surplus += existing_loan.advance_payment_surplus
        loan.number_of_defaults += existing_loan.number_of_defaults
        loan.last_default_date = existing_loan.last_default_date
        loan.last_default_amount = existing_loan.last_default_amount
        loan.total_paid += existing_loan.total_paid
        loan.principal_loan_paid += existing_loan.principal_loan_paid
        loan.interest_paid += existing_loan.interest_paid
        loan.default_interest_paid += existing_loan.default_interest_paid
        loan.fortnights_paid += existing_loan.fortnights_paid
        loan.number_of_repayments += existing_loan.number_of_repayments
        loan.save()

        if existing_loan.funding_date:
            date_of_statement = existing_loan.funding_date
        else:
            date_of_statement = transaction_date

        #create the loan statement
        Statement.objects.create(
            owner=user_profile, 
            ref = f'{existing_loan.ref}C',
            loanref = loan, 
            type="OTHER", 
            statement=f'LOAN - {existing_loan.ref } - CONSOLIDATED', 
            credit=existing_loan.total_outstanding,                           
            balance=loan.total_outstanding, 
            date=date_of_statement
            )

        existing_loanfile = LoanFile.objects.get(loan=existing_loan)

        loanfile.application_form_url = existing_loanfile.application_form_url
        loanfile.terms_conditions_url = existing_loanfile.terms_conditions_url
        loanfile.stat_dec_url = existing_loanfile.stat_dec_url
        loanfile.irr_sd_form_url = existing_loanfile.irr_sd_form_url
        loanfile.work_confirmation_letter_url = existing_loanfile.work_confirmation_letter_url
        loanfile.payslip1_url = existing_loanfile.payslip1_url
        loanfile.payslip2_url = existing_loanfile.payslip2_url
        loanfile.loan_statement1_url = existing_loanfile.loan_statement1_url
        loanfile.loan_statement2_url = existing_loanfile.loan_statement2_url
        loanfile.loan_statement3_url = existing_loanfile.loan_statement3_url
        loanfile.bank_statement_url = existing_loanfile.bank_statement_url
        loanfile.super_statement_url = existing_loanfile.super_statement_url
        loanfile.bank_standing_order_url = existing_loanfile.bank_standing_order_url
        loanfile.funding_receipt_url = existing_loanfile.funding_receipt_url
        loanfile.save()
        existing_loans_counter += 1
        print(existing_loans_counter)

        existing_loanfile.delete()
        existing_loan.delete()
        
        messages.success(request, f'{existing_loan.owner.first_name } {existing_loan.owner.last_name}\'s Loan {existing_loan.ref} has been consolidated', extra_tags='info')
    
       
    return redirect('admin_dashboard')
            
      
#def upload_update(request):

#@admin_check
def trupng_approve_loan(request, loan_ref):

    loan = Loan.objects.get(ref=loan_ref)
    loid = loan.owner.id
    user = UserProfile.objects.get(pk=loid)
    user_profile = user
    today = datetime.datetime.now()

    try:
        existing_loan = Loan.objects.get(owner=user, category='FUNDED', funded_category='ACTIVE')
        existing_loan_check = 'YES'
        print("There is an existing loan")
    except:
        existing_loan_check = 'NO'
        print("There is NOOOOO existing loan")
    staff_profile = UserProfile.objects.get(user=request.user)
    staff = StaffProfile.objects.get(user=staff_profile)

    if existing_loan_check == 'NO':

        
        
        startdate = loan.repayment_start_date
        duration_days = loan.number_of_fortnights * 14
        
        expected_end_date = startdate + datetime.timedelta(days=duration_days)
        fourteendays = datetime.timedelta(days=14)
        
        startdate_str = startdate.strftime('%Y-%m-%d')

        repayment_dates_list = [startdate_str]
        last_date = startdate
        fns = loan.number_of_fortnights
        while fns > 1:
            new_date = last_date + fourteendays
            new_date_str = new_date.strftime('%Y-%m-%d')
            repayment_dates_list.append(new_date_str)
            last_date = new_date
            fns -= 1
        # Serialize the list to a JSON string
        loan.set_repayment_dates(repayment_dates_list)
        
        loan.expected_end_date = expected_end_date
        loan.category = "PENDING"
        loan.last_repayment_amount = 0.00
        loan.number_of_repayments = 0
        loan.total_paid = 0
        loan.total_arrears = 0
        loan.advance_payments = 0
        loan.last_default_amount = 0
        loan.number_of_defaults = 0
        loan.default_interest_paid = 0
        loan.total_outstanding = loan.total_loan_amount
        loan.status = 'APPROVED'
        loan.officer = staff

        loan.principal_loan_receivable = loan.amount
        loan.ordinary_interest_receivable = loan.interest
        loan.default_interest_receivable = 0
        loan.total_outstanding = loan.principal_loan_receivable + loan.ordinary_interest_receivable + loan.default_interest_receivable
        loan.save()

        user.has_loan = 1
        user.save()

        subject = f'{loan_ref} is APPROVED'
        ''' if header_cta == 'yes' '''
        cta_label = 'View Loan'
        cta_link = f'{settings.DOMAIN}/loan/myloan/{loan.ref}/'

        greeting = f'Hi {loan.owner.first_name}'
        message = 'Your pending loan has been Approved.'
        message_details = f'Amount: K{round(loan.amount,2)}<br>\
                            Repayment: K{round(loan.repayment_amount,2)}<br>\
                            Repayment Start Date: {startdate}'

        ''' if cta == 'yes' '''
        cta_btn1_label = 'View Loan'
        cta_btn1_link = f'{settings.DOMAIN}/loan/myloan/{loan_ref}/'
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
            'promo': 'yes',
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
        
        text_content = strip_tags(email_content)
        email = EmailMultiAlternatives(subject,text_content,sender,[user.email, 'dev@webmasta.com.pg'])
        email.attach_alternative(email_content, "text/html")

        try: 
            email.send()
            messages.success(request, f'Loan was approved and Approval Email was sent to {loan.owner.first_name} {loan.owner.last_name} successfully.')
        except:
            messages.error(request, 'Loan status is updated as "Approved" and moved to the "Funding List".', extra_tags='info')
            messages.error(request, 'Loan approval notice email was NOT sent, please advise the customer by other means.', extra_tags='danger')
        
        return redirect('pending_loans')
    
    else:
        print(loan)
        print(type(loan))
        
        loan.uid = user_profile.uid
        loan.luid = settings.LUID
        loan.existing_code = existing_loan.existing_code
        loan.owner = user_profile
        loan.officer = staff
        loan.location = existing_loan.location
        loan.loan_type = existing_loan.loan_type
        loan.classification = existing_loan.classification
        loan.application_date = existing_loan.application_date
        
        #loan.processing_fee += existing_loan.processing_fee
        loan.interest += existing_loan.interest
        loan.total_loan_amount += existing_loan.total_loan_amount
       
        loan.principal_loan_receivable += existing_loan.principal_loan_receivable
        loan.ordinary_interest_receivable += existing_loan.ordinary_interest_receivable
        loan.default_interest_receivable += existing_loan.default_interest_receivable
        loan.total_outstanding += existing_loan.total_outstanding

        loan.total_paid += existing_loan.total_paid
        loan.principal_loan_paid += existing_loan.principal_loan_paid
        loan.interest_paid += existing_loan.interest_paid
        loan.default_interest_paid += existing_loan.default_interest_paid
        loan.fortnights_paid += existing_loan.fortnights_paid
        loan.number_of_repayments += existing_loan.number_of_repayments
        loan.save()

        loan.number_of_fortnights += existing_loan.number_of_fortnights
        if loan.number_of_fortnights > 10:
            repayment = loan.total_outstanding/Decimal(10.00)
        else:
            repayment = loan.total_outstanding/Decimal(loan.number_of_fortnights)
        loan.repayment_amount = repayment
        
        loan.save()

        #create the loan statement
        Statement.objects.create(
            owner=user_profile, 
            ref = f'{existing_loan.ref}ADD',
            loanref = loan, 
            type="DEBIT", 
            statement=f'ADDITIONAL LOAN',
            credit=loan.amount,                           
            balance=loan.total_outstanding, 
            date=today
            )

        existing_loan.funded_category = 'COMPLETED'
        existing_loan.status = 'COMPLETED'
        existing_loan.save()
        
        messages.success(request, f'{existing_loan.owner.first_name } {existing_loan.owner.last_name}\'s Loan {existing_loan.ref} has been consolidated', extra_tags='info')

        subject = f'Additional Loan {loan_ref} is APPROVED'
        ''' if header_cta == 'yes' '''
        cta_label = 'View Loan'
        cta_link = f'{settings.DOMAIN}/loan/myloan/{loan.ref}/'

        greeting = f'Hi {loan.owner.first_name}'
        message = 'Your pending loan has been Approved.'
        message_details = f'Amount: K{round(loan.amount,2)}<br>\
                            Repayment: K{round(loan.repayment_amount,2)}<br>\
                            Repayment Start Date: {loan.next_payment_date}'

        ''' if cta == 'yes' '''
        cta_btn1_label = 'View Loan'
        cta_btn1_link = f'{settings.DOMAIN}/loan/myloan/{loan_ref}/'
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
            'promo': 'yes',
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
        
        text_content = strip_tags(email_content)
        email = EmailMultiAlternatives(subject,text_content,sender,[user.email, 'dev@webmasta.com.pg'])
        email.attach_alternative(email_content, "text/html")

        try: 
            email.send()
            messages.success(request, f'Loan was approved and Approval Email was sent to {loan.owner.first_name} {loan.owner.last_name} successfully.')
        except:
            messages.error(request, 'Loan status is updated as "Approved" and moved to the "Funding List".', extra_tags='info')
            messages.error(request, 'Loan approval notice email was NOT sent, please advise the customer by other means.', extra_tags='danger')
        
        return redirect('pending_loans')
    
   #send email to user

def trupng_process_repayment(request,loan,stat,amount):
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
    if date >= datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d'):
        repayment_dates.pop(0)
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
    #status = send_email(user, sub=subject, gr=f'Hi {user.first_name}', msg=message, msg_details=message_details, cta='no', btn_lab='View Statement', b_link=f'{settings.DOMAIN}/loan/mystatements/', msgid=None, attachcheck='no', path='')
    #if status == 1:
    #    messages.success(request, 'Payment registered.', extra_tags='info')
    #else:
    #    messages.error(request, 'Payment advise email not sent.', extra_tags='warning')

    return redirect('staff_enter_payment')


@check_staff
def trupng_payment(request, loan_ref):

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

           
            payment.type = 'NORMAL REPAYMENT'
            payment.save()
            print(f'PAYMENT TYPE: {payment.type}')
            trupng_process_repayment(request, loan, stat, amount)

        else:
            messages.error(request, 'Payment not entered. Please check the form and try again.', extra_tags='danger')
        return redirect('staff_enter_payment')
            
    else:
        form = PaymentForm()        
    
    return render(request, 'payment.html', { 'loan_ref': loan_ref, 'form': form })



@check_staff
def register_loan_holiday(request):
    
    if request.method == 'POST':
        loan_ref = request.POST.get('loan_ref')
        date_for_repayment = request.POST.get('date_for_repayment')
        date_of_payment = request.POST.get('date_of_payment')
        amount = request.POST.get('amount')
        amount = Decimal(amount)
        statement = request.POST.get('statement')

        loan = Loan.objects.get(ref=loan_ref)
        user = loan.owner

        if 'loan_holiday_funding_receipt' in request.FILES:
            print('uploading now')
            loanfileuploader(request,'loan_holiday_funding_receipt', user, loan)

            print('uploaded already')
        print('out of uploader')
        date_of_payment = datetime.datetime.strptime(date_of_payment, '%Y-%m-%d')
        payment_date = date_of_payment.date()

        stat = Statement.objects.create(owner=user, loanref=loan, date=payment_date, 
        credit=amount, statement=statement, uid=user.uid, luid=settings.LUID)
        stat.save()

        stat.s_count += 1
        stat.ref = f'{loan.ref}LH{stat.s_count}'
        stat.balance = loan.total_outstanding
        stat.save()
            
        # Get the list of repayment dates
        date_for_repayment = datetime.datetime.strptime(date_for_repayment, '%Y-%m-%d')
        date = date_for_repayment.date()

        date = datetime.datetime(date.year, date.month, date.day)
        repayment_dates = loan.get_repayment_dates()
        if date >= datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d'):
            repayment_dates.pop(0)
            loan.set_repayment_dates(repayment_dates)
            loan.save()
        print(f'NORMAL: NEXT REPAYMENT DATE IS: {repayment_dates[0]}')
        loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
        loan.save()

        LoanHoliday.objects.create(
            loan=loan,
            date=payment_date,
            amount=amount,
            statement=statement,
        )
        messages.success(request, 'Loan Holiday payment registered and statement created.', extra_tags='info')

        return redirect('custom_functions')
    context = {
        'nav': 'loan_holiday',
    }
    return render(request, 'functions/register_loan_holiday.html', context)


@check_staff
def register_default(request):
    if request.method == 'POST':
        loan = Loan.objects.get(ref=request.POST['loan_ref'])
        date_of_missed_repayment = request.POST['date_of_missed_repayment']
        user = loan.owner

        date_of_missed_repayment = datetime.datetime.strptime(date_of_missed_repayment, '%Y-%m-%d')
        date = date_of_missed_repayment.date()

        # Get the list of repayment dates
        date = datetime.datetime(date.year, date.month, date.day)
        repayment_dates = loan.get_repayment_dates()
        if date >= datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d'):
            repayment_dates.pop(0)
            loan.set_repayment_dates(repayment_dates)
            loan.save()
        print(f'NORMAL: NEXT REPAYMENT DATE IS: {repayment_dates[0]}')
        loan.next_payment_date = datetime.datetime.strptime(repayment_dates[0], '%Y-%m-%d')
        loan.save()

        stat = Statement.objects.create(owner=user, loanref=loan, date=date, 
        statement='LOAN DEFAULTED', uid=user.uid, luid=settings.LUID)
        stat.save()
        
        stat.s_count += 1
        stat.ref = f'{loan.ref}SP{stat.s_count}' 
        stat.balance = loan.total_outstanding
        stat.default_amount = loan.repayment_amount
        
        loan.total_arrears += loan.repayment_amount
        
        loan.save()
        stat.arrears += loan.total_arrears
        stat.save()

        messages.success(request, 'Default registered and statement created.', extra_tags='info')
    
        return redirect('custom_functions')
    
    context = {
        'nav': 'register_default',
        }
    return render(request, 'functions/register_default.html', context)

@check_staff
def register_additional_loan(request):
    if request.method == 'POST':
        loan_ref = request.POST.get('loan_ref')
        date_of_funding = request.POST.get('date_of_funding')
        repayment_start_date = request.POST.get('repayment_start_date')
        no_of_fortnights = request.POST.get('no_of_fortnights')
        interest_rate = request.POST.get('interest_rate')
        amount = request.POST.get('amount')
        description = request.POST.get('statement')
        
        loan = Loan.objects.get(ref=loan_ref)
        user_profile = loan.owner

        date_of_funding = datetime.datetime.strptime(date_of_funding, '%Y-%m-%d')
        funding_date = date_of_funding.date()
        repayment_start_date = datetime.datetime.strptime(repayment_start_date, '%Y-%m-%d')
        start_of_repayment = repayment_start_date.date()
        interest_rate = Decimal(interest_rate)

        number_of_fortnights = int(no_of_fortnights)
        amount = Decimal(amount)

        interest = amount * (interest_rate/Decimal(100.00))
        total_loan_amount = amount + interest
        

        # #create the consolidated loan
        loan.amount += amount
        loan.interest += interest
        loan.total_loan_amount += total_loan_amount
        
        loan.number_of_fortnights = number_of_fortnights
        loan.total_outstanding += total_loan_amount
        loan.principal_loan_receivable += amount
        loan.ordinary_interest_receivable += interest
        loan.repayment_start_date = start_of_repayment
        loan.save()

        new_repayment = loan.total_outstanding / Decimal(number_of_fortnights)
        loan.repayment_amount = new_repayment
        loan.save()

        statement = Statement.objects.create(owner=user_profile, ref=f'{loan_ref}ADDL', 
        loanref=loan, type="OTHER", statement=description, credit=amount, 
        balance=loan.total_outstanding, date=funding_date, 
        uid=user_profile.uid, luid=settings.LUID)
        statement.save()

        #recalculate repayment dates
        fourteendays = datetime.timedelta(days=14)
        repayment_start_date = loan.repayment_start_date
        first_repayment_date = repayment_start_date
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
        loan.funding_date = date_of_funding
        loan.next_payment_date = repayment_start_date
        loan.save()
        
        user = loan.owner
        user.number_of_loans += 1
        user.save()

       
        # Construct the repayment dates HTML string
        repayment_dates_html = ''.join([f'<div>{date}</div>' for date in repayment_dates_list])
        #send email to user
        
        subject = f'ADDITIONAL LOAN INFORMATION'
        ''' if header_cta == 'yes' '''
        cta_label = ''
        cta_link = ''

        greeting = f'Hi {loan.owner.first_name}'
        message = 'Your additional Loan has been funded.'
        message_details = f'Amount: K{round(loan.amount-settings.PROCESSING_FEE,2)}<br>\
                            Processing Fee: K{round(settings.PROCESSING_FEE,2)}<br>\
                            Total Loan: K{round(loan.total_loan_amount,2)}<br>\
                            New Repayment: K{round(loan.repayment_amount,2)}<br>\
                            Repayment Start Date: {loan.next_payment_date}<br>\
                            Your repayment dates are listed here in order for your reference:</br>\
                            {repayment_dates_html}'

        ''' if cta == 'yes' '''
        cta_btn1_label = 'View Loan'
        cta_btn1_link = f'{settings.DOMAIN}/loan/myloan/{loan.ref}/'
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
            'user': user,
            'domain': settings.DOMAIN,
        })
        
        text_content = strip_tags(email_content)
        email = EmailMultiAlternatives(subject,text_content,sender,['admin@trupngfinance.com.pg', user.email ])
        email.attach_alternative(email_content, "text/html")

        #email.send()
        try: 
            email.send()
            messages.success(request, f'Additional Loan information was sent to {loan.owner.first_name} {loan.owner.last_name} successfully.')
        except:
            messages.error(request, 'Loan has been categorized as "FUNDED" and status updated to "RUNNING".', extra_tags='info')
            messages.error(request, 'Loan funding notice was NOT sent, please advise the client by email or phone.".', extra_tags='danger')
        
        return redirect('funding_receipt_upload', loan.ref)

    context = {
        'nav': 'register_additional_loan',
    }

    return render(request, 'functions/register_additional_loan.html', context)

@check_staff
def register_refund_amount(request):
    if request.method == 'POST':
        loan_ref = request.POST.get('loan_ref')
        date_of_funding = request.POST.get('date_of_funding')
        amount = request.POST.get('amount')
        description = request.POST.get('statement')
        add_to_balance = request.POST.get('add_to_balance')
        
        loan = Loan.objects.get(ref=loan_ref)
        user_profile = loan.owner
        amount = Decimal(amount)

        # #create the consolidated loan
        if add_to_balance == 'YES':
            loan.total_outstanding += amount
            loan.save()

        statement = Statement.objects.create(owner=user_profile, ref=f'{loan_ref}RF', 
        loanref=loan, type="OTHER", statement='description', debit=amount, 
        balance=loan.total_outstanding, date=funding_date, 
        uid=user_profile.uid, luid=settings.LUID)
        statement.save()

        
        messages.success(request, f'Loan Update Processed successfully.')
        
        return redirect('funding_receipt_upload', loan.ref)

    context = {
        'nav': 'register_additional_loan',
    }

    return render(request, 'functions/register_additional_loan.html', context)


def fund_additional_loan(request, running_loan_id, new_loan_id):
    running_loan = Loan.objects.get(id=running_loan_id)
    new_loan = Loan.objects.get(id=new_loan_id)

    # All statements from existing loan copied to new loan and new statements will continue from last statement of existing loan
    # New statements will be created for the new loan and the existing loan will be marked as COMPLETED and the new loan will be marked as ACTIVE

    existing_statements = Statement.objects.filter(loanref=running_loan)
    for statement in existing_statements:
        statement.pk = None  # This will create a new instance instead of updating the existing one
        statement.loanref = new_loan
        statement.save()

    today = datetime.date.today()

    Statement.objects.create(owner=running_loan.owner, ref=f'{running_loan.ref}LE', loanref=running_loan, type="REFINANCE", 
    statement=f"Loan Ended - Balance transfered to new loan {new_loan.ref}", debit=running_loan.total_outstanding, 
    balance=0.00, date=today, uid=running_loan.owner.uid, luid=settings.LUID)

    running_loan.status = 'COMPLETED'
    running_loan.funded_category = 'COMPLETED'
    existing_balance = running_loan.total_outstanding
    running_loan.total_outstanding = 0.00
    running_loan.save()

    new_loan.status = 'ACTIVE'
    new_loan.save()

    loan = new_loan

    #new code:

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
        Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="FUNDING", statement="Loan Funded", credit=loan.amount-loan.processing_fee, balance=loan.total_outstanding, date=today, uid=user.uid, luid=settings.LUID)
        Statement.objects.create(owner=user, ref=f'{loan.ref}F', loanref=loan, type="OTHER", statement="Loan Processing Fee", credit=loan.processing_fee, balance=loan.total_outstanding, date=today, uid=user.uid, luid=settings.LUID)
    else:
        Statement.objects.create(owner=user, ref=f'{loan.ref}ALF', loanref=loan, type="FUNDNG", statement=f"Additional Loan Funded - Balance updated with additional interest of {loan.interest}", credit=loan.amount, balance=loan.total_outstanding, date=today, uid=user.uid, luid=settings.LUID)

    

    #### Update loan balances and everything
    loan.classification = 'ADDITIONAL'
    loan.principal_loan_paid += running_loan.principal_loan_paid
    loan.interest_paid += running_loan.interest_paid
    loan.default_interest_paid += running_loan.default_interest_paid
    loan.total_paid += running_loan.total_paid
    
    loan.fortnights_paid += running_loan.fortnights_paid
    loan.number_of_repayments += running_loan.number_of_repayments
    loan.last_repayment_amount = running_loan.last_repayment_amount
    loan.last_repayment_date = running_loan.last_repayment_date
    loan.number_of_advance_payments += running_loan.number_of_advance_payments
    loan.last_advance_payment_date = running_loan.last_advance_payment_date
    loan.last_advance_payment_amount = running_loan.last_advance_payment_amount
    loan.total_advance_payment += running_loan.total_advance_payment
    loan.advance_payment_surplus += running_loan.advance_payment_surplus
    
    loan.number_of_defaults += running_loan.number_of_defaults
    loan.last_default_date = running_loan.last_default_date
    loan.last_default_amount = running_loan.last_default_amount
    loan.days_in_default += running_loan.days_in_default
    loan.total_arrears += running_loan.total_arrears

    loan.principal_loan_receivable += running_loan.principal_loan_receivable
    loan.ordinary_interest_receivable += running_loan.ordinary_interest_receivable
    loan.default_interest_receivable += running_loan.default_interest_receivable

    loan.opt1 = running_loan.opt1
    loan.opt2 = running_loan.opt2
    loan.opt3 = running_loan.opt3   
    loan.opt4 = running_loan.opt4
    loan.opt5 = running_loan.opt5
    loan.dcc = running_loan.dcc
    loan.notes = running_loan.notes
    loan.save()

    # Construct the repayment dates HTML string
    repayment_dates_html = ''.join([f'<div>{date}</div>' for date in repayment_dates_list])
    #send email to user
    
    subject = f'Additional Loan-{loan.ref} FUNDED'
    ''' if header_cta == 'yes' '''
    cta_label = ''
    cta_link = ''

    greeting = f'Hi {loan.owner.first_name}'
    message = 'Your approved additional loan has been funded'
    message_details = f'Amount: K{round(loan.amount-settings.PROCESSING_FEE,2)}<br>\
                        Processing Fee: K{round(settings.PROCESSING_FEE,0)}<br>\
                        Total Loan: K{round(loan.total_loan_amount,0)}<br>\
                        New Repayment: K{round(loan.repayment_amount,0)}<br>\
                        Repayment Start Date: {loan.next_payment_date}<br><br>\
                        Your repayment dates are listed here in order for your reference:</br>\
                        {repayment_dates_html}'

    ''' if cta == 'yes' '''
    cta_btn1_label = 'View Loan'
    cta_btn1_link = f'{settings.DOMAIN}/loan/myloan/{loan.ref}/'
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
        'user': user,
        'domain': settings.DOMAIN,
    })

    #recipients
    reply_to_email = settings.REPLY_TO_EMAIL
    email_list_one = [user.email, user.work_email]
    email_list_two = settings.ADMIN_EMAILS
    email_list  = email_list_one + email_list_two
    cc_list = settings.CC_EMAILS
    bcc_list = settings.BCC_EMAILS
    
    text_content = strip_tags(email_content)
    email = EmailMultiAlternatives(subject,text_content,sender,email_list, bcc=bcc_list, cc=cc_list, reply_to=[reply_to_email])
    email.attach_alternative(email_content, "text/html")

    try: 
        email.send()
        messages.success(request, f'Loan funding notice was sent to {loan.owner.first_name} {loan.owner.last_name} successfully.')
    except:
        messages.error(request, 'Loan has been categorized as "FUNDED" and status updated to "RUNNING".', extra_tags='info')
        messages.error(request, 'Loan funding notice was NOT sent, please advise the client by email or phone.".', extra_tags='danger')

