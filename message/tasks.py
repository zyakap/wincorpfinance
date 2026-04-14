import json
from django.shortcuts import render
from time import sleep
from celery import shared_task
from celery.result import AsyncResult
from .functions import send_email, send_email_toworkemail
from .models import Message, MessageLog
from accounts.models import UserProfile

@shared_task
def notify_customers(msg):
    
    print('Sending 10k emails...')
    print(msg)
    sleep(20)
   


@shared_task
def create_message_asc(userid_list, subject, content, message_id, attach=0, attachpath='', category=None):

    message = Message.objects.get(id=message_id)
    if attach == 1:
        attachcheck = 'yes'
        path = attachpath
    else:
        attachcheck = 'no'
        path = ''
    
    email_sent = []
    email_not_sent = []
    email_sent_work = []
    email_not_sent_work = []
    recipients_personal = 0
    recipients_work = 0

    my_dict = json.loads(userid_list)
    userids = my_dict["user_id_list"]

    user_list = []
    for uid in userids:
        user = UserProfile.objects.get(id=uid)
        user_list.append(user)

    for user in user_list:
        
        try:
            message_log = MessageLog.objects.get(user=user)
        except:
            message_log = MessageLog(user=user)

        if message_log.msgq == '':
            message_log.msgq = f'{str(message.id)}'
        else:
            message_log.msgq += f',{str(message.id)}'
        
        if message_log.msglog == '':
            message_log.msglog = f'{str(message.id)}'
        else:
            message_log.msglog += f',{str(message.id)}'
        
        message_log.save()
        msgtrid = f'{user.id}U{message.id}'
        status = send_email(user, sub=subject, msg=content, msgid=msgtrid, attachcheck=attachcheck, path=path, category=category)
        if status == 1:
            recipients_personal += 1
            email_sent.append(user.id)
            if message.emailto_personal == '':
                message.emailto_personal += f'{str(user.id)}'
            else:
                message.emailto_personal += f',{str(user.id)}'
            message.save()
            
            if message_log.msgbyemail == '':
                message_log.msgbyemail = f'{str(message.id)}'
            else:
                message_log.msgbyemail += f',{str(message.id)}'
            message_log.save()
            
        else:
            recipients_personal += 1
            email_not_sent.append(user.id)
            if message_log.msg_not_emailed == '':
                message_log.msg_not_emailed = f'{str(message.id)}'
            else:
                message_log.msg_not_emailed += f',{str(message.id)}'
            message_log.save()
            
        msgtridw = f'{user.id}W{message.id}'
        status_work = send_email_toworkemail(user, sub=subject, msg=content, msgid=msgtridw, attachcheck=attachcheck, path=path, category=category)
        if status_work == 1:
            recipients_work += 1
            email_sent_work.append(user.id)
            if message.emailto_work == '':
                message.emailto_work += f'{str(user.id)}'
            else:
                message.emailto_work += f',{str(user.id)}'
            message.save()
            
            if message_log.msgbyemail_work == '':
                message_log.msgbyemail_work = f'{str(message.id)}'
            else:
                message_log.msgbyemail_work += f',{str(message.id)}'
            message_log.save()
            
        else:
            if user.work_email == None:
                recipients_work += 0
            else:
                recipients_work += 1
            email_not_sent_work.append(user.id)
            if message_log.msg_not_emailed_work == '':
                message_log.msg_not_emailed_work = f'{str(message.id)}'
            else:
                message_log.msg_not_emailed_work += f',{str(message.id)}'
            message_log.save()
            
        
        message.recipients_personal = recipients_personal
        message.recipients_work = recipients_work

        email_sent_str = ','.join(str(e) for e in email_sent)
        email_not_sent_str = ','.join(str(e) for e in email_not_sent)
        email_sent_work_str = ','.join(str(e) for e in email_sent_work)
        email_not_sent_work_str = ','.join(str(e) for e in email_not_sent_work)

        message.email_sent = email_sent_str
        message.email_not_sent = email_not_sent_str
        message.email_sent_work = email_sent_work_str
        message.email_not_sent_work = email_not_sent_work_str
        message.save()

    message.delivery_status = 'done'
    message.save()