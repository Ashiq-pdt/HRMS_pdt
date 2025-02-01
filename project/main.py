# main.py

from random import random
from flask import Blueprint, render_template,request,flash,redirect,url_for,Markup,session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required,logout_user
from flask_security import roles_accepted
from .models import CompanyClockInOptions, CompanyDetails,MutipleAcces, CompanyMemo, User,Departments,user_datastore,CompanyOffices,CompanyEmployeeSchedule,CompanyHolidays
from bson.objectid import ObjectId
from flask_security import roles_accepted,current_user
from config import settings
from .decorators import employees_required
from .company.model import EmployeeDetails,EmployeeAttendance,EmployeeLeaveApprover,EmployeeLeaveRequest,EmployeeLeaveApplication
from .employee.model import EmployeeBreakHistory
from datetime import timedelta

# from . import create_app
#image upload
# from werkzeug.utils import secure_filename
# import os
import datetime 
main = Blueprint('main', __name__)
# app=create_app()


#User Index

#User Index
@main.route('/')
def index():
    if current_user.is_authenticated:
        if( current_user.type == "admin"):
            return render_template('admin/index.html')
        if(current_user.type == "company"):

            
            multiple_access_doc = MutipleAcces.objects(email=current_user.email).first()
            if multiple_access_doc:
                session["mutipleacces_parent_email"] = current_user.email
            mutipleacces_parent_email = session.get("mutipleacces_parent_email")
            if mutipleacces_parent_email:
                multiple_access_doc = MutipleAcces.objects(email=mutipleacces_parent_email).first()
            session["multiple_access_doc"] = multiple_access_doc

            
            company_details = CompanyDetails.objects(user_id=current_user.id).first()
            session["Main_company_name"] = company_details.company_name
            todayDate = datetime.datetime.today()
            

            if not current_user.confirmed:
                flash(Markup('You have not confirmed your email yet. Please check your inbox (and your spam folder) - you should have received an email with a confirmation link. Didn\'t get the email? <a href="/resend" class="text-primary alert-link">Resend Activation Mail</a>'),'danger')
            # Todo: Check if the other documents are expiring based on config sepcified in the alert settings
            notify_expiry()
            leave_applications = EmployeeLeaveApplication.objects(company_id=current_user.id,leave_status="pending").count()
            if leave_applications > 0:
                flash(Markup('There are '+str(leave_applications)+'  leave application(s) awaiting approvers approval. <a href="/leavesapplications" class="text-primary">Click here to view.</a>'),'secondary')
                
            session["company_name"] = company_details.company_name
            session["profile_pic"] = company_details.company_logo if hasattr(company_details,'company_logo') else ''
            return render_template('company/index.html',company_details=company_details,td=todayDate,multiple_access_doc=multiple_access_doc)
        if(current_user.type == "employee"):
            
            multiple_access_doc = MutipleAcces.objects(email=current_user.email).first()
            if multiple_access_doc:
                session["mutipleacces_parent_email"] = current_user.email
            mutipleacces_parent_email = session.get("mutipleacces_parent_email")
            if mutipleacces_parent_email:
                multiple_access_doc = MutipleAcces.objects(email=mutipleacces_parent_email).first()
            
            # session["Main_company_name"] = company_details.company_name

            session["multiple_access_doc"] = multiple_access_doc
            
            multiple_access_data = session.get("multiple_access_data")
            multiple_access_company_id=session.get("multiple_access_company_id")
            if not current_user.confirmed:
                flash(Markup('You have not confirmed your email yet. Please check your inbox (and your spam folder) - you should have received an email with a confirmation link. Didn\'t get the email? <a href="/resend" class="text-primary alert-link">Resend Activation Mail</a>'),'danger')
            # check if employee has any schedule today if not get the default office location else take scheduled office location
            # Todo: Check if the other documents are expiring based on config sepcified in the alert settings
            notify_expiry_employee()
            # employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
            attendance_date = datetime.datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
            previous_attendance_date = (datetime.datetime.today() - timedelta(days=1)).replace(minute=0, hour=0, second=0, microsecond=0) # incoming
            employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
            session["user_company_id"] =employee_details.company_id

            
            todayDate = datetime.datetime.today()
            company_id_old=ObjectId(employee_details.company_id)
            print(f"    Company Name1: {company_id_old}")
            if  multiple_access_company_id:
                if multiple_access_company_id==company_id_old:
                    session["multiple_access_company_old"] =True
                    company_id=ObjectId(employee_details.company_id)                              
                else:
                    session["multiple_access_company_old"] =None
                    company_id=multiple_access_company_id
            else :
                company_id=ObjectId(employee_details.company_id)

            company_details_seesion = CompanyDetails.objects(user_id=employee_details.company_id).first()
            session["Main_company_name"] = company_details_seesion.company_name   

            multiple_access_company_old=session.get("multiple_access_company_old")  
           
            approvers = EmployeeLeaveApprover.objects(employee_details_id=employee_details._id).only('_id')
            if approvers:
            # Look for application request based on approver ids with pending status
                data = []
                for item in approvers:
                    data.append(item._id)
                leave_requests = EmployeeLeaveRequest.objects(approver_id__in=data,request_status="pending").count()
                if leave_requests:
                    flash(Markup('You have '+str(leave_requests)+'  leave applications awaiting your approval. <a href="/leavesapprovals" class="text-primary">Click here to view.</a>'),'secondary')
            
            start_of_month = datetime.datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
            nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
            # subtracting the days from next month date to
            # get last date of current Month
            end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)

            holiday_details = CompanyHolidays.objects(company_id=company_id,occasion_date__gt=todayDate).order_by('occasion_date')

            # existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from=attendance_date).first()
            # upcoming_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from__gte=attendance_date)

            if  multiple_access_company_id:
                if multiple_access_company_id==company_id_old:
                    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from=attendance_date).first()
                    upcoming_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from__gte=attendance_date)
                else :
                    existing_schedule = []
                    upcoming_schedule = []
            else :
                existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from=attendance_date).first()
                upcoming_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from__gte=attendance_date)
            
               
            company_office_details = CompanyOffices.objects(company_id=employee_details.company_id,is_default=True).first()
            attendance_data = EmployeeAttendance.objects(company_id=company_id,attendance_date=attendance_date,employee_details_id=ObjectId(employee_details._id)).first()

            previos_day_attendance_data = EmployeeAttendance.objects(company_id=company_id,attendance_date=previous_attendance_date,employee_details_id=ObjectId(employee_details._id)).first()

            present_count = EmployeeAttendance.objects(company_id=company_id,attendance_status='present',employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
            late_count = EmployeeAttendance.objects(company_id=company_id,is_late=True,employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
            absent_count = EmployeeAttendance.objects(company_id=company_id,attendance_status='absent',employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
            monthly_att_data =EmployeeAttendance.objects(company_id=company_id,employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).order_by('-attendance_date')
            break_data = EmployeeBreakHistory.objects(company_id=company_id,attendance_date=attendance_date,employee_details_id=ObjectId(employee_details._id),already_ended=False).first()
            
            
            company_memos = CompanyMemo.objects(company_id=company_id)


            if employee_details.employee_company_details.allow_outside_checkin:
                session["allowed_outside"] = True
                clock_in_options = CompanyClockInOptions.objects(company_id=ObjectId(employee_details.company_id))
            else:
                session["allowed_outside"] = False
                clock_in_options = CompanyClockInOptions.objects(company_id=ObjectId(employee_details.company_id),outside_office=False)

            if (existing_schedule and existing_schedule.allow_outside_checkin) or employee_details.employee_company_details.allow_outside_checkin:
                if (hasattr(existing_schedule,'working_office') and existing_schedule.working_office is not None):
                    # session["office_lat"] = employee_details.employee_company_details.working_office.location_latitude
                    # session["office_lng"] = employee_details.employee_company_details.working_office.location_longitude
                    # session["office_radius"] = employee_details.employee_company_details.working_office.location_radius
                    session["working_office"] = existing_schedule.working_office._id
                    session["office_lat"] = existing_schedule.working_office.location_latitude
                    session["office_lng"] = existing_schedule.working_office.location_longitude
                    session["office_radius"] = existing_schedule.working_office.location_radius
                   
                else:
                     #allowed_outside -false
                    session["working_office"] = company_office_details._id
                    session["office_lat"] = company_office_details.location_latitude
                    session["office_lng"] = company_office_details.location_longitude
                    session["office_radius"] = company_office_details.location_radius
                    # session["working_office"] = employee_details.employee_company_details.working_office._id
                    # session["office_lat"] = employee_details.employee_company_details.working_office.location_latitude
                    # session["office_lng"] = employee_details.employee_company_details.working_office.location_longitude
                    # session["office_radius"] = employee_details.employee_company_details.working_office.location_radius
            else:
                if employee_details.employee_company_details.working_office:
                    #allowed_outside -true
                    session["working_office"] = employee_details.employee_company_details.working_office._id
                    session["office_lat"] = employee_details.employee_company_details.working_office.location_latitude
                    session["office_lng"] = employee_details.employee_company_details.working_office.location_longitude
                    session["office_radius"] = employee_details.employee_company_details.working_office.location_radius
                else:
                    session["working_office"] = company_office_details._id
                    session["office_lat"] = company_office_details.location_latitude
                    session["office_lng"] = company_office_details.location_longitude
                    session["office_radius"] = company_office_details.location_radius

            if previos_day_attendance_data and previos_day_attendance_data.has_next_day_clockout == True:
                if  True if datetime.datetime.today() < previos_day_attendance_data.next_day_co_final_datetime else False and True if (previos_day_attendance_data and hasattr(previos_day_attendance_data,'employee_check_out_at')) or (hasattr(previos_day_attendance_data,'attendance_status') and previos_day_attendance_data.attendance_status == "absent") else False:
                    session["has_next_day_clockout"] = True
                    session["already_checked_in"] = True if (previos_day_attendance_data and hasattr(previos_day_attendance_data,'employee_check_in_at')) or (hasattr(previos_day_attendance_data,'attendance_status') and previos_day_attendance_data.attendance_status == "absent") else False
                    session["already_checked_out"] = True if (previos_day_attendance_data and hasattr(previos_day_attendance_data,'employee_check_out_at')) or (hasattr(previos_day_attendance_data,'attendance_status') and previos_day_attendance_data.attendance_status == "absent") else False
                    session["checked_in_time"] = previos_day_attendance_data.employee_check_in_at if (previos_day_attendance_data and hasattr(previos_day_attendance_data,'employee_check_in_at')) else False
                    session["checked_out_time"] = previos_day_attendance_data.employee_check_out_at if (previos_day_attendance_data and hasattr(previos_day_attendance_data,'employee_check_out_at')) else ''
                    session['is_absent'] = True if (hasattr(previos_day_attendance_data,'attendance_status') and previos_day_attendance_data.attendance_status == "absent") else False
                    session['on_break'] = True if (hasattr(previos_day_attendance_data,'on_break') and previos_day_attendance_data.on_break == True) else False
                else:
                    session["has_next_day_clockout"] = False
                    session["already_checked_in"] = True if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
                    session["already_checked_out"] = True if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
                    session["checked_in_time"] = attendance_data.employee_check_in_at if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) else False
                    session["checked_out_time"] = attendance_data.employee_check_out_at if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) else ''
                    session['is_absent'] = True if (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
                    session['on_break'] = True if (hasattr(attendance_data,'on_break') and attendance_data.on_break == True) else False
            else:
                session["has_next_day_clockout"] = False
                session["already_checked_in"] = True if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
                session["already_checked_out"] = True if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
                session["checked_in_time"] = attendance_data.employee_check_in_at if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) else False
                session["checked_out_time"] = attendance_data.employee_check_out_at if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) else ''
                session['is_absent'] = True if (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
                session['on_break'] = True if (hasattr(attendance_data,'on_break') and attendance_data.on_break == True) else False

            session["employee_name"] = employee_details.first_name + ' ' + employee_details.last_name
            session["employee_designation"] = employee_details.employee_company_details.designation
            session["profile_pic"] = employee_details.profile_pic
            session["company_id"] = employee_details.company_id
            session["employee_details_id"] = employee_details._id
            session["already_checked_in"] = True if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
            session["already_checked_out"] = True if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
            session["checked_in_time"] = attendance_data.employee_check_in_at if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) else False
            session["checked_out_time"] = attendance_data.employee_check_out_at if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) else ''
            
            if  multiple_access_company_id:
                if multiple_access_company_id==company_id_old:
                    session["is_approver"] = True if employee_details.is_approver else False
                    session["is_super_approver"] = True if employee_details.is_super_leave_approver else False
                    session["is_time_approver"] = True if employee_details.is_time_approver else False
                else :
                    session["is_approver"] = False
                    session["is_super_approver"] = False
                    session["is_time_approver"] = False
            else:
                session["is_approver"] = True if employee_details.is_approver else False
                session["is_super_approver"] = True if employee_details.is_super_leave_approver else False
                session["is_time_approver"] = True if employee_details.is_time_approver else False

            session['is_absent'] = True if (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
            session['on_break'] = True if (hasattr(attendance_data,'on_break') and attendance_data.on_break == True) else False
            session['home_allowed'] = True if employee_details.employee_company_details.home_option else False
            
            # session["office_lat"] = company_office_details.location_latitude
            # session["office_lng"] = company_office_details.location_longitude
            # session["office_radius"] = company_office_details.location_radius


            return render_template('employee/index.html', present_count=present_count, absent_count=absent_count,employee_attendance_data=monthly_att_data,holiday_details=holiday_details,todayDate=todayDate,break_data=break_data,clock_in_options=clock_in_options,late_count=late_count,company_memos=company_memos,upcoming_schedule=upcoming_schedule)
    else:
        return redirect(url_for('auth.login'))

@main.route('/multiple_access/<email_id>')
def multiple_access_details(email_id):
    # Fetch the company details using the company_id
    if(current_user.type == "company"):
        print(email_id)
        #company = CompanyDetails.objects(company_id=company_id).first()
        parent_email = session.get("mutipleacces_parent_email")
        if parent_email:
            multiple_access_doc = MutipleAcces.objects(email=parent_email).first()

        multiple_access_doc1 = MutipleAcces.objects(email=parent_email).first()
        session["mutipleacces_email"] = current_user.email
        if multiple_access_doc1:
            if parent_email == multiple_access_doc1.email:
                session_data= dict(session)
                if '_user_id' in session_data:
                    print(multiple_access_doc1.company_id)
                    for entry in multiple_access_doc1.MultipleAccessEntry:
                        if email_id == entry.multiple_access_email_id:
                            print(f"  - Email ID: {entry.multiple_access_email_id}")
                            print(f"    Company Name: {entry.multiple_access_company_id}")
                            print(f"    Enabled: {entry.multiple_access_enabled}")
                            user_id= entry.multiple_access_company_id
                            current_user.id = entry.multiple_access_company_id
                            current_user.email=entry.multiple_access_email_id
                            session_data['_user_id'] = entry.multiple_access_company_id
                            session['mutipleacces_company'] = entry.multiple_access_company_name
                            session['multiple_access_company_id'] = entry.multiple_access_company_id
                            session.update(session_data) 
                            session['multiple_access_company_id'] = entry.multiple_access_company_id
                            session['mutipleacces_company'] = entry.multiple_access_company_name # Update session with new data
                print("Session email matches the email in multiple_access_doc.")
            else:
                print("Session email does NOT match the email in multiple_access_doc.")
        else:
            print("No document found for the given email.")

    
        if user_id:
            user_id = session.get("_user_id")
        company_details = CompanyDetails.objects(user_id=user_id).first()
        todayDate = datetime.datetime.today()
        

        if not current_user.confirmed:
            flash(Markup('You have not confirmed your email yet. Please check your inbox (and your spam folder) - you should have received an email with a confirmation link. Didn\'t get the email? <a href="/resend" class="text-primary alert-link">Resend Activation Mail</a>'),'danger')
        # Todo: Check if the other documents are expiring based on config sepcified in the alert settings
        notify_expiry()
        leave_applications = EmployeeLeaveApplication.objects(company_id=current_user.id,leave_status="pending").count()
        if leave_applications > 0:
            flash(Markup('There are '+str(leave_applications)+'  leave application(s) awaiting approvers approval. <a href="/leavesapplications" class="text-primary">Click here to view.</a>'),'secondary')
            
        session["company_name"] = company_details.company_name
        session["profile_pic"] = company_details.company_logo if hasattr(company_details,'company_logo') else ''
        return render_template('company/index.html',company_details=company_details,td=todayDate,multiple_access_doc=multiple_access_doc)
    


    if current_user.type == "employee":
        main_email_id = current_user.email
        if main_email_id:
            multiple_access_doc = MutipleAcces.objects(email=main_email_id).first()
            employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
            if multiple_access_doc:
                if main_email_id == multiple_access_doc.email:
                    session_data = dict(session)
                    if '_user_id' in session_data:
                        print(multiple_access_doc.company_id)  # Assuming 'company_id' exists
                        for entry in multiple_access_doc.MultipleAccessEntry:
                            if email_id == entry.multiple_access_email_id:
                                session['multiple_access_data'] = True
                                session['multiple_access_company_id'] = entry.multiple_access_company_id
                                session['mutipleacces_company'] = entry.multiple_access_company_name
                                break
                        else:
                            session['multiple_access_data'] = False  # Email does not match any entry
                            session['multiple_access_company_id'] = None  # Optional: Set to None if no match
                    print("Session email matches the email in multiple_access_doc.")
                else:
                    print("Session email does NOT match the email in multiple_access_doc.")
            else:
                print("No document found for the given email.")

        # Print session values to debug
        print("Session values:")
        for key, value in session.items():
            print(f"{key}: {value}")

        return redirect(url_for('main.index'))

       

      
def notify_expiry():

    date_from = datetime.datetime.now().replace(minute=0, hour=0, second=0,microsecond=0)
    expiry_date = date_from + timedelta(days=int(90))
    # Define the aggregation pipeline
    pipeline = [
        {
            "$match": {
                "company_id": { "$eq": current_user.id },
                "documents.document_expiry_on": {
                    "$gte": date_from,
                    "$lte": expiry_date
                }
            }
        },
        {
            "$unwind": "$documents"
        },
            {
            "$match": {
                "documents.document_expiry_on": {
                    "$gte": date_from,
                    "$lte": expiry_date
                }
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "count": { "$sum": 1 }
            }
        },
        {
            "$group": {
                "_id": "",
                "total_documents": { "$sum": "$count" },
                "total_employees": { "$sum": 1 }
            }
        }
    ]
    em = EmployeeDetails.objects.aggregate(*pipeline)
    employee_list = list(em)
    # Print the number of documents expiring in a day for each employee
    for doc in employee_list:
         # Create the message string
        message = Markup(f"You have {doc['total_documents']} document(s) of {doc['total_employees']} employee(s) expiring soon (in 90 Days)! <a href='/documentdashboard?no_of_days=90' class='alert-link'> See Now!</a>")
        flash(message,'info')

def notify_expiry_employee():
    date_from = datetime.datetime.now().replace(minute=0, hour=0, second=0,microsecond=0)
    expiry_date = date_from + timedelta(days=int(90))
    # Define the aggregation pipeline
    pipeline = [
        {
            "$match": {
                "user_id": { "$eq": current_user.id },
                "documents.document_expiry_on": {
                    "$gte": date_from,
                    "$lte": expiry_date
                }
            }
        },
        {
            "$unwind": "$documents"
        },
            {
            "$match": {
                "documents.document_expiry_on": {
                    "$gte": date_from,
                    "$lte": expiry_date
                }
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "count": { "$sum": 1 }
            }
        },
        {
            "$group": {
                "_id": "",
                "total_documents": { "$sum": "$count" },
                "total_employees": { "$sum": 1 }
            }
        }
    ]
    em = EmployeeDetails.objects.aggregate(*pipeline)
    employee_list = list(em)
    # Print the number of documents expiring in a day for each employee
    for doc in employee_list:
         # Create the message string
        message = Markup(f"You have {doc['total_documents']} document(s) expiring soon! <a href='/profile' class='alert-link'> See Now!</a>")
        flash(message,'info')