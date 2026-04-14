import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings

from accounts.models import UserProfile, UserActivityLog
from loan.models import Loan
from .forms import CreateTicketForm
from .models import SupportTicket, SupportTicketThread

from .functions import send_email, email_admin
from admin1.models import Location
from accounts.functions import check_staff, login_check, admin_check
from admin1.models import AdminSettings

try:
    prefix = AdminSettings.objects.get(settings_name='setting1').loanref_prefix
except:
    prefix = settings.PREFIX

#FILES UPLOAD
from django.core.files.storage import FileSystemStorage
    
domain = settings.DOMAIN

# VIEWS START HERE

@login_check
def user_support(request):
    user = UserProfile.objects.get(user_id=request.user.id)
    upid = user.id
    
    supporttickets = SupportTicket.objects.filter(user_id=upid)

    return render(request, 'user_support.html', {'nav': 'user_support', 'supporttickets': supporttickets, 'user': user})

@login_check
def create_ticket(request):
    uid = request.user.id
    user_profile = UserProfile.objects.get(user_id=uid)
    upid = user_profile.id
    
    if user_profile.first_name == '' or user_profile.last_name == '':
        messages.error(request, "Please update your profile with your first and last name.", extra_tags='danger')
        return redirect('profile')
    
    if request.method == 'POST':
        form = CreateTicketForm(request.POST)
        if form.is_valid():
            
            temp_ref = f'{user_profile.first_name[0]}{user_profile.last_name[0]}{upid}'
            category = form.cleaned_data['category']
            subject = form.cleaned_data['subject']
            content = form.cleaned_data['content']
            ticket = SupportTicket.objects.create(user_id=upid, category=category, subject=subject, content=content, ref=temp_ref)
            ticket.save()
            ref = f'{ticket.ref}T{ticket.id}'
            ticket.ref = ref
            ticket.save()
            
            thread_id = f'{ticket.id}U'
            ticketthread = SupportTicketThread.objects.create(ticket=ticket, thread=thread_id, thread_content=content)
            ticketthread.save()

            ticket.threadlog = f'{ticketthread.id}U'
            ticket.threadq = f'{ticketthread.id}U'
            ticket.status = 'user_replied'
            ticket.save()

            if 'attachment' in request.FILES:
                attachment = request.FILES['attachment']
                fsattachment = FileSystemStorage()
                newattachment_name = f'{ref}-MSG-ATTACHMENT-{attachment.name}'
                attachment_filename = fsattachment.save(newattachment_name, attachment)
                attachment_url = fsattachment.url(attachment_filename)
                ticket.attachment_url = attachment_url
                ticket.attachment_name = attachment_filename
                ticket.save()

                ticketthread.attachment_name = attachment_filename
                ticketthread.attachment_url = attachment_url
                ticketthread.save()

                messages.success(request, 'Attachment uploaded successfully...')
                attachment_check = 'yes'
                attachmentpath = f'media/{attachment_filename}'
            else:
                attachment_check = 'no'
                attachmentpath = ''
            
            status = email_admin(user_profile, sub=f'{user_profile.first_name} {user_profile.last_name} has created a new support ticket: {ref}', msg=subject.upper(), msg_details=content, cta='yes', btnlab='View Ticket', btnlink=f'{settings.DOMAIN}/support/tickets/view/{ticket.ref}', attachcheck=attachment_check, path=attachmentpath)
            
            if status == 1:
               messages.success(request, f"Your ticket {ref} has been created successfully. We will get back to you shortly.")
            else:
                messages.error(request, "EMAIL WAS NOT SENT", extra_tags='danger')
            return redirect('view_ticket', ref=ref)
    else:
        form = CreateTicketForm()
    return render(request, 'create_ticket.html', {'nav': 'user_support', 'form': form, 'user':user_profile})

