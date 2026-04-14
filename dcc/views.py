import requests
from django.shortcuts import render
from rest_framework.response import Response
from .serializers import LoanSerializer
from accounts.models import UserProfile
from django.conf import settings

# Create your views here.

def dcc_get_loans_for_client(request, uid):
    dcc_endpoint = settings.DCC_ENDPOINT
    endpoint = f'https://{dcc_endpoint}/API/get_client_loans/{uid}/'
    # Make a GET request to the API endpoint
    response = requests.get(endpoint, verify=False)
    # Check if the request was successful
    print("PRINTING RESPONSE")
    print(response)
    
    if response.status_code == 200:
        # Extract JSON data from the response
        data = response.json()
        print(data)
        # Check if 'results' key exists in the data
        if data:
            # Create an instance of ProfileSerializer
            serializer = LoanSerializer(data=data, many=True)
            print(serializer)

            if serializer.is_valid():
                print(serializer.validated_data)
                print('SERIALIZER IS VALID!!!:')
                loans = serializer.validated_data
                print('PRINTING LOANS')
                print(loans)
                print('PRINTING TYPE OF LOANS LIST:')
                print(type(loans))
                #loans = dict(loans_list)
                print('PRINTING TYPE OF LOANS:')
                #print(type(loans))
                #return render(request, 'loanslist.html',{ 'loans':loans })
                return serializer.validated_data
            else:
                print("PRINTING SERIALIZER ERRORS:")
                print(serializer.errors)
                return serializer.errors
        else:
            error = "Client has no loan(s)."
            return render(request, 'error.html', { 'error':error })
            
    else:
        # Handle error if the request was not successful
        error = "Failed to fetch data from the API"
        return render(request, 'error.html', { 'error':error })


def reset_indcc(request):
    userprofiles = UserProfile.objects.all()
    for user in userprofiles:
        user.dcc = False
        user.save()
    return render(request, 'reset_indcc.html', { 'message':'All users have been reset.' })
