# main.py

from random import random
from flask import Blueprint, render_template,request,flash,redirect,url_for,Markup,session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required,logout_user
from flask_security import roles_accepted
from .models import CompanyClockInOptions, CompanyDetails, CompanyMemo, User,Departments,user_datastore,CompanyOffices,CompanyEmployeeSchedule,CompanyHolidays
from bson.objectid import ObjectId
from flask_security import roles_accepted,current_user
from config import settings
from .decorators import employees_required
from .company.model  import EmployeeDetails,EmployeeAttendance,EmployeeLeaveApprover,EmployeeLeaveRequest,EmployeeLeaveApplication
from .employee.model  import EmployeeBreakHistory
from datetime import timedelta

# from . import create_app
#image upload
# from werkzeug.utils import secure_filename
# import os
import datetime
main = Blueprint('main', __name__)
# app=create_app()


#User Index
@main.route('/')
def index():
    if current_user.is_authenticated:
        if( current_user.type == "admin"):
            return render_template('admin/index.html')
        if(current_user.type == "company"):
            company_details = CompanyDetails.objects(user_id=current_user.id).first()
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
            return render_template('company/index.html',company_details=company_details,td=todayDate)
        if(current_user.type == "employee"):
            if not current_user.confirmed:
                flash(Markup('You have not confirmed your email yet. Please check your inbox (and your spam folder) - you should have received an email with a confirmation link. Didn\'t get the email? <a href="/resend" class="text-primary alert-link">Resend Activation Mail</a>'),'danger')
            # check if employee has any schedule today if not get the default office location else take scheduled office location
            # Todo: Check if the other documents are expiring based on config sepcified in the alert settings
            notify_expiry_employee()
            # employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
            attendance_date = datetime.datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
            previous_attendance_date = (datetime.datetime.today() - timedelta(days=1)).replace(minute=0, hour=0, second=0, microsecond=0)
            employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
            todayDate = datetime.datetime.today()
           
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

            holiday_details = CompanyHolidays.objects(company_id=ObjectId(employee_details.company_id),occasion_date__gt=todayDate).order_by('occasion_date')

            existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from=attendance_date).first()
            upcoming_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from__gte=attendance_date)

            company_office_details = CompanyOffices.objects(company_id=employee_details.company_id,is_default=True).first()
            attendance_data = EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),attendance_date=attendance_date,employee_details_id=ObjectId(employee_details._id)).first()

            previos_day_attendance_data = EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),attendance_date=previous_attendance_date,employee_details_id=ObjectId(employee_details._id)).first()

            present_count = EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),attendance_status='present',employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
            late_count = EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),is_late=True,employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
            absent_count = EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),attendance_status='absent',employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
            monthly_att_data =EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).order_by('-attendance_date')
            break_data = EmployeeBreakHistory.objects(company_id=ObjectId(employee_details.company_id),attendance_date=attendance_date,employee_details_id=ObjectId(employee_details._id),already_ended=False).first()
            company_memos = CompanyMemo.objects(company_id=employee_details.company_id)
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
                    session["working_office"] = company_office_details._id
                    session["office_lat"] = company_office_details.location_latitude
                    session["office_lng"] = company_office_details.location_longitude
                    session["office_radius"] = company_office_details.location_radius
            else:
                if employee_details.employee_company_details.working_office:
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
            # session["already_checked_in"] = True if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
            # session["already_checked_out"] = True if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) or (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
            # session["checked_in_time"] = attendance_data.employee_check_in_at if (attendance_data and hasattr(attendance_data,'employee_check_in_at')) else False
            # session["checked_out_time"] = attendance_data.employee_check_out_at if (attendance_data and hasattr(attendance_data,'employee_check_out_at')) else ''
            session["is_approver"] = True if employee_details.is_approver else False
            session["is_super_approver"] = True if employee_details.is_super_leave_approver else False
            session["is_time_approver"] = True if employee_details.is_time_approver else False
            # session['is_absent'] = True if (hasattr(attendance_data,'attendance_status') and attendance_data.attendance_status == "absent") else False
            # session['on_break'] = True if (hasattr(attendance_data,'on_break') and attendance_data.on_break == True) else False
            session['home_allowed'] = True if employee_details.employee_company_details.home_option else False

            # session["office_lat"] = company_office_details.location_latitude
            # session["office_lng"] = company_office_details.location_longitude
            # session["office_radius"] = company_office_details.location_radius
            return render_template('employee/index.html',present_count=present_count,absent_count=absent_count,employee_attendance_data=monthly_att_data,holiday_details=holiday_details,todayDate=todayDate,break_data=break_data,clock_in_options=clock_in_options,late_count=late_count,company_memos=company_memos,upcoming_schedule=upcoming_schedule)
    else:
        return redirect(url_for('auth.login'))


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