@login_check
def view_ticket(request, ref):
    
    ticket = SupportTicket.objects.get(ref=ref)
    ticketthread = SupportTicketThread.objects.filter(ticket=ticket).order_by('date')
    
    user = UserProfile.objects.get(id=ticket.user.id)

    if request.method == 'POST':
        content = request.POST.get('thread_content')
        thread_id = f'{ticket.id}U'
        ticketthread = SupportTicketThread.objects.create(ticket=ticket, thread=thread_id, thread_content=content)
        ticketthread.save()
        
        ticket.threadlog += f',{ticketthread.id}U'
        ticket.threadq = f'{ticketthread.id}U'
        ticket.status = 'user_replied'
        ticket.save()
        
        status = email_admin(user, sub=f'{user.first_name} {user.last_name} has replied to support ticket: {ticket.ref}', msg=ticket.subject.upper(), msg_details=content, cta='yes', btnlab='View Ticket', btnlink=f'{settings.DOMAIN}/support/ticket/view/{ref}/')
        
        if status == 1:
            messages.success(request, f"Your reply has been sent successfully.")
        else:
            messages.error(request, "EMAIL WAS NOT SENT", extra_tags='danger')
        return redirect('view_ticket', ref=ref)

    context = {
        'nav': 'user_support',
        'ticket': ticket,
        'ticketthread': ticketthread,
        'user': user,
        'domain': domain
    }

    return render(request, 'view_ticket.html', context)

@login_check
def close_ticket(request, ref):
    user = UserProfile.objects.get(user_id=request.user.id)
    ticket = SupportTicket.objects.get(ref=ref)
    ticket.status = 'closed'
    
    ticket.save()
    thread = f'{ticket.id}U'
    ticketthread = SupportTicketThread.objects.create(ticket=ticket, thread_content="Ticket closed by user.", thread=thread)
    ticketthread.save()
    ticket.threadlog += f',{ticketthread.id}U'
    ticket.threadq = f'{ticketthread.id}U'
    ticket.save()

    status = email_admin(user, sub=f'{user.first_name} {user.last_name} has closed support ticket: {ticket.ref}', msg="TICKET CLOSED", msg_details="Ticket closed by user.", cta='yes', btnlab='View Ticket', btnlink=f'{settings.DOMAIN}/support/tickets/view/{ref}/')
        
    if status == 1:
        messages.success(request, f"Ticket {ref} has been closed.")
    else:
        messages.error(request, "Admin Notification EMAIL WAS NOT SENT", extra_tags='danger')
    return redirect('view_ticket', ref=ref)

@check_staff
def support_tickets(request):
    supporttickets = SupportTicket.objects.all().order_by('date')
    print("here at support")
    return render(request, 'supporttickets.html', {'nav': 'usersupport', 'supporttickets': supporttickets})

@login_check
def staff_view_ticket(request, ref):
    
    ticket = SupportTicket.objects.get(ref=ref)
    ticketthread = SupportTicketThread.objects.filter(ticket=ticket).order_by('date')
    print(ticket.user.id)
    
    user = UserProfile.objects.get(id=ticket.user.id)

    if request.method == 'POST':
        uid = request.user.id
        staff_profile = UserProfile.objects.get(user_id=uid)
        staff = f'{staff_profile.first_name} {staff_profile.last_name}'
        content = request.POST.get('thread_content')
        thread_id = f'{ticket.id}R'
        ticketthread = SupportTicketThread.objects.create(ticket=ticket, thread=thread_id, thread_content=content, responder=staff)
        ticketthread.save()
        
        ticket.threadlog += f',{ticketthread.id}R'
        ticket.threadq = f'{ticketthread.id}R'
        ticket.status = 'staff_replied'
        ticket.save()
        
        status = send_email(user, sub=f'A staff has replied to your support ticket: {ticket.ref}', msg=ticket.subject.upper(), msg_details=content, cta='yes', btnlab='View Ticket', btnlink=f'{settings.DOMAIN}/support/ticket/view/{ref}/')
        
        if status == 1:
            messages.success(request, f"Reply has been sent successfully.")
        else:
            messages.error(request, "EMAIL WAS NOT SENT", extra_tags='danger')
        return redirect('staff_view_ticket', ref=ref)

    context = {
        'nav': 'user_support',
        'ticket': ticket,
        'ticketthread': ticketthread,
        'user': user,
        'domain': domain
    }

    return render(request, 'staff_view_ticket.html', context)

