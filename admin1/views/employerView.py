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

from collections import defaultdict

################ 
# START OF CODE
################

@admin_check
def employer_overview(request):

    user_profiles = UserProfile.objects.all()
    employers_dict = defaultdict(list)
    for profile in user_profiles:
        if profile.employer:
            employers_dict[profile.employer].append(profile)

    employers = {}
    for employer, profiles in employers_dict.items():
        total_loans = Loan.objects.filter(owner__in=profiles).count()
        repayment_total = Loan.objects.filter(owner__in=profiles).aggregate(Sum('repayment_amount'))['repayment_amount__sum'] or 0
        outstanding_total = Loan.objects.filter(owner__in=profiles).aggregate(Sum('total_outstanding'))['total_outstanding__sum'] or 0
        default_total = Loan.objects.filter(owner__in=profiles, status='DEFAULTED').count()
        arrears_total = Loan.objects.filter(owner__in=profiles).aggregate(Sum('total_arrears'))['total_arrears__sum'] or 0

        employers[employer] = {
            'profiles': profiles,
            'number_of_loans': total_loans,
            'repayment_total': repayment_total,
            'outstanding_total': outstanding_total,
            'default_total': default_total,
            'arrears_total': arrears_total
        }

    context = {
        'nav': 'employer_overview',
        'employers': employers,
        }
    
    return render(request, 'employer_overview.html', context)

@admin_check
def loans_by_employer(request):
    user_profiles = UserProfile.objects.all()
    employers_dict = defaultdict(list)
    for profile in user_profiles:
        if profile.employer:
            employers_dict[profile.employer].append(profile)

    employers = {}
    for employer, profiles in sorted(employers_dict.items()):
        loans = Loan.objects.filter(owner__in=profiles).exclude(funded_category='COMPLETED')
        loan_details = []
        for loan in loans:
            loan_details.append({
                'loan_ref': loan.ref,
                'alesco_paycode': loan.owner.alesco_paycode,
                'first_name': loan.owner.first_name,
                'last_name': loan.owner.last_name,
                'status': loan.status,
                'loan_amount': loan.amount,
                'number_of_fortnights': loan.number_of_fortnights,
                'repayment_amount': loan.repayment_amount,
                'total_outstanding': loan.total_outstanding,
                'number_of_defaults': loan.number_of_defaults,
                'total_arrears': loan.total_arrears,
                'user_id': loan.owner.id,
            })

        employers[employer] = {
            'profiles': profiles,
            'loans': loan_details,
        }

    context = {
        'nav': 'loans_by_employer',
        'employers': employers,
        'domain': settings.DOMAIN,
    }

    return render(request, 'loans_by_employer.html', context)