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


#loanmasta_combination_check
def combination_check(amount, num_fns):
    max_fortnights = {
        500: 4,
        600: 4,
        700: 5,
        800: 5,
        900: 6,
        1000: 6,
        1100: 6,
        1200: 8,
        1300: 8,
        1400: 10,
        1500: 10,
        1600: 11,
        1700: 11,
        1800: 12,
        1900: 12,
        2000: 13,
        2100: 13,
        2200: 14,
        2300: 14,
        2400: 15,
        2500: 15,
        2600: 16,
        2700: 16,
        2800: 16,
        2900: 16,
        3000: 18,
        3100: 18,
        3200: 18,
        3300: 20,
        3400: 20,
        3500: 20,
        3600: 21,
        3700: 21,
        3800: 22,
        3900: 22,
        4000: 23,
        4100: 23,
        4200: 24,
        4300: 24,
        4400: 24,
        4500: 30,
        4600: 30,
        4700: 30,
        4800: 30,
        4900: 30,
        5000: 30,
    }

    max_fn = max_fortnights.get(amount)
    print(f'MAX FN FUNCTION: {max_fn}')
    if max_fn is not None and num_fns not in range(settings.MIN_FN, max_fn + 1):
        return max_fn
    else:
        return 0

#ktpfinance_repayment
def repayment(amount, interest_type, fns, location):
    """Calculate the repayment amount based on the provided table
    Args:
        amount (float): The amount of the loan
        fns (int): The number of fortnights in the loan term
    Returns:
        pmt (float): The payment for a loan based on the provided table
    """ 

    # Repayment table: keys = loan amount, values = list of fortnightly payments starting from 3FN
    # Index 0 = 3FN, index 1 = 4FN, ..., index 27 = 30FN
    repayment_table = {
        500:  [229.67, 172.25],
        600:  [275.60, 206.70],
        700:  [321.53, 241.15, 192.92],
        800:  [367.47, 275.60, 220.48],
        900:  [413.40, 310.05, 248.04, 206.70],
        1000: [459.33, 344.50, 275.60, 229.67],
        1100: [505.27, 378.95, 303.16, 252.63],
        1200: [551.20, 413.40, 330.72, 275.60, 245.31, 214.65],
        1300: [597.13, 447.85, 358.28, 298.57, 265.76, 232.54],
        1400: [643.07, 482.30, 385.84, 321.53, 286.20, 250.43, 222.60, 207.76],
        1500: [689.00, 516.75, 413.40, 344.50, 306.64, 268.31, 238.50, 222.60],
        1600: [734.93, 551.20, 440.96, 367.47, 327.09, 286.20, 254.40, 237.44, 215.85],
        1700: [780.87, 585.65, 468.52, 390.43, 347.53, 304.09, 270.30, 252.28, 229.35],
        1800: [826.80, 620.10, 496.08, 413.40, 367.97, 321.98, 286.20, 267.12, 242.84, 222.60],
        1900: [872.73, 654.55, 523.64, 436.37, 388.41, 339.86, 302.10, 281.96, 256.33, 234.97],
        2000: [918.67, 689.00, 551.20, 459.33, 408.86, 357.75, 318.00, 296.80, 269.82, 247.33, 236.46],
        2100: [964.60, 723.45, 578.76, 482.30, 429.30, 375.64, 333.90, 311.64, 283.31, 259.70, 248.28],
        2200: [1010.53, 757.90, 606.32, 505.27, 449.74, 393.53, 349.80, 326.48, 296.80, 272.07, 260.11, 241.53],
        2300: [1056.47, 792.35, 633.88, 528.23, 470.19, 411.41, 365.70, 341.32, 310.29, 284.43, 271.93, 252.51],
        2400: [1102.40, 826.80, 661.44, 551.20, 490.63, 429.30, 381.60, 356.16, 323.78, 296.80, 283.75, 263.49, 245.92],
        2500: [1148.33, 861.25, 689.00, 574.17, 511.07, 447.19, 397.50, 371.00, 337.27, 309.17, 295.58, 274.46, 256.17],
        2600: [1194.27, 895.70, 716.56, 597.13, 531.51, 465.08, 413.40, 385.84, 350.76, 321.53, 307.40, 285.44, 266.41, 258.38],
        2700: [1240.20, 930.15, 744.12, 620.10, 551.96, 482.96, 429.30, 400.68, 364.25, 333.90, 319.22, 296.42, 276.66, 268.31],
        2800: [1286.13, 964.60, 771.68, 643.07, 572.40, 500.85, 445.20, 415.52, 377.75, 346.27, 331.05, 307.40, 286.91, 278.25],
        2900: [1332.07, 999.05, 799.24, 666.03, 592.84, 518.74, 461.10, 430.36, 391.24, 358.63, 342.87, 318.38, 297.15, 288.19],
        3000: [1378.00, 1033.50, 826.80, 689.00, 613.29, 536.63, 477.00, 445.20, 404.73, 371.00, 354.69, 329.36, 307.40, 298.13, 280.59, 265.00],
        3100: [1423.93, 1067.95, 854.36, 711.97, 633.73, 554.51, 492.90, 460.04, 418.22, 383.37, 366.52, 340.34, 317.65, 308.06, 289.94, 273.83],
        3200: [1469.87, 1102.40, 881.92, 734.93, 654.17, 572.40, 508.80, 474.88, 431.71, 395.73, 378.34, 351.31, 327.89, 318.00, 299.29, 282.67],
        3300: [1515.80, 1136.85, 909.48, 757.90, 674.61, 590.29, 524.70, 489.72, 445.20, 408.10, 390.16, 362.29, 338.14, 327.94, 308.65, 291.50, 285.36, 271.10],
        3400: [1561.73, 1171.30, 937.04, 780.87, 695.06, 608.18, 540.60, 504.56, 458.69, 420.47, 401.98, 373.27, 348.39, 337.88, 318.00, 300.33, 294.01, 279.31],
        3500: [1607.67, 1205.75, 964.60, 803.83, 715.50, 626.06, 556.50, 519.40, 472.18, 432.83, 413.81, 384.25, 358.63, 347.81, 327.35, 309.17, 302.66, 287.53],
        3600: [1653.60, 1240.20, 992.16, 826.80, 735.94, 643.95, 572.40, 534.24, 485.67, 445.20, 425.63, 395.23, 368.88, 357.75, 336.71, 318.00, 311.31, 295.74, 281.66],
        3700: [1699.53, 1274.65, 1019.72, 849.77, 756.39, 661.84, 588.30, 549.08, 499.16, 457.57, 437.45, 406.21, 379.13, 367.69, 346.06, 326.83, 319.95, 303.96, 289.48],
        3800: [1745.47, 1309.10, 1047.28, 872.73, 776.83, 679.73, 604.20, 563.92, 512.65, 469.93, 449.28, 417.19, 389.37, 377.63, 355.41, 335.67, 328.60, 312.17, 297.30, 292.95],
        3900: [1791.40, 1343.55, 1074.84, 895.70, 797.27, 697.61, 620.10, 578.76, 526.15, 482.30, 461.10, 428.16, 399.62, 387.56, 364.76, 344.50, 337.25, 320.39, 305.13, 300.65],
        4000: [1837.33, 1378.00, 1102.40, 918.67, 817.71, 715.50, 636.00, 593.60, 539.64, 494.67, 472.92, 439.14, 409.87, 397.50, 374.12, 353.33, 345.89, 328.60, 312.95, 308.36, 294.96],
        4100: [1883.27, 1412.45, 1129.96, 941.63, 838.16, 733.39, 651.90, 608.44, 553.13, 507.03, 484.75, 450.12, 420.11, 407.44, 383.47, 362.17, 354.54, 336.82, 320.78, 316.07, 302.33],
        4200: [1929.20, 1446.90, 1157.52, 964.60, 858.60, 751.28, 667.80, 623.28, 566.62, 519.40, 496.57, 461.10, 430.36, 417.38, 392.82, 371.00, 363.19, 345.03, 328.60, 323.78, 309.70, 296.80],
        4300: [1975.13, 1481.35, 1185.08, 987.57, 879.04, 769.16, 683.70, 638.12, 580.11, 531.77, 508.39, 472.08, 440.61, 427.31, 402.18, 379.83, 371.84, 353.25, 336.42, 331.49, 317.08, 303.87],
        4400: [2021.07, 1515.80, 1212.64, 1010.53, 899.49, 787.05, 699.60, 652.96, 593.60, 544.13, 520.22, 483.06, 450.85, 437.25, 411.53, 388.67, 380.48, 361.46, 344.25, 339.20, 324.45, 310.93],
        4500: [2067.00, 1550.25, 1240.20, 1033.50, 919.93, 804.94, 715.50, 667.80, 607.09, 556.50, 532.04, 494.04, 461.10, 447.19, 420.88, 397.50, 389.13, 369.68, 352.07, 346.91, 331.83, 318.00, 315.00, 302.71, 295.92, 298.78, 292.91, 287.42],
        4600: [2112.93, 1584.70, 1267.76, 1056.47, 940.37, 822.83, 731.40, 682.64, 620.58, 568.87, 543.86, 505.01, 471.35, 457.13, 430.24, 406.33, 397.78, 377.89, 359.90, 354.62, 339.20, 325.07, 322.00, 309.44, 302.49, 305.42, 299.41, 294.13],
        4700: [2158.87, 1619.15, 1295.32, 1079.43, 961.80, 840.71, 747.30, 697.48, 634.07, 581.23, 555.68, 515.99, 481.59, 467.06, 439.59, 415.17, 406.43, 386.11, 367.72, 362.33, 346.57, 332.13, 329.00, 316.17, 309.07, 312.06, 305.92, 300.20],
        4800: [2204.80, 1653.60, 1322.88, 1102.40, 981.26, 858.60, 763.20, 712.32, 647.56, 593.60, 567.51, 526.97, 491.84, 477.00, 448.94, 424.00, 415.07, 394.32, 375.54, 370.04, 353.95, 339.20, 336.00, 322.89, 315.64, 318.70, 312.43, 306.58],
        4900: [2250.73, 1688.05, 1350.44, 1125.37, 1001.70, 876.49, 779.10, 727.16, 661.05, 605.97, 579.33, 537.95, 502.09, 486.94, 458.29, 432.83, 423.72, 402.54, 383.37, 377.75, 361.32, 346.27, 343.00, 329.62, 322.22, 325.34, 318.94, 312.97],
        5000: [2296.67, 1722.50, 1378.00, 1148.33, 1022.14, 894.38, 795.00, 742.00, 674.55, 618.33, 591.15, 548.93, 512.33, 496.88, 467.65, 441.67, 432.37, 410.75, 391.19, 385.45, 368.70, 353.33, 350.00, 336.35, 328.80, 331.98, 325.45, 319.36],
        }

    # Function to get the repayment amount
    if amount not in repayment_table:
        return "Invalid loan amount"
    
    fortnight_index = fns - 3
    if fortnight_index < 0 or fortnight_index >= len(repayment_table[amount]): #since length of both locations should be same
        return "Invalid number of fortnights"
    
    pmt = repayment_table[amount][fortnight_index]
    
    print('Repayment:', pmt)
    
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