@check_staff
def staff_close_ticket(request, ref):
    staff_profile = UserProfile.objects.get(user_id=request.user.id)
    staff = f'{staff_profile.first_name} {staff_profile.last_name}'
    ticket = SupportTicket.objects.get(ref=ref)
    ticket.status = 'closed'
    
    ticket.save()
    thread = f'{ticket.id}R'
    ticketthread = SupportTicketThread.objects.create(ticket=ticket, thread_content="Ticket closed by a Staff.", thread=thread, responder=staff)
    ticketthread.save()
    ticket.threadlog += f',{ticketthread.id}R'
    ticket.threadq = f'{ticketthread.id}R'
    ticket.save()

    user = UserProfile.objects.get(id=ticket.user.id)
    status = send_email(user, sub=f'A staff has closed support ticket: {ticket.ref}', msg="TICKET CLOSED", msg_details="Ticket closed by a Staff.", cta='yes', btnlab='View Ticket', btnlink=f'{settings.DOMAIN}/support/ticket/view/{ref}/')
        
    if status == 1:
        messages.success(request, f"Ticket {ref} has been closed.")
    else:
        messages.error(request, "User Notification EMAIL WAS NOT SENT", extra_tags='danger')
    return redirect('staff_view_ticket', ref=ref)



#### admin tickets

@admin_check
def support_tickets_admin(request):
    supporttickets = SupportTicket.objects.all().order_by('date')
    return render(request, 'supporttickets_admin.html', {'nav': 'support_tickets_admin', 'supporttickets': supporttickets})

@admin_check
def admin_view_ticket(request, ref):
    
    ticket = SupportTicket.objects.get(ref=ref)
    ticketthread = SupportTicketThread.objects.filter(ticket=ticket).order_by('date')
    print(ticket.user.id)
    
    user = UserProfile.objects.get(id=ticket.user.id)

    if request.method == 'POST':
        uid = request.user.id
        staff_profile = UserProfile.objects.get(user_id=uid)
        staff = f'{staff_profile.first_name} {staff_profile.last_name}'
        content = request.POST.get('thread_content')
        thread_id = f'{ticket.id}R'
        ticketthread = SupportTicketThread.objects.create(ticket=ticket, thread=thread_id, thread_content=content, responder=staff)
        ticketthread.save()
        
        ticket.threadlog += f',{ticketthread.id}R'
        ticket.threadq = f'{ticketthread.id}R'
        ticket.status = 'staff_replied'
        ticket.save()
        
        status = send_email(user, sub=f'A staff has replied to your support ticket: {ticket.ref}', msg=ticket.subject.upper(), msg_details=content, cta='yes', btnlab='View Ticket', btnlink=f'{settings.DOMAIN}/support/ticket/view/{ref}/')
        
        if status == 1:
            messages.success(request, f"Reply has been sent successfully.")
        else:
            messages.error(request, "EMAIL WAS NOT SENT", extra_tags='danger')
        return redirect('admin_view_ticket', ref=ref)

    context = {
        'nav': 'support_tickets_admin',
        'ticket': ticket,
        'ticketthread': ticketthread,
        'user': user,
        'domain': domain
    }

    return render(request, 'admin_view_ticket.html', context)

@admin_check
def pending_tickets_admin(request):
    supporttickets = SupportTicket.objects.all().order_by('date')
    return render(request, 'pending_tickets_admin.html', {'nav': 'pending_tickets_admin', 'supporttickets': supporttickets})

@admin_check
def closed_tickets_admin(request):
    supporttickets = SupportTicket.objects.all().order_by('date')
    return render(request, 'supporttickets_closed_admin.html', {'nav': 'closed_tickets_admin', 'supporttickets': supporttickets})

@admin_check
def open_tickets_admin(request):
    supporttickets = SupportTicket.objects.all().order_by('date')
    return render(request, 'supporttickets_open_admin.html', {'nav': 'open_tickets_admin', 'supporttickets': supporttickets})