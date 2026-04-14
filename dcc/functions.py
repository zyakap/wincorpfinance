import requests
from django.conf import settings
from django.shortcuts import render

from .serializers import ProfileSerializer, LoanSerializer, StatementSerializer  # Import your Serializer

def check_client_in_dcc(uid):
    
    dcc_endpoint = settings.DCC_ENDPOINT
    endpoint = f'https://{dcc_endpoint}/API/get_clientprofile/{uid}/'
    try:
        # Make a GET request to the API endpoint
        response = requests.get(endpoint, verify=False)
    except:
        error = "DCC Credit Database is Offline."
        return error

    # Check if the request was successful
    print("PRINTING RESPONSE")
    print(response)
    if response.status_code == 200:
        # Extract JSON data from the response
        data = response.json()
        print(data)
        # Map the keys from the API response to the serializer fields
        mapped_data = {
            'uid': data.get('CUID'),
            'luid': data.get('LUID')
        }
        print("Mapped Data:", mapped_data)
        # Create an instance of ProfileSerializer
        if data:
            serializer = ProfileSerializer(data=mapped_data)
            # Use ProfileSerializer to deserialize the data into Profile instances
            # Use LoanSerializer to deserialize the data into Loan instances
            if serializer.is_valid():
                client = serializer.data
                print(client)
                return client
        else:
            error = "Client is not in database."
            return error
    elif response.status_code == 404:      
        error = "Client is not in DCC Credit Database."
        return error
    else:
        # Handle error if the request was not successful
        error = "Failed to fetch data from the API"
        return error

def get_loans_for_client(uid):
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
            serializer = LoanSerializer(data=data)
            # Use LoanSerializer to deserialize the data into Loan instances
            if serializer.is_valid():
                loans = serializer.validated_data
                print(loans)
                return loans
        else:
            error = "Client has no loan(s)."
            return error
            
    else:
        # Handle error if the request was not successful
        error = "Failed to fetch data from the API"
        return error

def get_transactions_for_client(uid):
    dcc_endpoint = settings.DCC_ENDPOINT
    endpoint = f'https://{dcc_endpoint}/API/get_client_transactions/{uid}/'
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
            serializer = StatementSerializer(data=data)
            # Use LoanSerializer to deserialize the data into Loan instances
            if serializer.is_valid():
                statements = serializer.data
                print(statements)
                return statements
        else:
            error = "Client has no transaction(s)."
            return error
            
    else:
        # Handle error if the request was not successful
        error = "Failed to fetch data from the API"
        return error


