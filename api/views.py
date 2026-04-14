from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from accounts.models import UserProfile
from loan.models import Loan, Statement
from .serializers import LoanSerializer, UserProfileSerializer, StatementSerializer


@api_view(['GET'])
def userprofiles(request):
    users = UserProfile.objects.filter(credit_consent='YES').exclude(dcc="INDCC", first_name='', last_name='')
    for user in users:
        user.dcc = 'INDCC'
        user.save()
        
    serializer = UserProfileSerializer(users, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def allloans(request):
    loans = Loan.objects.exclude(dcc='INDCC')
    for loan in loans:
        loan.dcc = 'INDCC'
        loan.save()
    
    print(loans)

    serializer = LoanSerializer(loans, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def statements(request):
    statements = Statement.objects.exclude(dcc='INDCC')
    for statement in statements:
        statement.dcc = 'INDCC'
        statement.save()
    serializer = StatementSerializer(statements, many=True, context={'request': request})
    return Response(serializer.data)

