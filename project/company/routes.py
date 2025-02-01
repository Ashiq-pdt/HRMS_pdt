# employees.py

from pprint import pprint
from flask import Blueprint, jsonify, render_template,request,flash,redirect,url_for,json,current_app,Response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required,logout_user
from flask_security import roles_accepted
from ..models import BankDetails, CompanyDetails, MutipleAcces,MultipleAccessEntry,CompanyExchange, CompanySif, CompanySignature, Role,User,Departments,user_datastore,WorkTimings,CompanyEmployeeSchedule,CompanyHolidays,CompanyOvertimePolicies,Designations\
,CompanyOffices,CompanyAdjustmentReasons,CompanyPayrollAdjustment,CompanyPayroll,CompanyClockInOptions,CompanyLeavePolicies,CompanyLeaveApprovers,CompanyTimeApprovers,CompanyRole\
,ActivityLog,CompanyMemo,SubCompanies,CompanyTimeOffAdjustment,SuperLeaveApprovers,CompanyBiometricDevice,CompanyBiometricAttendance
from bson.objectid import ObjectId
from flask_security import roles_accepted,current_user
from config import settings 
import uuid
from .model import BioMetricUserData, BioMetricActivity, RightPlanEmbeddedDocument, ValidEmbeddedDocument, EmployeeDetails,EmployeeCompanyDetails,EmployeeBankDetails,EmployeeDocuments,EmployeeAttendance, EmployeeLeaveApplication, EmployeeLeaveRequest,ScheduledBackgroundTask,CeleryTaskMeta\
    ,EmployeeLeavePolicies,EmployeeLeaveApprover,EmployeeTimeRequest,EmployeeLeaveAdjustment,EmployeeSifDetails,EmployeeReimbursement
from .. import create_app,db,create_celery_app
from werkzeug.utils import secure_filename
from types import SimpleNamespace
import os
from datetime import date, datetime, timedelta,time,timezone
from mongoengine.queryset.visitor import Q
from bson import json_util, ObjectId, DBRef
from bson.json_util import loads, dumps
import csv
import json
import time
import calendar
from flask import session
from os.path import join, getsize
import shutil
from flask_mail import Mail,Message
import string
import random
from ..token import generate_confirmation_token, confirm_token
from ..helper import create_activity_log
from .wps.WPS_Factory import WPS_Factory, WPS_Strategy
from .utils.attendance_related_functions import remove_leave_schedules, add_leave_schedules, \
                                                add_sundays_to_attendace, add_sundays_to_attendace_company_level, \
                                                add_workingdays_to_attendace, count_sundays, get_late_days_aggregate,\
                                                get_set_of_absent_days, get_late_and_absent, get_employee_schedule_statistics
from .wps.SIF_Model import SIF
from .wps.SCR_Models import SCR
from .wps.EDR_Models import EDR
from .wps.helper_functions import get_data_for_WPS_view, dereference_dbrefs
import jinja2,pdfkit,math
from prettytable import PrettyTable
import logging
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
import requests
from random import choices
import base64
from requests.auth import HTTPDigestAuth
from ..config.config_strategy import Config_Strategy
from dateutil.relativedelta import relativedelta
from datetime import date #Added By Ashiq Date : 19/sep/2024 Issues : Date formate 

company = Blueprint('company', __name__)
app=create_app()
celery = create_celery_app()
mail = Mail()

dynamic_config_strategy = Config_Strategy()
dynamic_config = dynamic_config_strategy.get_dynamic_config()
#Departments Page
@company.route('/departments')
@login_required
@roles_accepted('admin','company')
def departments():
    departments = CompanyDetails.objects(user_id=current_user.id).only('departments').first()
    return render_template('company/employee/departments.html', departments=departments)

@company.route('/designations')
@login_required
@roles_accepted('admin','company')
def designations():
    designations = CompanyDetails.objects(user_id=current_user.id).only('designations').first()
    return render_template('company/employee/designations.html', designations=designations)

#Add Departments
@company.route('/add/department', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def add_department():
    name = request.form.get('dept_name')
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    department_exist = list(filter(lambda x:(x['department_name'])==((name.upper()).strip()),company_details.departments))
    if not department_exist:
        company_details.departments.append(Departments(department_name=name.upper()))
        if company_details and company_details.save(): 
            flash('Department Added Successfully!', 'success')
            return redirect(url_for('company.departments'))
    else:
        flash('Department Already Exists!', 'danger')
        return redirect(url_for('company.departments'))

#Add Departments
@company.route('/add/designation', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def add_designation():
    name = request.form.get('designation_name')
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    designation_exist = list(filter(lambda x:(x['designation_name'])==((name.upper()).strip()),company_details.designations))
    if not designation_exist:
        company_details.designations.append(Designations(designation_name=name.upper()))
        if company_details and company_details.save(): 
            flash('Designation Added Successfully!', 'success')
            return redirect(url_for('company.designations'))
    else:
        flash('Designation Already Exists!', 'danger')
        return redirect(url_for('company.designations'))
    
#Update Department
@company.route('/update/department', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def update_department():
    name = request.form.get('dept_name')
    dept_id = request.form.get('dept_id')
    company_details =  CompanyDetails.objects(user_id=current_user.id).filter(departments__dep_id=dept_id).update(set__departments__S__department_name=(name.upper()).strip()) 
    if company_details: 
        flash('Department updated Successfully!', 'success')
        return redirect(url_for('company.departments'))
    
@company.route('/update/designation', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def update_designation():
    name = request.form.get('designation_name')
    designation_id = request.form.get('designation_id')
    company_details =  CompanyDetails.objects(user_id=current_user.id).filter(designations__designation_id=designation_id).update(set__designations__S__designation_name=(name.upper()).strip()) 
    if company_details: 
        flash('Designation updated Successfully!', 'success')
        return redirect(url_for('company.designations'))
    
#Delete User Profile
@company.route('/delete/department/<dep_id>')
@login_required
@roles_accepted('admin','company')
def delete_department(dep_id):
    # Delete reference employee object
    company_details=CompanyDetails.objects(user_id=current_user.id).update_one(pull__departments__dep_id=dep_id)
    if company_details: 
        flash('Department Deleted Successfully!', 'success')
        return redirect(url_for('company.departments'))
    
#Delete User Profile
@company.route('/delete/designation/<designation_id>')
@login_required
@roles_accepted('admin','company')
def delete_designation(designation_id):
    # Delete reference employee object
    company_details=CompanyDetails.objects(user_id=current_user.id).update_one(pull__designations__designation_id=designation_id)
    if company_details: 
        flash('Designation Deleted Successfully!', 'success')
        return redirect(url_for('company.designations'))


#Employee List Page
@company.route('/employees')
@login_required
# @roles_accepted('admin','company','peoplemanager')
def employees_list():


    multiple_access_company_id=session.get("multiple_access_company_id")
    print(f"    Company Name2: {multiple_access_company_id}")
    if multiple_access_company_id:
        company_id=multiple_access_company_id
    else :
        company_id=current_user.id

    employees = CompanyDetails.objects(user_id=company_id).only('employees','profile_pic').first()

    if not employees:
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        employees = CompanyDetails.objects(user_id=employee_details.company_id).only('employees','profile_pic').first()  
    return render_template('company/employee/list.html', employees=employees)

#Departments Page
@company.route('/add/employee')
@login_required
@roles_accepted('admin','company','peoplemanager')
def add_employee_details():

    multiple_access_company_id=session.get("multiple_access_company_id")
    print(f"    Company Name2: {multiple_access_company_id}")
    if multiple_access_company_id:
        company_id=multiple_access_company_id
    else :
        company_id=current_user.id

    departments = CompanyDetails.objects(user_id=company_id).only('departments','offices','worktimings','sub_companies','passport_expiry_alert','emirates_expiry_alert','visa_expiry_alert','offer_expiry_alert','other_expiry_alert').first()

    bank_details = BankDetails.objects(company_id=company_id)
    if not departments: 
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        departments = CompanyDetails.objects(user_id=employee_details.company_id).only('departments','offices','worktimings','sub_companies','passport_expiry_alert','emirates_expiry_alert','visa_expiry_alert','offer_expiry_alert','other_expiry_alert').first()  
    return render_template('company/employee/add_employee.html',departments=departments,bank_details=bank_details)

#Create New Employee
@company.route('/create/employee', methods=['GET','POST'])
@login_required
# @employees_required
@roles_accepted('admin','company','peoplemanager')
def add_employee():
    if request.method == 'POST':
        #Create Employee Login Details
        email = request.form.get('email')
        password = request.form.get('password')
        
       # First check if the user is present the db
        user = User.objects(email=email).first() # if this returns a user, then the email already exists in database

        if user: # if a user is found, we want to redirect back to add employee so user can try again  
            flash('Email address already exists')
            departments = CompanyDetails.objects(user_id=current_user.id).only('departments','offices','worktimings','sub_companies','passport_expiry_alert','emirates_expiry_alert','visa_expiry_alert','offer_expiry_alert','other_expiry_alert').first()
            bank_details = BankDetails.objects(company_id=current_user.id)
            if not departments: 
                employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
                departments = CompanyDetails.objects(user_id=employee_details.company_id).only('departments','offices','worktimings','sub_companies','passport_expiry_alert','emirates_expiry_alert','visa_expiry_alert','offer_expiry_alert','other_expiry_alert').first()  
            return render_template('company/employee/add_employee.html',departments=departments,bank_details=bank_details)
        
        # Create a user with employee role
        employee_user = user_datastore.create_user(email=email, password=generate_password_hash(password, method='sha256'),roles=['employee'],type='employee')
        
        # Create an Employee Record
        # Get Employee Details Records From Request
        if employee_user:
            file = request.files['profile_pic']
            profile_pic = upload_profile_pic(file)
            
            #Add Employee Personal Details
            employee_details = populate_employee_details(request,employee_user)
            new_employee = EmployeeDetails(**employee_details)
            new_employee.profile_pic = profile_pic
            employee_user.active = True if request.form.get('status') else False
            employee_user.save()
            #Add Employee Company Details
            employee_company_details = populate_employee_company_details(request)
            new_employee.employee_company_details = EmployeeCompanyDetails(**employee_company_details)
            
            # Set status 
            status = True if request.form.get('status') else False
            employee_user.update(set__active = status)
            #Add Employee Company Details
            
            employee_bank_details = populate_employee_bank_details(request)
            new_employee.employee_bank_details = EmployeeBankDetails(**employee_bank_details)
            employee_documents_details = []
            
            employee_sif_details = populate_employee_sif_details(request)
            new_employee.employee_sif_details = EmployeeSifDetails(**employee_sif_details)
            
            # Link to a company
            if current_user.type == "employee":
                employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
                new_employee.company_id = employee_details.company_id
                company_id = employee_details.company_id
            else:
                new_employee.company_id = current_user.id
                company_id = current_user.id
            
            departments = CompanyDetails.objects(user_id=company_id).only('company_name').first() or "null"
            
            #Add Documents if any
            files_len = len(request.files.getlist("document[]"))
            if files_len > 0:
                document_type_list = request.form.getlist('document_type[]')
                alert_before_list = request.form.getlist('alert_before[]')
                expiry_date_list = request.form.getlist('expiry_date[]')
                document_list = request.files.getlist("document[]")
                document_remarks = request.files.getlist("document_remark[]")
                employee_documents_details = []
                for item in range(0,files_len):
                    document_type = document_type_list[item]
                    document_name = document_list[item]
                    document_expiry_on = expiry_date_list[item]
                    days_before_expiry_alert = alert_before_list[item]
                    document_remark = document_remarks[item]
                    employee_documents_details.append(populate_employee_documents_details(document_type,document_name,document_expiry_on,days_before_expiry_alert,document_remark,departments.company_name))
            new_employee.documents = employee_documents_details
            
            #save the employee
            new_employee.save() 
            
            # todo: Create a record in Activity Log 
            activity_log = create_activity_log(request,current_user.id,company_id)    
            new_employee.update(push__activity_history=activity_log._id)  
            #push id to the list of employees field
            CompanyDetails.objects(user_id=company_id).update(push__employees=ObjectId(new_employee.id))
        
        flash('Employee Added Successfully!', 'success')
        return redirect(url_for('company.employees_list'))
    else:
        return render_template('company/employee/add_employee.html') 

def populate_employee_details(request, user):
    employee_details = {
        'user_id': user.id,
        'first_name' : request.form.get('first_name'),
        'last_name' : request.form.get('last_name'),
        'father_name' :  request.form.get('father_name'),
        'contact_no' : request.form.get('contact_no'),
        'emergency_contact_no_1' :  request.form.get('emergency_contact_no_1'),
        'emergency_contact_no_2' :  request.form.get('emergency_contact_no_2'),
        'dob' :  request.form.get('dob'),
        'gender' :  request.form.get('gender'),
        'marital_status' :  request.form.get('marital_status'),
        'blood_group' :  request.form.get('blood_group'),
        'present_address' :  request.form.get('present_address'),
        'permanent_address' :  request.form.get('permanent_address'),
        'personal_email' :  request.form.get('personal_email'),
        'email_notification' :  request.form.get('email_notification'),
        'passport_number' :  request.form.get('passport_number'),
        'emirates_id_no' :  request.form.get('emirates_id_no')
        }
    return employee_details

def populate_employee_company_details(request):
    if current_user.type == "employee":
            employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
            company_id = employee_details.company_id
    else:
        company_id = current_user.id
        
    default_work_office = CompanyOffices.objects(company_id=company_id,is_default=True).first()
    default_work_timing = WorkTimings.objects(company_id=company_id,is_default=True).first()
    
    employee_company_details = {
        'employee_id' : request.form.get('employee_id'),
        'department' : request.form.get('department').upper(),
        # 'working_office' : request.form.get('working_office') if request.form.get('working_office') else default_work_office._id,
        # 'work_timing' : request.form.get('work_timing') if request.form.get('work_timing') else default_work_timing._id,
        'designation' :  request.form.get('designation').upper(),
        'allow_outside_checkin' : True if request.form.get('office_clockins') == 'yes' else False,
        'date_of_joining' : request.form.get('date_of_joining'),
        'probation_end_date' : request.form.get('probation_end_date'),
        'date_of_resignation' :  request.form.get('date_of_resignation'),
        'date_of_termination' :  request.form.get('date_of_termination'),
        'credit_leaves' :  request.form.get('credit_leaves'),
        'home_option': False if request.form.get('wfh_option') == 'no' else True,
        'type' :  request.form.get('type'),
        'status' :  request.form.get('status')
        }
    if request.form.get('working_sub_company'):
        employee_company_details['working_sub_company'] = request.form.get('working_sub_company')
    
    if request.form.get('working_office'):
        employee_company_details['working_office'] = request.form.get('working_office')
    
    if request.form.get('work_timing'):
        employee_company_details['work_timing'] = request.form.get('work_timing')

    if request.form.get('type') == '0': #type = full time
        basic_salary = 0 if request.form.get('basic_salary') == '' else int(request.form.get('basic_salary'))
        housing_allowance = 0 if request.form.get('housing_allowance') == '' else int(request.form.get('housing_allowance'))
        travel_allowance = 0 if request.form.get('travel_allowance') == '' else int(request.form.get('travel_allowance'))
        fuel_allowances = 0 if request.form.get('fuel_allowance') == '' else int(request.form.get('fuel_allowance'))
        mobile_allowances = 0 if request.form.get('mobile_allowance') == '' else int(request.form.get('mobile_allowance'))
        medical_allowances = 0 if request.form.get('medical_allowance') == '' else int(request.form.get('medical_allowance'))
        other_allowances = 0 if request.form.get('other_allowances') == '' else int(request.form.get('other_allowances'))

        employee_company_details['basic_salary'] = basic_salary
        employee_company_details['housing_allowance'] = housing_allowance
        employee_company_details['travel_allowance'] = travel_allowance
        employee_company_details['fuel_allowance'] = fuel_allowances
        employee_company_details['mobile_allowance'] = mobile_allowances
        employee_company_details['medical_allowance'] = medical_allowances
        employee_company_details['other_allowances'] = other_allowances
        employee_company_details['total_salary'] = basic_salary+housing_allowance+travel_allowance+other_allowances+fuel_allowances+mobile_allowances+medical_allowances
    elif request.form.get('type') == '1': # type = part-time
        employee_company_details['basic_salary'] = 0
        employee_company_details['housing_allowance'] = 0
        employee_company_details['travel_allowance'] = 0
        employee_company_details['other_allowances'] = 0
        employee_company_details['fuel_allowance'] = 0
        employee_company_details['mobile_allowance'] = 0
        employee_company_details['medical_allowance'] = 0
        employee_company_details['total_salary'] = request.form.get('salary-per-hour')
    else:
        employee_company_details['basic_salary'] = 0
        employee_company_details['housing_allowance'] = 0
        employee_company_details['travel_allowance'] = 0
        employee_company_details['other_allowances'] = 0
        employee_company_details['fuel_allowance'] = 0
        employee_company_details['mobile_allowance'] = 0
        employee_company_details['medical_allowance'] = 0
        employee_company_details['total_salary'] = 0

    return employee_company_details

def populate_employee_bank_details(request):
    employee_bank_details = {
        'account_holder' : request.form.get('account_holder'),
        'account_no' : request.form.get('account_no'),
        'iban_no' : request.form.get('iban_no'),
        'swift_code' : request.form.get('swift_code'),
        'bank_name' :  request.form.get('bank_name'),
        'routing_code' :  request.form.get('routing_code'),
        'branch_location' : request.form.get('branch_location'),
        'ifsc_code' :  request.form.get('ifsc_code'),
        'tax_id' :  request.form.get('tax_id')
        }
    return employee_bank_details

    

def populate_employee_sif_details(request):
    company_exchange = request.form.get('company_exchange')
    employee_sif_details = {
        'employee_mol_no' : request.form.get('employee_mol_no'),
        'company_mol_no' : request.form.get('company_mol_no'),
        }
    if company_exchange:
        employee_sif_details['company_exchange'] = ObjectId(company_exchange)
    return employee_sif_details

def upload_profile_pic(file):
    fname=''
    file = request.files['profile_pic']
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = str.lower(os.path.splitext(filename)[1])
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in app.config['UPLOAD_EXTENSIONS']: 
            flash('Please insert image with desired format!')
            return redirect(url_for('company.add_employee'))
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    return fname;

def upload_document(file,company_name):
    fname=''
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = str.lower(os.path.splitext(filename)[1])
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in app.config['UPLOAD_DOCUMENT_EXTENSIONS']: 
            flash('Please insert document with desired format!')
            return redirect(url_for('company.add_employee'))
        file_path = app.config['UPLOAD_DOCUMENT_FOLDER'] + company_name.strip()
        # if not os.path.exists(app.config['UPLOAD_DOCUMENT_FOLDER']):
        #     os.makedirs(app.config['UPLOAD_DOCUMENT_FOLDER'])
        # file.save(os.path.join(app.config['UPLOAD_DOCUMENT_FOLDER'], fname))
        if not os.path.exists(file_path):
                os.makedirs(file_path)
        file.save(os.path.join(file_path, fname))
    return fname;

def upload_adjustment_document(file,company_name):
    fname=''
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = str.lower(os.path.splitext(filename)[1])
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in app.config['UPLOAD_DOCUMENT_EXTENSIONS']: 
            flash('Please insert document with desired format!')
            return redirect(url_for('company.add_employee'))
        file_path = app.config['UPLOAD_DOCUMENT_FOLDER'] + company_name.strip()+'/adjustments/'
        # if not os.path.exists(app.config['UPLOAD_DOCUMENT_FOLDER']):
        #     os.makedirs(app.config['UPLOAD_DOCUMENT_FOLDER'])
        # file.save(os.path.join(app.config['UPLOAD_DOCUMENT_FOLDER'], fname))
        if not os.path.exists(file_path):
                os.makedirs(file_path)
        file.save(os.path.join(file_path, fname))
    return fname;

def filter_active_employees(employees, start_date, sub_company):
    if sub_company:
        return [
            employee for employee in employees 
            if (employee.user_id.active_till is None or employee.user_id.active_till > start_date) 
            and hasattr(employee.user_id, 'active') and employee.user_id.active == True  # old one -->employee.is_active == True ->replace  and hasattr(employee.user_id, 'active') and employee.user_id.active == True  by ashiq
            and employee.employee_company_details is not None 
            and employee.employee_company_details.working_sub_company is not None 
            and employee.employee_company_details.working_sub_company.id == ObjectId(sub_company)
        ]
    else:
        return [
            employee for employee in employees 
                if (hasattr(employee.user_id, 'active') and employee.user_id.active == True) 
                # or
                # (hasattr(employee.user_id, 'active_till') and employee.user_id.active_till and employee.user_id.active_till >= start_date)
            ]


#Edit Employee Details  
@company.route('/edit/employee/<emp_id>', methods=['GET','POST'])
@login_required
@roles_accepted('admin','company','peoplemanager')
def edit_employee_details(emp_id):
    employee = EmployeeDetails.objects(_id=emp_id).first()
    
    start_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
    nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
    # subtracting the days from next month date to
    # get last date of current Month
    end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
    
    start_of_year = datetime(year=start_of_month.year, month=1, day=1)
    end_of_year = datetime(year=start_of_month.year, month=12, day=31)
    
    present_count = EmployeeAttendance.objects(company_id=ObjectId(employee.company_id),attendance_status='present',employee_details_id=ObjectId(employee._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
    late_count = EmployeeAttendance.objects(company_id=ObjectId(employee.company_id),is_late=True,employee_details_id=ObjectId(employee._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
    early_count = EmployeeAttendance.objects(company_id=ObjectId(employee.company_id),has_left_early=True,employee_details_id=ObjectId(employee._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
    absent_count = EmployeeAttendance.objects(company_id=ObjectId(employee.company_id),attendance_status='absent',employee_details_id=ObjectId(employee._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).count()
    
    year_attendance_count = EmployeeAttendance.objects(company_id=ObjectId(employee.company_id),attendance_status='present',employee_details_id=ObjectId(employee._id),attendance_date__gte=start_of_year,attendance_date__lte=end_of_year).count()
    year_absent_count = EmployeeAttendance.objects(company_id=ObjectId(employee.company_id),attendance_status='absent',employee_details_id=ObjectId(employee._id),attendance_date__gte=start_of_year,attendance_date__lte=end_of_year).count()
    year_late_count = EmployeeAttendance.objects(company_id=ObjectId(employee.company_id),is_late=True,employee_details_id=ObjectId(employee._id),attendance_date__gte=start_of_year,attendance_date__lte=end_of_year).count()
    
    statistics = {
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "early_count":early_count,
                "start_of_month":start_of_month,
                "end_of_the_month":end_of_the_month,
                "year_present":year_attendance_count,
                "year_absent_count":year_absent_count,
                "year_late_count":year_late_count,
                }
    
    if current_user.type == "employee":
            employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
            company_id = employee_details.company_id
    else:
        company_id = current_user.id
    departments = CompanyDetails.objects(user_id=company_id).only('departments','offices','leave_policies',
                                                                  'worktimings','company_exchanges','sub_companies','company_name',
                                                                  'passport_expiry_alert','emirates_expiry_alert','visa_expiry_alert',
                                                                  'offer_expiry_alert','other_expiry_alert').first()
    
    #bank_list = BankDetails.objects()
    bank_list = BankDetails.objects(company_id=current_user.id)

    if request.method == 'POST':
        new_employee = EmployeeDetails.objects(_id=emp_id)
        # Link to a company
        new_employee.company_id = company_id
        new_employee.update(company_id = company_id)
        #Add Employee Personal Details
        employee_details = populate_employee_details(request,employee.user_id)
        new_employee.update(**employee_details)
        file = request.files['profile_pic']
        if file:
            profile_pic = upload_profile_pic(file)
            new_employee.profile_pic = profile_pic 
        
        #Add Employee Company Details
        employee_company_details = populate_employee_company_details(request)
        new_employee.update(set__employee_company_details=employee_company_details)
        
        employee_user = User.objects(email=employee.user_id.email).first()
        status = True if request.form.get('status') else False
        if employee_user.active and not status :
            employee_user.update(set__active_till=datetime.now)
        employee_user.update(set__active = status)
        #Add Employee Company Details
        employee_bank_details = populate_employee_bank_details(request)
        new_employee.update(set__employee_bank_details=employee_bank_details)
        
        # add new docs
        files_len = len(request.files.getlist("document[]"))
        if files_len > 0:
            document_type_list = request.form.getlist('document_type[]')
            alert_before_list = request.form.getlist('alert_before[]')
            expiry_date_list = request.form.getlist('expiry_date[]')
            document_list = request.files.getlist("document[]")
            document_remarks = request.form.getlist("document_remark[]")
            
            for item in range(0,files_len):
                document_type = document_type_list[item]
                document_name = document_list[item]
                document_expiry_on = expiry_date_list[item]
                days_before_expiry_alert = alert_before_list[item]
                document_remark = document_remarks[item]
                new_employee.update(push__documents=populate_employee_documents_details(document_type,document_name,document_expiry_on,days_before_expiry_alert,document_remark,departments.company_name))
        
        #Add Employee SIF Config Details
        employee_sif_details = populate_employee_sif_details(request)
        new_employee.update(set__employee_sif_details=employee_sif_details)
        
        # todo: Create a record in Activity Log 
        activity_log = create_activity_log(request,current_user.id,company_id)    
        new_employee.update(push__activity_history=activity_log._id)
                  
        flash('Employee Updated Successfully!', 'success')
        return redirect(url_for('company.employees_list'))
    else:
        return render_template('company/employee/edit_employee.html', 
                               employee=employee,departments=departments,
                               statistics=statistics, bank_list = bank_list) 
    
def populate_employee_documents_details(document_type,document_name,document_expiry_on,days_before_expiry_alert,document_remark,company_name):
    document_name = upload_document(document_name,company_name)
    document_type = document_type
    if document_expiry_on:  
        document_expiry_on = datetime.strptime(document_expiry_on, '%d/%m/%Y')
    else:
        document_expiry_on = datetime.now
    days_before_expiry_alert = days_before_expiry_alert
    emp_doc = EmployeeDocuments(document_name=document_name,document_type=document_type,document_expiry_on=document_expiry_on,days_before_expiry_alert=days_before_expiry_alert,document_remark=document_remark)
    return emp_doc   

#Delete User Profile
@company.route('/delete/document/<doc_id>/employee/<emp_id>/')
@login_required
@roles_accepted('admin','company')
def delete_employee_document(doc_id,emp_id):
    employee_document= EmployeeDetails.objects(_id=emp_id).first()
    # e= EmployeeDetails.objects(_id=ObjectId(emp_id),documents___id=ObjectId(doc_id)).first()
    departments = CompanyDetails.objects(user_id=employee_document.company_id).only('company_name').first()
    if employee_document:
        for item in employee_document.documents:
            if item._id == ObjectId(doc_id):
                doc_name= app.config['UPLOAD_DOCUMENT_FOLDER']+departments.company_name.strip()+'/'+item.document_name
                if os.path.exists(doc_name):
                    EmployeeDetails.objects(_id=emp_id).update_one(pull__documents___id=doc_id)
                    os.remove(doc_name)
                    flash('Document Deleted Successfully!', 'success')
                    return redirect(url_for('company.edit_employee_details',emp_id=emp_id))
                else:
                    flash('Something went Wrong. Please try again.', 'danger')
                    return redirect(url_for('company.edit_employee_details',emp_id=emp_id))
    else:
        flash('Something went Wrong. Please try again.', 'danger')
        return redirect(url_for('company.edit_employee_details',emp_id=emp_id))
            
#Employee List Page
@company.route('/settings')
@login_required
@roles_accepted('admin','company')
def company_settings():
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    Employee_Details=EmployeeDetails.objects(company_id=current_user.id).all()
    departments = CompanyDetails.objects(user_id=current_user.id).only('departments','company_exchanges','sub_companies','offices','email_config','super_leave_approvers').first()
    leave_applications = EmployeeLeaveApplication.objects(company_id=current_user.id,leave_status="pending").only('company_approver')
    multiple_access_doc = MutipleAcces.objects(Main_company_id=current_user.id).all()
    banks_list = CompanyExchange.objects().all()
    for approver in company_details.leave_approvers:
        leave_applications = EmployeeLeaveApplication.objects(company_id=current_user.id,leave_status="pending",company_approver=approver._id).count()
        if leave_applications:
            approver.can_delete = False
            approver.pending_applications = leave_applications
        else:
            approver.can_delete = True
    
    return render_template('company/settings.html',company_details=company_details,departments=departments,leave_applications=leave_applications,
                           banks_list=banks_list,multiple_access_doc=multiple_access_doc,Employee_Details=Employee_Details)

@company.route('/update/settings/', methods=['POST'])
def update_settings():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            #Create Employee Login Details
            company_details.company_name = request.form.get('company_name')
            company_details.company_email = request.form.get('company_email')
            company_details.company_address = request.form.get('company_address')
            company_details.company_contact_no = request.form.get('company_contact_no')
            company_details.company_website = request.form.get('company_website')
            company_details.Currency = request.form.get('company_Currency')
            company_details.Timezone = request.form.get('company_Timezone')
            
            file = request.files['company_logo']
            if file:
                company_details.company_logo = upload_company_logo(file)
            # #push id to the list of employees field
            company_details.save()
            
            flash('Company Details Updated Successfully!', 'success')
            return redirect(url_for('company.company_settings'))
    else:
        return render_template('company/settings.html') 
    
@company.route('/update/emailsettings/', methods=['POST'])
def update_email_settings():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
                company_details_email_config = {
                'company_email_host' : request.form.get('email_host'),
                'company_email_port' : request.form.get('email_port'),
                'company_email_user' :  request.form.get('email_user'),
                'company_email_password' : request.form.get('email_password'),
                'company_email_name' : request.form.get('email_name'),
                'company_email_from' :  request.form.get('email_from')
                }
                company_details.update(set__email_config=company_details_email_config) 
            
                flash('Company Email Configuration Updated Successfully!', 'success')
                return redirect(url_for('company.company_settings'))
    else:
        return render_template('company/settings.html')

def upload_company_logo(file):
    fname=''
    file = request.files['company_logo']
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1]
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in app.config['UPLOAD_EXTENSIONS']: 
            flash('Please insert image with desired format!')
            return redirect(url_for('company.update_settings'))
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    return fname;

@company.route('/update/alerts/', methods=['POST'])
def update_alerts():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            #Create Employee Login Details
            company_details.passport_expiry_alert = request.form.get('passport_expiry_alert')
            company_details.emirates_expiry_alert = request.form.get('emirates_expiry_alert')
            company_details.visa_expiry_alert = request.form.get('visa_expiry_alert')
            company_details.labour_expiry_alert = request.form.get('labour_expiry_alert')
            company_details.other_expiry_alert = request.form.get('other_expiry_alert')
            company_details.save()
            flash('Company Alert Settings Updated Successfully!', 'success')
            return redirect(url_for('company.company_settings'))
    else:
        return render_template('company/settings.html') 
    
@company.route('/update/emailreceivers/', methods=['POST'])
def update_emailreceivers():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            #Create Employee Login Details
            company_details.receiver_emails = request.form.get('receiver_emails')
            company_details.save()
            flash('Company Alert Receiver Settings Updated Successfully!', 'success')
            return redirect(url_for('company.company_settings'))
    else:
        return render_template('company/settings.html')

#Employee List Page
@company.route('/documentdashboard', methods=['GET'])
@login_required
@roles_accepted('admin','company')
def document_dashboard():
    date_from = datetime.now() # The end date
    args = request.args
    no_of_days=args.get("no_of_days", default="30", type=str)
    if no_of_days == '120+':
        no_of_days = 365
    # date_till = date_from + timedelta(days=30)
    date_till = date_from + timedelta(days=int(no_of_days))
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    departments = CompanyDetails.objects(user_id=current_user.id).only('departments').first()

        
    return render_template('company/document_dashboard.html',date_till=date_till,date_from=date_from,departments=departments,company_details=company_details)

#Employee List Page
@company.route('/scheduleshift', methods=['GET'])
@login_required
@roles_accepted('admin','company')
def schedule_shift():
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    list = []
    for item in company_details.employees:
        list.append({'id':str(item._id),'department':item.employee_company_details.department,'title':item.first_name + ' ' +item.last_name})
    return render_template('company/schedule_shift.html',company_details=company_details,list=list)

@company.route('/createworktiming/settings/', methods=['POST'])
def create_work_timing():
    if request.method == 'POST':
        schedule_color = request.form.get('schedule_color')
        name = request.form.get("work_timing_name")
        is_day_off = request.form.get("is_day_off")
        office_start_at = request.form.get("office_start_at")
        office_end_at = request.form.get("office_end_at")
        # is_half_day = True if request.form['is_half_day") else False
        # is_half_day = True if request.form.get("is_half_day") == 'on' else False
        late_arrival__later_than =request.form.get("late_arrival__later_than")
        early_departure_earliar_than =request.form.get("early_departure_earliar_than")
        consider_absent_after =request.form.get("consider_absent_after")
        is_default = True if request.form.get("wt_is_default") else False
        minimum_ot = request.form.get("minimum_ot")
        
        
        # allow_breaks =request.form.get("allow_breaks")
        # c= datetime.strptime(office_start_at, '%I:%M %p')
        # out_of_office_check_in =True if request.form.get("out_of_office_check_in")== 'on' else False
        week_off=[]
        wo = request.form.getlist('week_offs[]')
        for item in wo:
            week_off.append(int(item))
        # validate the received values
        if is_day_off and name:
            work_timings =  WorkTimings(name=name,
                                    schedule_color='#808080',
                                    is_day_off=True,
                                    office_start_at='',
                                    office_end_at='',
                                    late_arrival__later_than='',
                                    early_departure_earliar_than='',
                                    consider_absent_after='',
                                    week_offs = '',
                                    company_id = current_user.id
                                    )
        
        elif name and office_start_at and office_end_at:
            total_working_hour = datetime.strptime(office_end_at, '%I:%M %p') - datetime.strptime(office_start_at, '%I:%M %p')  
            work_timings = WorkTimings(name=name,
                                    office_start_at=office_start_at,
                                    office_end_at=office_end_at,
                                    # is_half_day=is_half_day,
                                    late_arrival__later_than=late_arrival__later_than,
                                    early_departure_earliar_than=early_departure_earliar_than,
                                    consider_absent_after=consider_absent_after,
                                    # allow_breaks=allow_breaks,
                                    # out_of_office_check_in=out_of_office_check_in,
                                    schedule_color=schedule_color,
                                    week_offs = week_off,
                                    is_default=is_default,
                                    minimum_ot=minimum_ot,
                                    total_working_hour=str(total_working_hour),
                                    company_id = current_user.id
                                    )
        else:
            msg =  '{ "html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
        
        work_timings.save()
        update_details = CompanyDetails.objects(user_id=current_user.id).update(push__worktimings=work_timings.id)
        if update_details:
            details = WorkTimings.objects(company_id=current_user.id)
            js_data = loads(details.to_json())
            return dumps(js_data)
    else:
        return render_template('company/settings.html') 
    
@company.route('/editworktiming/settings/', methods=['POST'])
def update_work_timing():
    if request.method == 'POST':
        work_timing_id = request.form.get('edit_work_timing_id')
        work_timings_details = WorkTimings.objects(_id=ObjectId(work_timing_id))
        if work_timings_details:
            schedule_color = request.form.get('edit_schedule_color')
            name = request.form.get("edit_work_timing_name")
            is_day_off = request.form.get("edit_is_day_off")
            office_start_at = request.form.get("edit_office_start_at")
            office_end_at = request.form.get("edit_office_end_at")
            # is_half_day = True if request.form['is_half_day") else False
            # is_half_day = True if request.form.get("is_half_day") == 'on' else False
            late_arrival__later_than =request.form.get("edit_late_arrival__later_than")
            early_departure_earliar_than =request.form.get("edit_early_departure_earliar_than")
            consider_absent_after =request.form.get("edit_consider_absent_after")
            is_default = True if request.form.get("edit_wt_is_default") else False
            minimum_ot = request.form.get("edit_minimum_ot")
              
            # allow_breaks =request.form.get("allow_breaks")
            # c= datetime.strptime(office_start_at, '%I:%M %p')
            # out_of_office_check_in =True if request.form.get("out_of_office_check_in")== 'on' else False
            week_off=[]
            wo = request.form.getlist('edit_week_offs[]')
            for item in wo:
                week_off.append(int(item))
            # validate the received values
            if is_day_off and name:
                work_timings = work_timings_details.update(name=name,
                                        schedule_color='#808080',
                                        is_day_off=True,
                                        office_start_at='',
                                        office_end_at='',
                                        late_arrival_later_than='',
                                        early_departure_earliar_than='',
                                        consider_absent_after='',
                                        week_offs = '',
                                        company_id = current_user.id
                                        )
            
            elif name and office_start_at and office_end_at:
                total_working_hour = datetime.strptime(office_end_at, '%I:%M %p') - datetime.strptime(office_start_at, '%I:%M %p')  
                work_timings = work_timings_details.update(name=name,
                                        office_start_at=office_start_at,
                                        office_end_at=office_end_at,
                                        # is_half_day=is_half_day,
                                        is_day_off=is_day_off,
                                        late_arrival_later_than=late_arrival__later_than,
                                        early_departure_earliar_than=early_departure_earliar_than,
                                        consider_absent_after=consider_absent_after,
                                        # allow_breaks=allow_breaks,
                                        # out_of_office_check_in=out_of_office_check_in,
                                        schedule_color=schedule_color,
                                        week_offs = week_off,
                                        is_default=is_default,
                                        minimum_ot=minimum_ot,
                                        total_working_hour=str(total_working_hour),
                                        company_id = current_user.id
                                        )
            else:
                msg =  '{ "html":"<h3>Enter the required fields</h3>"}'
                msghtml = json.loads(msg)
                return msghtml["html"]
            
            if work_timings:
                details = WorkTimings.objects(company_id=current_user.id)
                js_data = loads(details.to_json())
                return dumps(js_data)
    else:
        return render_template('company/settings.html') 

#Delete Event
@company.route('/deleteworktiming/settings/', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def delete_work_timing():
    # Delete reference employee object
    work_timing_id = request.form.get('id')
    check_schdules = CompanyEmployeeSchedule.objects(work_timings=ObjectId(work_timing_id))
    
    if not check_schdules:
        status = WorkTimings.objects(_id=ObjectId(work_timing_id)).delete()
        company_details=CompanyDetails.objects(user_id=current_user.id).update_one(pull__worktimings=ObjectId(work_timing_id))
        if status and company_details:
            details = WorkTimings.objects(company_id=current_user.id)
            msg =  json.dumps({"status":"success","details":details.to_json()})
            msghtml = json.loads(msg)
            return msghtml
    # Failed
    msg =  json.dumps({"status":"failed"})
    msghtml = json.loads(msg)
    return msghtml

@company.route('/masscheduleshift', methods=['GET'])
@login_required
@roles_accepted('admin','company','shiftscheduler')
def mass_schedule_shift():
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year
    multiple_access_company_id=session.get("multiple_access_company_id")
    print(f"    Company Name2: {multiple_access_company_id}")
    if multiple_access_company_id:
        company_id=multiple_access_company_id
    else :
        company_id=current_user.id

    company_details = CompanyDetails.objects(user_id=company_id).first()

    if not company_details: 
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        #company_details = CompanyDetails.objects(user_id=employee_details.company_id).first()
        company_details = CompanyDetails.objects(user_id=company_id).first()     

    list = []
    eventList = []    

    # Resources List
    for item in company_details.employees:
        list.append({'id':str(item._id),'department':item.employee_company_details.department,'title':item.first_name + ' ' +item.last_name})

    for item in company_details.employee_schedules:

        # if item.schedule_from.month == current_month and item.schedule_from.year == current_year:
        # -> REMOVED THE ABOVE IF STATEMENT SO AS TO ALLOW EVENTS ACROSS ANY DATE TO APPEAR ON THE CALLENDER

        # check if item has worktiming atr

        if hasattr(item, 'work_timings'):
            eventList.append({'id':str(item.id),
                            'title':(item.leave_name if hasattr(item, 'is_leave') else item.work_timings.name + " (" + item.working_office.office_name +")"),
                            'start':str(item.schedule_from),
                            'end':str(item.schedule_till),
                            'resourceId':str(item.employee_id._id),
                            'display': 'auto',
                            'eventBackgroundColor':item.work_timings.schedule_color,
                            'color':item.work_timings.schedule_color,
                            'allDay':'true'}
                            )

    return render_template('company/mass_schedule_shift.html', company_details=company_details, list=list, eventList=eventList)
    # company_details = CompanyDetails.objects(user_id=current_user.id).first()
    # if not company_details: 
    #     employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    #     company_details = CompanyDetails.objects(user_id=employee_details.company_id).first()   
    # list = []
    # eventList = []    
    # # Resources List
    # for item in company_details.employees:
    #     list.append({'id':str(item._id),'department':item.employee_company_details.department,'title':item.first_name + ' ' +item.last_name})

    # for item in company_details.employee_schedules:
    #     eventList.append({'id':str(item._id),
    #                       'title':(item.leave_name if hasattr(item, 'is_leave') else item.work_timings.name + " (" + item.working_office.office_name +")"),
    #                       'start':str(item.schedule_from),
    #                       'end':str(item.schedule_till),
    #                       'resourceId':str(item.employee_id._id),
    #                       'display': 'auto',
    #                       'eventBackgroundColor':item.work_timings.schedule_color,
    #                       'color':item.work_timings.schedule_color,
    #                       'allDay':'true'}
    #                     )
    
    # return render_template('company/mass_schedule_shift.html',company_details=company_details,list=list,eventList=eventList)

@company.route('/masschedule/shifts/', methods=['POST'])
@login_required
@roles_accepted('admin','company','shiftscheduler')
def create_mass_schedule():
    if request.method == 'POST':
        eventList = []
        work_timing = request.form.get('work_timing')
        working_office = request.form.get('work_office')
        employee_ids = request.form.getlist("employee_ids[]")
        schedule_from = request.form.get('schedule_from')
        schedule_till = request.form.get("schedule_till")
        allow_outside_checkin = request.form.get('allow_outside_checkin')
        company_id = request.form.get('company_id')
        
        if work_timing and employee_ids and schedule_from and schedule_till and allow_outside_checkin:
            work_timing_details = WorkTimings.objects(_id=ObjectId(work_timing)).first()
            working_office_details = CompanyOffices.objects(_id=ObjectId(working_office)).first()
            
            for employee_id in employee_ids:
                start_date = datetime.strptime(schedule_from, '%Y-%m-%d')
                end_date = datetime.strptime(schedule_till, '%Y-%m-%d')
                day = timedelta(days=1)
                while start_date <= end_date:
                    is_already_scheduled = CompanyEmployeeSchedule.objects(employee_id=ObjectId(employee_id),schedule_from=start_date,schedule_till=start_date).first()
                    if not is_already_scheduled:
                        employee_schedule = CompanyEmployeeSchedule(company_id=ObjectId(company_id),
                                                    work_timings=ObjectId(work_timing),
                                                    working_office=ObjectId(working_office),
                                                    employee_id=ObjectId(employee_id),
                                                    schedule_from=start_date,
                                                    schedule_till=start_date,
                                                    allow_outside_checkin = allow_outside_checkin,
                        )
                        status = employee_schedule.save()
                        # Append to enent list for calendar
                        eventList.append({'id':str(employee_schedule._id),
                                'title':work_timing_details.name + " (" + working_office_details.office_name +")",
                                'start':str(employee_schedule.schedule_from),
                                'end':str(employee_schedule.schedule_till),
                                'resourceId':str(employee_id),
                                'display': 'auto',
                                'eventBackgroundColor':work_timing_details.schedule_color,
                                'color':work_timing_details.schedule_color,
                                'allDay':'true'}
                                )
                        update_details = CompanyDetails.objects(user_id=ObjectId(company_id)).update(push__employee_schedules=employee_schedule._id)
                    start_date = start_date + day
            # todo: Create a record in Activity Log 
            activity_log = create_activity_log(request,current_user.id,ObjectId(company_id))           
            if eventList:
                msg =  json.dumps({"status":"success","eventList":eventList})
                msghtml = json.loads(msg)
                return msghtml
            else:
                msg =  '{ "status":"fail","message":"*Same shift already scheduled for the day!"}'
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg =  '{ "status":"fail","message":"*Select Required Field"}'
            msghtml = json.loads(msg)
            return msghtml
    else:
        return render_template('company/masscheduleshift.html') 
    
@company.route('/deletemasschedule/shifts/', methods=['POST'])
def delete_mass_schedule():
    if request.method == 'POST':
        eventList = []
        employee_ids = request.form.getlist("employee_ids[]")
        schedule_from = request.form.get('schedule_from')
        schedule_till = request.form.get("schedule_till")
        company_id = request.form.get("company_id")
        
        if employee_ids and schedule_from and schedule_till:
            for employee_id in employee_ids:
                employee_schedule_details = CompanyEmployeeSchedule.objects(employee_id=ObjectId(employee_id),schedule_from__gte=schedule_from,schedule_till__lte=schedule_till)
                for item in employee_schedule_details:
                    eventList.append({'id':str(item._id)})
                    CompanyDetails.objects(user_id=item.employee_id.company_id).update(pull__employee_schedules=item._id)
                    item.delete()
            # todo: Create a record in Activity Log 
            activity_log = create_activity_log(request,current_user.id,ObjectId(company_id)) 
            if eventList:
                msg =  json.dumps({"status":"success","eventList":eventList})
                msghtml = json.loads(msg)
                return msghtml
            else:
                msg =  '{ "status":"fail","message":"*No shift scheduled for the day!"}'
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg =  '{ "status":"fail","message":"*Select Required Field"}'
            msghtml = json.loads(msg)
            return msghtml
    else:
        return render_template('company/masscheduleshift.html') 

@company.route('/update/generalsettings/', methods=['POST'])
def update_general_settings():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            working_hour = request.form.get('working_hour')
            working_days = [{"month":"january", "days": request.form.get('january')},
                            {"month":"february", "days": request.form.get('february')},    
                            {"month":"march", "days": request.form.get('march')},
                            {"month":"april", "days": request.form.get('april')},   
                            {"month":"may", "days": request.form.get('may')},
                            {"month":"june", "days": request.form.get('june')},   
                            {"month":"july", "days": request.form.get('july')},
                            {"month":"august", "days": request.form.get('august')},   
                            {"month":"september", "days": request.form.get('september')},
                            {"month":"october", "days": request.form.get('october')},   
                            {"month":"november", "days": request.form.get('november')},
                            {"month":"december", "days": request.form.get('december')},                        
                           ]
            company_details.daily_working_hour = working_hour
            company_details.working_days = working_days
            company_details.save()
            msg =  '{ "status":"success"}'
            msghtml = json.loads(msg)
            return msghtml
    else:
        return render_template('company/settings.html') 
    
@company.route('/holidays', methods=['GET'])
@login_required
@roles_accepted('admin','company')
def holidays():
    company_details = CompanyDetails.objects(user_id=current_user.id).only('holidays','overtime_policies').first()
    list = []
    for item in company_details.holidays:
        if item.is_recurring:
            list.append({'id':str(item._id),
                        'title':item.occasion_for ,
                        'rrule': {
                            'dtstart': str(item.occasion_date),
                            'freq': item.frequency
                        },   
                        'display': 'auto',
                        'color':'#34568B',
                        'allDay':'true'})
        else:
            list.append({'id':str(item._id),
                    'title':item.occasion_for ,
                    'start':str(item.occasion_date),
                    'end':str(item.occasion_date),
                    'display': 'auto',
                    'color':'rgba(255, 173, 0, 1)',
                    'allDay':'true'})
    return render_template('company/holidays.html',company_details=company_details,list=list)

@company.route('/create/holiday/', methods=['POST'])
def create_holiday():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            occasion_date = request.form.get('occasion_date')
            occasion_for = request.form.get('occasion_for')
            is_recurring = request.form.get('is_recurring')
            frequency = request.form.get('frequency')
            is_working_day = request.form.get('is_working_day')
            ot_policy=request.form.get('overtime_policy')
            
            comapany_holiday = CompanyHolidays(company_id=current_user.id,
                                               occasion_date=datetime.strptime(occasion_date, '%d-%m-%Y'),
                                               occasion_for=occasion_for
                                              )
            if is_working_day:
                comapany_holiday.is_working_day = True
                comapany_holiday.ot_policy = ObjectId(ot_policy)   
            if is_recurring:
                comapany_holiday.is_recurring = True
                comapany_holiday.frequency = frequency
                event = {'id':str(comapany_holiday._id),
                        'title':comapany_holiday.occasion_for ,
                        'rrule': {
                        'dtstart': str(comapany_holiday.occasion_date),
                        'freq': frequency
                         },
                        'display': 'auto',
                        'color':'#34568B',
                        'allDay':'true'}
            else:
                event = {'id':str(comapany_holiday._id),
                        'title':comapany_holiday.occasion_for ,
                        'start':str(comapany_holiday.occasion_date),
                        'end':str(comapany_holiday.occasion_date),
                        'display': 'auto',
                        'color':'rgba(255, 173, 0, 1)',
                        'allDay':'true'}
            comapany_holiday.save()  
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__holidays=comapany_holiday.id)
            if update_details:
                details = CompanyHolidays.objects(company_id=current_user.id)
                msg =  json.dumps({"status":"success","details":details.to_json(),"event":event})
                msghtml = json.loads(msg)
                return msghtml
    else:
        return render_template('company/holidays.html') 
    
#Delete Event
@company.route('/delete/holiday/', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def delete_holiday():
    # Delete reference employee object
    event_id = request.form.get('id')
    company_holiday = CompanyHolidays.objects(_id=ObjectId(event_id)).delete()
    company_details=CompanyDetails.objects(user_id=current_user.id).update_one(pull__holidays=ObjectId(event_id))
    
    if company_holiday and company_details:
        msg =  json.dumps({"status":"success"})
        msghtml = json.loads(msg)
        return msghtml

@company.route('/create/overtimepolicy/', methods=['POST'])
def create_overtime_policy():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            ot_policy_name = request.form.get('ot_policy_name')
            ot_policy_on = request.form.get('ot_policy_on')
            ot_policy_multiplier = request.form.get('ot_policy_multiplier')
            is_default = request.form.get('is_default')
            if ot_policy_name and ot_policy_on and ot_policy_multiplier:
                comapany_ot_policy = CompanyOvertimePolicies(company_id=current_user.id,
                                                ot_policy_name=ot_policy_name,
                                                ot_policy_on=ot_policy_on,
                                                ot_policy_multiplier=ot_policy_multiplier,
                                                is_default = is_default
                                                )
                comapany_ot_policy.save()  
                update_details = CompanyDetails.objects(user_id=current_user.id).update(push__overtime_policies=comapany_ot_policy.id)
                if update_details:
                    details = CompanyOvertimePolicies.objects(company_id=current_user.id)
                    msg =  json.dumps({"status":"success","details":details.to_json()})
                    msghtml = json.loads(msg)
                    return msghtml
            else:
                msg =  json.dumps({"status":"failed"})
                msghtml = json.loads(msg)
                return msghtml
    else:
        return render_template('company/settings.html') 

@company.route('/attendance', methods=['POST','GET'])
@login_required
@roles_accepted('admin','company')
def payroll(): 
    if request.method=="POST":
        start_of_month = datetime. strptime(request.form.get('selected_month'), '%Y-%m-%d')  if request.form.get('selected_month') else datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
    else:
        start_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
    nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
    # subtracting the days from next month date to
    # get last date of current Month
    end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
    no_of_days = int((end_of_the_month - start_of_month).days)+1
    
    employees_details = CompanyDetails.objects(user_id=ObjectId(current_user.id)).first()
    active_employees = list(filter(lambda x:(x['employee_company_details']['status'])==(True),employees_details.employees))
    attendance_data = []
    emp_attendance_data = []
    program_starts = time.time()
    for employee in active_employees:
        attendance_data = []
        employee_att = EmployeeAttendance.objects(employee_id=employee.employee_company_details.employee_id,company_id=current_user.id,attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).order_by('attendance_date')
        # attendance_data.append()
        # for current_date in range(int((end_of_the_month - start_of_month).days+1)):
        #     current_attendance_date = (start_of_month + timedelta(current_date)) 
        #     attendance_data.append(EmployeeAttendance.objects(employee_id=employee.employee_company_details.employee_id,attendance_date=current_attendance_date).first())
        emp_attendance_data.append({'emp_data':employee,'attendance_data':employee_att})
    now = time.time()
    print("It has been {0} seconds since the loop started".format(now - program_starts))
    return render_template('company/payroll.html',no_of_days=no_of_days,emp_attendance_data=emp_attendance_data,start_of_month=start_of_month)

#Employee List Page
@company.route('/compute/payroll', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def compute_payroll():
    attendance_data = []
    file = request.files.getlist('files')
    selected_month = request.form.get('selected_month')
    # Start Parsing through CSV File
    if file:
            filename = secure_filename(file[0].filename)
            fn = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            fname = fn+str(uuid.uuid4())+file_ext
            if file_ext not in app.config['UPLOAD_FILE_EXTENSIONS']: 
                flash('Please insert document with desired format!')
                return redirect(url_for('company.payroll'))
            if not os.path.exists(app.config['UPLOAD_FILE_FOLDER']):
                os.makedirs(app.config['UPLOAD_FILE_FOLDER'])
            document_path = os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname)
            file[0].save(os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname))
            
        # Dialect helps in grouping together many specific formatting patterns like delimiter, skipinitialspace, quoting, escapechar into a single dialect name.
            csv.register_dialect('myDialect',
                            skipinitialspace=True,
                            quoting=csv.QUOTE_ALL)
            
            with open(document_path, 'r') as file:
                csvreader = csv.DictReader(file, dialect='myDialect')
                # header = next(csvreader)
                for row in csvreader:
                    attendance_data.append(dict(row))
            os.remove(document_path)
    # End Parsing through CSV File
            # print(attendance_data)
    if attendance_data:
        result = compute_overall_data.delay(attendance_data,selected_month,str(current_user.id))
        if result:
            task_scheduled_details = ScheduledBackgroundTask(celery_task_id=result.id,company_id=current_user.id,task_type='compute_payroll',file_name=filename,uploaded_on=datetime.now())
            task_scheduled_details.save()
            # r = celery.AsyncResult(result.id)
            return "True"
    else:
        return "False"

def calculate_late_details(employee_check_in_time,current_working_day_check_in,hourly_rate):
    
    late_by_time = employee_check_in_time-current_working_day_check_in
    late_by_minutes = late_by_time.total_seconds()/60
    # Calculate Late amount to be deducted
    # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
    late_deduction_amount = (hourly_rate/60)*late_by_minutes
    
    return late_by_time,late_by_minutes,late_deduction_amount
    
def calculate_early_departure_details(employee_check_out_time,current_working_day_check_out,hourly_rate):
    
    early_by_time = current_working_day_check_out-employee_check_out_time
    early_by_minutes = early_by_time.total_seconds()/60
    # Calculate Late amount to be deducted
    # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
    early_deduction_amount = (hourly_rate/60)*early_by_minutes
    
    return early_by_time,early_by_minutes,early_deduction_amount

def compute_attendance_data(work_timings,check_in_time,check_out_time,current_attendance_date,employee_data,is_non_working_day,overtime_type,current_user):
    work_timings = WorkTimings.objects(_id=ObjectId(work_timings)).first()
    e_id = employee_data
    employee_data = EmployeeDetails.objects(employee_company_details__employee_id=e_id).first()
    
    attendance_date = datetime.strptime(current_attendance_date, '%d/%m/%Y')
    employee_check_in_time = datetime.strptime(check_in_time, '%d/%m/%Y %I:%M %p')
    employee_check_out_time = datetime.strptime(check_out_time, '%d/%m/%Y %I:%M %p')
    
    # Need to calculate these
    scs = time.process_time()
    late_deduction_amount = 0
    extra_ot_amount = 0
    early_deduction_amount = 0  
    gross_pay_per_day = 0 
    # Check if the existing attendance record exists if yes the delete and add new record
    data_available = EmployeeAttendance.objects(company_id=ObjectId(current_user),attendance_date=attendance_date,employee_details_id=employee_data._id)
    if data_available:
        data_available.delete()
    
    employee_attendance = EmployeeAttendance()
    employee_attendance.employee_id = employee_data.employee_company_details.employee_id
    employee_attendance.employee_details_id = employee_data._id
    employee_attendance.attendance_date = attendance_date
    employee_attendance.company_id = ObjectId(current_user)
    
    # Wages Details
    monthly_salary = employee_data.employee_company_details.total_salary if employee_data.employee_company_details.total_salary else 0
    
    employee_attendance.monthly_salary = monthly_salary
    
    if employee_data.employee_company_details.type == '0': # if the employee salary type is 0 i.e Full-time employee 
        basic_monthly_salary = employee_data.employee_company_details.basic_salary if employee_data.employee_company_details.basic_salary else 0
    elif employee_data.employee_company_details.type == '1':  # if the employee salary type is 1 i.e Part-time employee
        basic_monthly_salary = employee_data.employee_company_details.total_salary if employee_data.employee_company_details.total_salary else 0
    else:  # if the employee salary type is not selected
        basic_monthly_salary = 0
    
    employee_attendance.basic_monthly_salary = basic_monthly_salary
        
    current_month = datetime(attendance_date.year, attendance_date.month, 1).strftime('%B')
    
    employee_attendance.attendance_month = str(current_month.lower())
    
    calendar_working_days = CompanyDetails.objects(user_id=ObjectId(current_user)).only('working_days','daily_working_hour').first()
    # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
    working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))
    
    employee_attendance.working_days = working_days

    no_of_working_days = int(working_days[0]['days']) if working_days else 30 # By Default Set to 30 Days
    daily_salary = int(monthly_salary)/no_of_working_days # Get the no of working days in current monthly calendar
    daily_basic_salary = int(basic_monthly_salary)/no_of_working_days # Get the no of working days in current monthly calendar
    daily_working_hour = calendar_working_days.daily_working_hour if calendar_working_days.daily_working_hour else 8 # Default Set to 8 Working Hours
    hourly_rate = float(daily_salary)/float(daily_working_hour)
    basic_hourly_rate = float(daily_basic_salary)/float(daily_working_hour)
    
    employee_attendance.daily_salary = daily_salary
    employee_attendance.daily_basic_salary = daily_basic_salary
    employee_attendance.daily_working_hour = daily_working_hour
    employee_attendance.hourly_rate = hourly_rate
    employee_attendance.basic_hourly_rate = basic_hourly_rate

    # Wages Details End
    if not is_non_working_day:
        office_start_at = work_timings.office_start_at 
        office_end_at = work_timings.office_end_at
        late_arrival_later_than = work_timings.late_arrival_later_than
        early_departure_earliar_than = work_timings.early_departure_earliar_than
        
        default_checkout_time =  datetime.strptime(office_end_at, '%I:%M %p')
        default_checkin_time = datetime.strptime(office_start_at, '%I:%M %p')   
        

        # This Condition will check if the checkout time is next day of the checkin time 
        if "AM" in office_end_at:
            # Checkout without Grace
            current_check_out_date = datetime.combine(attendance_date.date()+timedelta(days=1),default_checkout_time.time())
            # Checkout with Grace
            current_working_day_check_out = current_check_out_date + timedelta(minutes=-int(early_departure_earliar_than))
            # Checkin without Grace
            current_check_in_date = datetime.combine(attendance_date.date(),default_checkin_time.time())
            # Checkin with Grace
            current_working_day_check_in = current_check_in_date + timedelta(minutes=int(late_arrival_later_than))
        else:
            # Checkout without Grace
            current_check_out_date = datetime.combine(attendance_date.date(),default_checkout_time.time())
            # Checkout with Grace
            current_working_day_check_out = current_check_out_date + timedelta(minutes=-int(early_departure_earliar_than))
            # Checkin without Grace
            current_check_in_date = datetime.combine(attendance_date.date(),default_checkin_time.time())
            # Checkin with Grace
            current_working_day_check_in = current_check_in_date + timedelta(minutes=int(late_arrival_later_than)) 
        
        # check if the employee checked_in early if he/she is early set checkin time at current day work_start time 
        employee_check_in_time = current_check_in_date if employee_check_in_time <= current_check_in_date else employee_check_in_time
        # compute ot,late,early and gp 
        total_hrs_worked = employee_check_out_time-employee_check_in_time
        employee_attendance.total_hrs_worked = str(total_hrs_worked)
            
        employee_attendance.employee_check_out_at = employee_check_out_time
        employee_attendance.current_working_day_check_out = str(current_working_day_check_out)
        employee_attendance.employee_check_in_at = employee_check_in_time
        employee_attendance.current_working_day_check_in = str(current_working_day_check_in)
            
        total_working_hour = current_check_out_date - current_check_in_date
        minimum_ot = int(work_timings.minimum_ot) if work_timings.minimum_ot else 0
        employee_attendance.minimum_ot = str(minimum_ot)
        # Calculate Late
        if employee_check_in_time > current_working_day_check_in:
            # Means Employee is Late 
            late_by_time,late_by_minutes,late_deduction_amount = calculate_late_details(employee_check_in_time,current_check_in_date,hourly_rate)
            employee_attendance.late_by_minutes = str(late_by_minutes)
            employee_attendance.late_deduction_amount = late_deduction_amount
            employee_attendance.late_approved = True
            employee_attendance.has_late_deduction = True
            
            
        # This check if the employee has went early after allotted the grace time of checking out
        if employee_check_out_time < current_working_day_check_out:
            early_by_time,early_by_minutes,early_deduction_amount = calculate_early_departure_details(employee_check_out_time,current_check_out_date,hourly_rate)
            employee_attendance.early_by_minutes = str(early_by_minutes)
            employee_attendance.early_deduction_amount = early_deduction_amount
            employee_attendance.early_approved = True
            employee_attendance.has_early_deduction = True
    else:
        total_hrs_worked = employee_check_out_time-employee_check_in_time
        overtime_minutes = total_hrs_worked.total_seconds()/60
        minimum_ot = 0
        employee_attendance.total_hrs_worked = str(total_hrs_worked)
        employee_attendance.employee_check_out_at = employee_check_out_time
        employee_attendance.current_working_day_check_out = ""
        employee_attendance.employee_check_in_at = employee_check_in_time
        employee_attendance.current_working_day_check_in = ""   
    # This condition will assume that the employee has done the overtime
    # overtime will be calculated only for full time employees
    if employee_data.employee_company_details.type == '0':
        if is_non_working_day:
            overtime_minutes = total_hrs_worked.total_seconds()/60
        else:
            overtime_hours = total_hrs_worked-total_working_hour
            overtime_minutes = overtime_hours.total_seconds()/60 if overtime_hours else 0
                
        if overtime_minutes >= minimum_ot:
            overtime_policy = CompanyOvertimePolicies.objects(company_id=ObjectId(current_user),ot_policy_name=overtime_type).first()
            if overtime_policy:
                employee_attendance.has_overtime = True
                employee_attendance.ot_by_minutes = str(overtime_minutes)
                employee_attendance.ot_policy_multiplier = overtime_policy.ot_policy_multiplier
                employee_attendance.ot_type = overtime_policy.ot_policy_name
                employee_attendance.ot_policy_on = overtime_policy.ot_policy_on
                employee_attendance.ot_approved = True
                
            # Calculate Overtime amount to be increased/included
            # Desired Formula for Calculating the Overtime is Overtime = (Hourly Rate*ot_multiplier)/60 x Total No of Minutes of OT (Convert hours to minutes)
                if(overtime_policy.ot_policy_on == 'basic_salary'):
                    extra_ot_amount = ((basic_hourly_rate*float(overtime_policy.ot_policy_multiplier))/60)*overtime_minutes
                else:
                    extra_ot_amount = ((hourly_rate*float(overtime_policy.ot_policy_multiplier))/60)*overtime_minutes
                employee_attendance.ot_amount = extra_ot_amount
        # else:
        #     print('Not Valid O.T')
    if is_non_working_day:
        gross_pay_per_day = extra_ot_amount
    else:
       gross_pay_per_day = daily_salary + extra_ot_amount - late_deduction_amount - early_deduction_amount
    
    employee_attendance.attendance_status = "present"
    employee_attendance.gross_pay_per_day = gross_pay_per_day
    
    # employee_attendance.save()
    # return {"status": True} 
    # print('After Computation : ',time.process_time() - scs)
    return employee_attendance

def compute_absent_data(current_attendance_date,employee_id,current_user):
    gross_pay_per_day = 0 
    attendance_date = datetime.strptime(current_attendance_date, '%d/%m/%Y')
    default_work_timings = WorkTimings.objects(company_id=ObjectId(current_user),is_default=True).first()
    e_id = employee_id
    employee = EmployeeDetails.objects(employee_company_details__employee_id=e_id).first()
    is_holiday = CompanyHolidays.objects(company_id=ObjectId(current_user),occasion_date=attendance_date,is_working_day=False).first()
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee._id,schedule_from=attendance_date).first()
    current_week_day = attendance_date.weekday()
    is_non_working_day = True if (is_holiday or current_week_day in default_work_timings.week_offs or (existing_schedule.work_timings.is_day_off if existing_schedule else False )) else False
    leave_type='absent'
    if is_non_working_day:
        leave_type = 'holiday' if is_holiday else 'dayoff'
    data_available = EmployeeAttendance.objects(company_id=ObjectId(current_user),attendance_date=attendance_date,employee_details_id=employee._id)
    if data_available:
        data_available.delete()
    
    employee_attendance = EmployeeAttendance()    
    employee_attendance.employee_id = employee.employee_company_details.employee_id
    employee_attendance.employee_details_id = employee._id
    employee_attendance.attendance_date = attendance_date
    employee_attendance.company_id = ObjectId(current_user)
    
        # Wages Details
    monthly_salary = employee.employee_company_details.total_salary if employee.employee_company_details.total_salary else 0
    
    employee_attendance.monthly_salary = monthly_salary
    
    if employee.employee_company_details.type == '0': # if the employee salary type is 0 i.e Full-time employee 
        basic_monthly_salary = employee.employee_company_details.basic_salary if employee.employee_company_details.basic_salary else 0
    elif employee.employee_company_details.type == '1':  # if the employee salary type is 1 i.e Part-time employee
        basic_monthly_salary = employee.employee_company_details.total_salary if employee.employee_company_details.total_salary else 0
    else:  # if the employee salary type is not selected
        basic_monthly_salary = 0
    
    employee_attendance.basic_monthly_salary = basic_monthly_salary
        
    current_month = datetime(attendance_date.year, attendance_date.month, 1).strftime('%B')
    
    employee_attendance.attendance_month = str(current_month.lower())
    
    calendar_working_days = CompanyDetails.objects(user_id=ObjectId(current_user)).only('working_days','daily_working_hour').first()
    # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
    working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))
    
    employee_attendance.working_days = working_days

    no_of_working_days = int(working_days[0]['days']) if working_days else 30 # By Default Set to 30 Days
    daily_salary = int(monthly_salary)/no_of_working_days # Get the no of working days in current monthly calendar
    daily_basic_salary = int(basic_monthly_salary)/no_of_working_days # Get the no of working days in current monthly calendar
    daily_working_hour = calendar_working_days.daily_working_hour if calendar_working_days.daily_working_hour else 8 # Default Set to 8 Working Hours
    hourly_rate = float(daily_salary)/float(daily_working_hour)
    basic_hourly_rate = float(daily_basic_salary)/float(daily_working_hour)
    
    employee_attendance.daily_salary = daily_salary
    employee_attendance.daily_basic_salary = daily_basic_salary
    employee_attendance.daily_working_hour = daily_working_hour
    employee_attendance.hourly_rate = hourly_rate
    employee_attendance.basic_hourly_rate = basic_hourly_rate

    # Wages Details End
    if leave_type == 'holiday':
        employee_attendance.attendance_status = "holiday"
        employee_attendance.occasion_for = is_holiday.occasion_for
        employee_attendance.gross_pay_per_day = 0
        
    elif leave_type == 'dayoff':
        employee_attendance.attendance_status = "dayoff"
        employee_attendance.gross_pay_per_day = 0
    else:
        if employee.employee_company_details.type == '1':
            employee_attendance.attendance_status = "no-attendance"
        else:    
            employee_attendance.attendance_status = "absent"
        employee_attendance.gross_pay_per_day = 0
    
    # employee_attendance.gross_pay_per_day = daily_salary
    # employee_attendance.save()
    # return {"status": True} 
    return employee_attendance

@celery.task(track_started = True,result_extended=True,name='Compute-Attendance-Data')
def compute_overall_data(attendance_data,selected_month,current_user):
    if attendance_data:
        start_of_month = datetime.strptime(selected_month, '%Y-%m-%d')
        nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
        # subtracting the days from next month date to
        # get last date of current Month
        end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
        
        bulk_attendance_data = []
        
        for current_date in range(int((end_of_the_month - start_of_month).days+1)):
            attendance_date = start_of_month + timedelta(current_date)
            current_attendance_date = (start_of_month + timedelta(current_date)).strftime('%d/%m/%Y')
            # Get all active employees
            employees_details = CompanyDetails.objects(user_id=ObjectId(current_user)).first()
            active_employees = list(filter(lambda x:x['employee_company_details']['status']==True,employees_details.employees))
            for employee in active_employees:
                # Check if the attendance data exist in the file
                attendance_data_exist = list(filter(lambda x:(x['employee_id'],x['attendance_date'])==(employee.employee_company_details.employee_id,current_attendance_date),attendance_data))
                if attendance_data_exist and not employee.employee_company_details.type == '1':
                    check_in_at = datetime.strptime(attendance_data_exist[0]['check_in_time_1'], '%d/%m/%Y %I:%M %p')
                    check_out_at = datetime.strptime(attendance_data_exist[0]['check_out_time_1'], '%d/%m/%Y %I:%M %p')
                    # Continue with algorithm on 26th May
                    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee._id,schedule_from=attendance_date).first()
                    if existing_schedule:
                        is_holiday = CompanyHolidays.objects(company_id=ObjectId(current_user),occasion_date=attendance_date,is_working_day=False).first()
                        is_non_working_day = True if (is_holiday or existing_schedule.work_timings.is_day_off) else False
                        overtime_type='extended'
                        if is_non_working_day:
                            overtime_type = 'holiday' if is_holiday else 'dayoff'
                        wt = str(existing_schedule.work_timings._id)
                        bulk_attendance_data.append(compute_attendance_data(wt,attendance_data_exist[0]['check_in_time_1'],attendance_data_exist[0]['check_out_time_1'],current_attendance_date,employee.employee_company_details.employee_id,is_non_working_day,overtime_type,current_user))
                    else:
                        # Default Work Timings
                        default_work_timings = WorkTimings.objects(company_id=ObjectId(current_user),is_default=True).first()
                        if default_work_timings:
                            is_holiday = CompanyHolidays.objects(company_id=ObjectId(current_user),occasion_date=attendance_date,is_working_day=False).first()
                            current_week_day = attendance_date.weekday()
                            is_non_working_day = True if (is_holiday or current_week_day in default_work_timings.week_offs) else False
                            overtime_type='extended'
                            if is_non_working_day:
                                overtime_type = 'holiday' if is_holiday else 'dayoff'
                           
                            bulk_attendance_data.append(compute_attendance_data(str(default_work_timings._id),attendance_data_exist[0]['check_in_time_1'],attendance_data_exist[0]['check_out_time_1'],current_attendance_date,employee.employee_company_details.employee_id,is_non_working_day,overtime_type,current_user))
                # if the employee works only parttime/by hour
                elif attendance_data_exist and employee.employee_company_details.type == '1':
                    data_available = EmployeeAttendance.objects(company_id=ObjectId(current_user),attendance_date=attendance_date,employee_details_id=employee._id)
                    if data_available:
                        data_available.delete()
                    
                    employee_attendance = EmployeeAttendance()
                    employee_attendance.employee_id = employee.employee_company_details.employee_id
                    employee_attendance.employee_details_id = employee._id
                    employee_attendance.attendance_date = attendance_date
                    employee_attendance.company_id = ObjectId(current_user)
                    
                    employee_check_in_time = datetime.strptime(attendance_data_exist[0]['check_in_time_1'], '%d/%m/%Y %I:%M %p')
                    employee_check_out_time = datetime.strptime(attendance_data_exist[0]['check_out_time_1'], '%d/%m/%Y %I:%M %p')
    
                    total_hrs_worked = employee_check_out_time-employee_check_in_time
                    basic_monthly_salary = employee.employee_company_details.total_salary if employee.employee_company_details.total_salary else 0
                    employee_attendance.total_hrs_worked = str(total_hrs_worked)
                    employee_attendance.employee_check_in_at = employee_check_in_time
                    employee_attendance.employee_check_out_at = employee_check_out_time
                    employee_attendance.basic_hourly_rate = basic_monthly_salary
                    working_minutes = total_hrs_worked.total_seconds()/60
                    
                    gross_pay_per_day = (float(basic_monthly_salary)/60)*float(working_minutes)
                    employee_attendance.attendance_status = "present"
                    employee_attendance.gross_pay_per_day = gross_pay_per_day
                    bulk_attendance_data.append(employee_attendance)
                else:
                    # if not employee.employee_company_details.type == '1':
                    bulk_attendance_data.append(compute_absent_data(current_attendance_date,employee.employee_company_details.employee_id,current_user))
        
        save_data = EmployeeAttendance.objects.insert(bulk_attendance_data)    
        if save_data:
            return True
    else:
    # empty File
      return False;
  
@company.route('/queuestatus', methods=['GET'])
def get_queue_status():
    scheduled_queue = ScheduledBackgroundTask.objects(company_id=current_user.id,task_type="compute_payroll")
    if scheduled_queue:
        details = {}
        data = []
        for item in scheduled_queue:
            details = {
                'file_name' : item.file_name,
                'uploaded_on' : str(item.uploaded_on) if item.uploaded_on else '',
                'status' :  item.celery_task_id.status if item.celery_task_id.status else 'STARTED',
                'task_id' : str(item.celery_task_id.id) if item.celery_task_id.id else '',
            }
            data.append(details)
        msg =  json.dumps({"status":"success","details":data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml
    
@company.route('/payslipdetails', methods=['GET'])
def get_payslip_details():
    employee_id = request.args.get('employee_id')
    selected_month =  datetime.strptime(request.args.get('selected_month'), '%Y-%m-%d')  if request.args.get('selected_month') else datetime.today().replace(day=1)
    # selected_year =  datetime. strptime(request.args.get('selected_year'), '%Y-%m-%d')  if request.args.get('selected_year') else datetime.now()
    
    start_of_month = selected_month.replace(year=selected_month.year)
    end_of_month = selected_month.replace(day = calendar.monthrange(start_of_month.year, start_of_month.month)[1])
    
    gp_with_deduction = EmployeeAttendance.objects(company_id=current_user.id,employee_details_id=ObjectId(employee_id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_month).sum('gross_pay_per_day')
    ot_amount = EmployeeAttendance.objects(company_id=current_user.id,employee_details_id=ObjectId(employee_id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_month).sum('ot_amount')
    late_deduction_amount = EmployeeAttendance.objects(company_id=current_user.id,employee_details_id=ObjectId(employee_id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_month).sum('late_deduction_amount')
    early_deduction_amount = EmployeeAttendance.objects(company_id=current_user.id,employee_details_id=ObjectId(employee_id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_month).sum('early_deduction_amount')
    
    # print(gp_with_deduction)
    employee_details = EmployeeDetails.objects(_id=ObjectId(employee_id)).exclude('employee_bank_details','documents').first()
    
    if gp_with_deduction > 0 and employee_details:
        employee_data = loads(employee_details.to_json())
        js_data = {
                'status': 'success',
                'employee_details':employee_data,
                'gross_pay':gp_with_deduction,
                'ot_amount':ot_amount,
                'late_deduction_amount':late_deduction_amount,
                'early_deduction_amount':early_deduction_amount
                }
    else:
        employee_details = EmployeeDetails.objects(_id=ObjectId(employee_id)).exclude('employee_bank_details','documents').first()
        employee_data = loads(employee_details.to_json())
        js_data = {
                'status': 'failed',
                'employee_details':employee_data,
                }
    return dumps(js_data)

#Employee List Page
@company.route('/massupload')
@login_required
@roles_accepted('admin','company')
def mass_upload():
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    departments = CompanyDetails.objects(user_id=current_user.id).only('departments','employees').first()
    return render_template('company/mass_upload.html', company_details=company_details,departments=departments)

#Employee List Page
@company.route('/bulk/addemployees', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def bulk_upload_employees():
    employee_data = []
    file = request.files.getlist('files')
    file_path = request.form.get('file_path')
    # Start Parsing through CSV File
    if file:
            filename = secure_filename(file[0].filename)
            fn = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            fname = fn+str(uuid.uuid4())+file_ext
            if file_ext not in app.config['UPLOAD_FILE_EXTENSIONS']: 
                flash('Please insert document with desired format!')
                return redirect(url_for('company.payroll'))
            if not os.path.exists(app.config['UPLOAD_FILE_FOLDER']):
                os.makedirs(app.config['UPLOAD_FILE_FOLDER'])
            document_path = os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname)
            file[0].save(os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname))
            
        # Dialect helps in grouping together many specific formatting patterns like delimiter, skipinitialspace, quoting, escapechar into a single dialect name.
            csv.register_dialect('myDialect',
                            skipinitialspace=True,
                            quoting=csv.QUOTE_ALL)
            
            with open(document_path, 'r') as file:
                csvreader = csv.DictReader(file, dialect='myDialect')
                for row in csvreader:
                    employee_data.append(dict(row))
            os.remove(document_path)
            
            if employee_data:
               #result = add_bulk_employees.delay(employee_data,str(current_user.id),file_path)
                result = add_bulk_employees(employee_data,str(current_user.id),file_path)
                return "True"
            # if result:
            #    message = 'Bulk Employee Creation with uploaded file named ' + filename + ' has '
            #    task_scheduled_details = ScheduledBackgroundTask(celery_task_id=result.id,company_id=current_user.id,task_type='employee_data',message=message,file_name=filename,uploaded_on=datetime.now())
            #    task_scheduled_details.save()
            #    return "True"
    else:
        return "False"

#Create New Employees
#@celery.task(track_started = True,result_extended=True,name='Employee-Data')
def add_bulk_employees(employee_data,current_user,file_path):
    new_users = []
    for employee in employee_data:
        email_flag = False
        # First check if the user is present the db
        user = User.objects(email=employee['email']).first() # if this returns a user, then the email already exists in database

        if user: # if a user is found, we want to redirect back to add employee so user can try again  
            employee_user = user
        # Create a user with employee role
        else:
            if employee['email'] != '':
                # Create a 10 digit random password using choices and send it via email
                # sending an activation email
                email_flag = True #means need to send an email for this user since this is a new user
                # Generate a random password
                #S = 10  # number of characters in the string.  
                # call random.choices() string module to find the string in Uppercase + numeric data.  
                # random_password = ''.join(random.choices(string.ascii_uppercase + string.digits, k = S))  
                random_password = "password"  
                employee_user = user_datastore.create_user(email=employee['email'], password=generate_password_hash(random_password, method='sha256'),roles=['employee'],type='employee')
                if employee_user:
                    new_users.append({"email":employee['email'],"password":random_password})
            else:
                employee_user = False
        # if only user is created    
        if employee_user:    
            new_employee = EmployeeDetails.objects(user_id=employee_user.id,company_id=ObjectId(current_user)).first()
            if new_employee:
            # Create an Employee Record
            #Add Employee Personal Details
                employee_details = populate_bulk_employee_details(employee,employee_user)
                new_employee.update(**employee_details)
                 # Link to a company
                new_employee.update(company_id = ObjectId(current_user))           
                #Add Employee Company Details
                employee_company_details = populate_bulk_employee_company_details(employee,current_user)
                new_employee.update(set__employee_company_details=employee_company_details)
                #Add Employee Company Details
                employee_bank_details = populate_bulk_employee_bank_details(employee)
                new_employee.update(set__employee_bank_details=employee_bank_details)
                
                #Add Employee Company Details
                employee_sif_details = populate_bulk_employee_sif_details(employee,current_user)
                new_employee.update(set__employee_sif_details=employee_sif_details)
                
                
            else:
                employee_details = populate_bulk_employee_details(employee,employee_user)
                new_employee = EmployeeDetails(**employee_details)
                            
                #Add Employee Company Details
                employee_company_details = populate_bulk_employee_company_details(employee,current_user)
                new_employee.employee_company_details = EmployeeCompanyDetails(**employee_company_details)
                
                employee_bank_details = populate_bulk_employee_bank_details(employee)
                new_employee.employee_bank_details = EmployeeBankDetails(**employee_bank_details)
                
                #Add Employee Company Details
                employee_sif_details = populate_bulk_employee_sif_details(employee,current_user)
                new_employee.employee_sif_details = EmployeeSifDetails(**employee_sif_details)
                
                new_employee.company_id = ObjectId(current_user)
            
                new_employee.save()   
            departments = CompanyDetails.objects(user_id=current_user).only('company_name').first()
            if file_path:
                    new_employee.update(push__documents=populate_bulk_employee_documents_details('id_proof',employee['emirates_file_name'],employee['emirates_expiry_date'],employee['emirates_id_no'],file_path,departments.company_name))
                    new_employee.update(push__documents=populate_bulk_employee_documents_details('passport_copy',employee['passport_file_name'],employee['passport_expiry_date'],employee['passport_no'],file_path,departments.company_name))
                    
            # # #push id to the list of employees field
            save_data = CompanyDetails.objects(user_id=current_user).update(add_to_set__employees=ObjectId(new_employee.id))
    # send Bulk emails with celery
    
    # send_bulk_emails.delay(new_users,str(current_user)    
    
    # continue tomorrow
    
    return True

def populate_bulk_employee_details(employee_data, user):
    employee_details = {
        'user_id': user.id,
        'first_name' : employee_data['first_name'],
        'personal_email' : employee_data['email'],
        'last_name' : employee_data['last_name'],
        'contact_no' : employee_data['contact_no'],
        'dob' : employee_data['dob'],
        'emergency_contact_no_1' : employee_data['emergency_conatct_no'],
        'emergency_contact_no_2' : employee_data['contact_person'],
        'gender' :  'male' if employee_data['gender'] == 'M' else 'female',
        'marital_status' :  'single' if employee_data['marital_status'] == 'Single' else 'married',
        'passport_number' : employee_data['passport_no'],
        'emirates_id_no' : employee_data['emirates_id_no'],
        }
    return employee_details

def populate_bulk_employee_company_details(employee_data,company_id):
    company_details = CompanyDetails.objects(user_id=company_id).only('departments','designations').first()
    department_exist = list(filter(lambda x:(x['department_name'])==((employee_data['department'].upper()).strip()),company_details.departments))
    designation_exist = list(filter(lambda x:(x['designation_name'])==((employee_data['designation'].upper()).strip()),company_details.designations))
    default_work_office = CompanyOffices.objects(company_id=company_id,is_default=True).first()
    default_work_timing = WorkTimings.objects(company_id=company_id,is_default=True).first()
    
    if not department_exist and employee_data['department'] != '':
        company_details.departments.append(Departments(department_name=(employee_data['department'].upper()).strip()))
        company_details.save()
    
    if not designation_exist and employee_data['designation'] != '':
        company_details.designations.append(Designations(designation_name=(employee_data['designation'].upper()).strip()))
        company_details.save()
        
    employee_company_details = {
        'employee_id' : employee_data['employee_id'],
        'department' : (employee_data['department'].upper()).strip(),
        'designation' :  (employee_data['designation'].upper()).strip(),
        'date_of_joining' :  employee_data['date_of_joining'],
        'type' : '0' if employee_data['salary_type'] == 'Full-time' else '1',
        #'working_office':default_work_office._id if default_work_office else '',
        #'work_timing' : default_work_timing._id if default_work_timing else '',
        'status' :  True,
        }
    # if default_work_timing:
    #     employee_company_details['working_sub_company'] = default_work_timing._id
    # if employee_data['working_sub_company']:
    #     # Todo: Check if the sub company config is created; if not create a new config with the name
    #     sub_company_exists = SubCompanies.objects(company_id=company_id,company_name=employee_data['working_sub_company']).first() or SubCompanies(company_id=company_id,company_name=employee_data['working_sub_company']).save()
    #     CompanyDetails.objects(user_id=company_id).update(add_to_set__sub_companies=sub_company_exists._id)
    #     employee_company_details['working_sub_company'] = sub_company_exists._id
    
    if employee_data['salary_type'] == 'Full-time': #type = full time
        basic_salary = 0 if employee_data['basic_salary'] == '' else int(employee_data['basic_salary'])
        housing_allowance = 0 if employee_data['housing_allowance'] == '' else int(employee_data['housing_allowance'])
        travel_allowance = 0 if employee_data['travel_allowance'] == '' else int(employee_data['travel_allowance'])
        other_allowances = 0 if employee_data['other_allowance'] == '' else int(employee_data['other_allowance'])

        employee_company_details['basic_salary'] = basic_salary
        employee_company_details['housing_allowance'] = housing_allowance
        employee_company_details['travel_allowance'] = travel_allowance
        employee_company_details['other_allowances'] = other_allowances
        employee_company_details['total_salary'] = basic_salary+housing_allowance+travel_allowance+other_allowances
    elif employee_data['salary_type'] == 'Part-time': # type = part-time
        employee_company_details['basic_salary'] = 0
        employee_company_details['housing_allowance'] = 0
        employee_company_details['travel_allowance'] = 0
        employee_company_details['other_allowances'] = 0
        employee_company_details['total_salary'] = employee_data['hourly_rate']
    else:
        employee_company_details['basic_salary'] = 0
        employee_company_details['housing_allowance'] = 0
        employee_company_details['travel_allowance'] = 0
        employee_company_details['other_allowances'] = 0
        employee_company_details['total_salary'] = 0

    return employee_company_details

def populate_bulk_employee_bank_details(employee_data):
    employee_bank_details = {
        'account_holder' : employee_data['bank_account_name'],
        'account_no' : employee_data['account_no'],
        'bank_name' :  employee_data['bank_name'],
        'branch_location' : employee_data['branch_location'],
        'iban_no' :  employee_data['iban_no'],
        'routing_code' : employee_data['routing_code']
        }
    return employee_bank_details

def populate_bulk_employee_sif_details(employee_data,company_id):
    exchange_name = employee_data['exchange_name']
    employee_sif_details = {
        'employee_mol_no' : employee_data['employee_mol_no'],
        'company_mol_no' : employee_data['company_mol_no'],
        }
    if exchange_name:
        exchange_exist = CompanyExchange.objects(exchange_name=exchange_name).first() or CompanyExchange(company_id=company_id,exchange_name=exchange_name).save()
        CompanyDetails.objects(user_id=company_id).update(add_to_set__company_exchanges=exchange_exist._id)
        employee_sif_details['company_exchange'] = exchange_exist._id
    return employee_sif_details

def populate_bulk_employee_documents_details(document_type,document_name,document_expiry_on,document_no,file_path,company_name):
    document_name = upload_bulk_document(document_name,file_path,company_name)
    document_type = document_type
    if document_expiry_on:  
        document_expiry_on = datetime.strptime(document_expiry_on, '%d/%m/%Y')
    else:
        document_expiry_on = datetime.now
    emp_doc = EmployeeDocuments(document_name=document_name,document_type=document_type,document_expiry_on=document_expiry_on,document_no=document_no)
    return emp_doc   

def upload_bulk_document(file_name,file_path,company_name):
    fname=""
    for root, dirs,files in os.walk(file_path):
        # file_name = employee['emirates_file_name']
        if file_name in files:
            filename = secure_filename(file_name)
            fn = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            fname = fn+str(uuid.uuid4())+file_ext
            file_path = app.config['UPLOAD_DOCUMENT_FOLDER']+company_name.strip()
            # if not os.path.exists(app.config['UPLOAD_DOCUMENT_FOLDER']):
            #     os.makedirs(app.config['UPLOAD_DOCUMENT_FOLDER'])
            # document_path = os.path.join(app.config['UPLOAD_DOCUMENT_FOLDER'], fname)
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            document_path = os.path.join(file_path, fname)
            src = root+'/'+filename
            shutil.copyfile(src, document_path)
    return fname;

@celery.task(track_started = True,result_extended=True,name='Employee-Confirmation-Email')
def send_bulk_emails(new_users,company_id):
    
    app = create_app()  # create the Flask app
    mail = Mail(current_app)  # initialize Flask-Mail with default email server details

    company_details = CompanyDetails.objects(user_id=ObjectId(company_id)).only('email_config').first()
    if company_details.email_config:
        mail_server = company_details.email_config.company_email_host
        mail_port = company_details.email_config.company_email_port
        mail_use_tls = company_details.email_config.company_email_tls
        mail_username = company_details.email_config.company_email_user
        mail_password = company_details.email_config.company_email_password
       
        current_app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USERNAME=mail_username,
        MAIL_PASSWORD=mail_password
        )
        
        mail.init_app(current_app)
    else:
        mail_server = app.config['MAIL_SERVER']
        mail_port = app.config['MAIL_PORT']
        mail_use_tls = app.config['MAIL_USE_TLS']
        mail_username = app.config['MAIL_USERNAME']
        mail_password = app.config['MAIL_PASSWORD']
        mail.init_app(app)

    with current_app.app_context():
        for user in new_users:
            token = generate_confirmation_token(user['email'])
            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            html = render_template('email/employee_confirmation.html', confirm_url=confirm_url,current_password=user['password'])
            msg = Message('Please confirm your email! | Cubes HRMS', sender = ("Cubes HRMS",app.config['MAIL_USERNAME']), recipients = [user['email']])
            msg.html = html
            mail.send(msg)

    return True 
    
@company.route('/resend')
@login_required
def resend_confirmation():
    if current_user.email:
        send_resend_emails.delay(current_user.email,str(current_user.id))
        flash('Confirmation Link has been sent your registered email.','success')
    return redirect(url_for('main.index'))

@celery.task(track_started = True,result_extended=True,name='Employee-ReConfirmation-Email')
def send_resend_emails(email,company_id):
    app = create_app()  # create the Flask app
    mail = Mail(current_app)  # initialize Flask-Mail with default email server details
    # Get Leave Application Details
    company_details = CompanyDetails.objects(user_id=ObjectId(company_id)).only('email_config').first()
    if not company_details:
        employee_details = employee_details = EmployeeDetails.objects(user_id=ObjectId(company_id)).only('company_id').first()
        company_details = CompanyDetails.objects(user_id=employee_details.company_id).only('email_config').first()
    if company_details.email_config:
        mail_server = company_details.email_config.company_email_host
        mail_port = company_details.email_config.company_email_port
        mail_use_tls = company_details.email_config.company_email_tls
        mail_username = company_details.email_config.company_email_user
        mail_password = company_details.email_config.company_email_password
       
        current_app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USERNAME=mail_username,
        MAIL_PASSWORD=mail_password
        )
        
        mail.init_app(current_app)
    else:
        mail_server = app.config['MAIL_SERVER']
        mail_port = app.config['MAIL_PORT']
        mail_use_tls = app.config['MAIL_USE_TLS']
        mail_username = app.config['MAIL_USERNAME']
        mail_password = app.config['MAIL_PASSWORD']
        mail.init_app(app)

    with current_app.app_context():
        token = generate_confirmation_token(email)
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        html = render_template('email/confirmation.html', confirm_url=confirm_url)
        msg = Message('Please confirm your email! | Cubes HRMS', sender = ("Cubes HRMS",app.config['MAIL_USERNAME']), recipients = [email])
        msg.html = html
        mail.send(msg)
        return True
    
    
    # token = generate_confirmation_token(email)
    # confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    # html = render_template('email/confirmation.html', confirm_url=confirm_url)
    # msg = Message('Please confirm your email!', sender = app.config['MAIL_USERNAME'], recipients = [email])
    # msg.html = html
    # mail.send(msg)
    # return True
@company.route('/attendancereport',methods=["GET","POST"])
@login_required
@roles_accepted('admin','company','supervisor','attendancemanager')
def attendance_report():

    multiple_access_company_id=session.get("multiple_access_company_id")
    print(f"    Company Name2: {multiple_access_company_id}")
    if multiple_access_company_id:
        company_id=multiple_access_company_id
    else :
        company_id=current_user.id

    company_employees = CompanyDetails.objects(user_id=company_id).only('employees','clock_in_options').first()
    company_id = company_id
    start_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)

    if not company_employees: 
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        company_employees = CompanyDetails.objects(user_id=employee_details.company_id).only('employees','clock_in_options').first()   
        company_id = employee_details.company_id


    # company_employees['employees'] = list(filter(lambda x: x['user_id']['active_till'] is None or x['user_id']['active_till'] > start_date, company_employees['employees']))
    company_employees['employees'] = list(filter(lambda x: x['user_id']['active'], company_employees['employees']))

    if request.method=="POST":
        company_employees = CompanyDetails.objects(user_id=company_id).only('employees','clock_in_options').first()

        daterange = request.form.get('daterange')
        attendance_from, attendance_to = [date.strip() for date in daterange.split('-')]
        employee_details_id = request.form.get('employee_id')
        start_date = datetime. strptime(attendance_from, '%d/%m/%Y')
        end_date = datetime. strptime(attendance_to, '%d/%m/%Y')

        # company_employees['employees'] = list(filter(lambda x: x['user_id']['active_till'] is None or x['user_id']['active_till'] > start_date, company_employees['employees']))
        company_employees['employees'] = list(filter(lambda x: x['user_id']['active'], company_employees['employees']))
	

        total_hrs_worked = timedelta()
        data = []
        
        if employee_details_id:
            employee_attendance = EmployeeAttendance.objects(company_id=company_id,attendance_date__gte=start_date,attendance_date__lte=end_date,employee_details_id=ObjectId(employee_details_id))
            for i in employee_attendance:
                if "total_hrs_worked" in i:
                      # Splitting days and time components
                        parts = i.total_hrs_worked.split(', ')
                        if len(parts) == 2:  # If days component is present
                            days = int(parts[0].split()[0])  # Extracting the number of days
                            time_str = parts[1]  # Extracting the time component
                        else:
                            days = 0
                            time_str = parts[0]

                        # Parsing hours, minutes, and seconds
                        (h, m, s) = time_str.split(':')

                        # Calculate total hours worked excluding the day component
                        d = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
                        
                        # Adding the calculated timedelta to total_hrs_worked
                        total_hrs_worked += d
                    # (h, m, s) = i.total_hrs_worked.split(':')
                    # d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))
                    # total_hrs_worked += d
            for item in employee_attendance:
                sum_of_break = 0
                if item.break_history:
                    for bh in item.break_history:
                        if bh.already_ended:
                            sum_of_break += bh.break_difference

                if "total_hrs_worked" in item:
                    # Splitting days and time components
                    parts = item.total_hrs_worked.split(', ')
                    if len(parts) == 2:  # If days component is present
                        days = int(parts[0].split()[0])  # Extracting the number of days
                        time_str = parts[1]  # Extracting the time component
                    else:
                        days = 0
                        time_str = parts[0]

                    # Parsing hours, minutes, and seconds
                    (h, m, s) = time_str.split(':')

                    if sum_of_break > 0:
                        # Subtracting break time from total time
                        item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s)) - timedelta(minutes=int(sum_of_break))
                    else:
                        item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
                # if "total_hrs_worked" in item:
                #     (h, m, s) = item.total_hrs_worked.split(':')
                #     if sum_of_break > 0:
                #         item.total_hr_worked_excluding = d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))-timedelta(minutes=int(sum_of_break))
                #     else:
                #         item.total_hr_worked_excluding = d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))
                    
                data.append(item)
            employee_details = EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
            if dynamic_config.env not in ["hrm", "hrm-debug"]:

                data = add_sundays_to_attendace(data, start_date, end_date, employee_details)
            
                # Sorting the result list by 'attendance_date'
            data.sort(key=lambda x: x['attendance_date'])

            return render_template('company/attendance_report.html',employee_attendance=data,employees_details=company_employees,selected_emp=ObjectId(employee_details_id),start=start_date,end=end_date,total_hrs_worked=chop_microseconds(total_hrs_worked))
                    
        else:
            employee_attendance = EmployeeAttendance.objects(company_id=company_id,attendance_date__gte=start_date,attendance_date__lte=end_date)
            for item in employee_attendance:
                sum_of_break = 0
                if item.break_history:
                    for bh in item.break_history:
                        if bh.already_ended:
                            sum_of_break += bh.break_difference

                if "total_hrs_worked" in item:
                    # Splitting days and time components
                    parts = item.total_hrs_worked.split(', ')
                    if len(parts) == 2:  # If days component is present
                        days = int(parts[0].split()[0])  # Extracting the number of days
                        time_str = parts[1]  # Extracting the time component
                    else:
                        days = 0
                        time_str = parts[0]

                    # Parsing hours, minutes, and seconds
                    (h, m, s) = time_str.split(':')

                    if sum_of_break > 0:
                        # Subtracting break time from total time
                        item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s)) - timedelta(minutes=int(sum_of_break))
                    else:
                        item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
                # if "total_hrs_worked" in item:
                #     (h, m, s) = item.total_hrs_worked.split(':')
                #     if sum_of_break > 0:
                #         item.total_hr_worked_excluding = d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))-timedelta(minutes=int(sum_of_break))
                #     else:
                #         item.total_hr_worked_excluding = d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))
                data.append(item)

            if dynamic_config.env not in ['hrm', "hrm-debug"]:

                data = add_sundays_to_attendace_company_level(data, start_date, end_date, company_employees['employees'])

                        
                # Sorting the result list by 'attendance_date'
            data.sort(key=lambda x: x['attendance_date'])

            return render_template('company/attendance_report.html',employee_attendance=data,employees_details=company_employees,start=start_date,end=end_date)
        # attendance_date = datetime. strptime(request.form.get('attendance_range[0]'), '%d/%m/%Y')  if request.form.get('attendance_date') else datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
    else:
        # company_employees = CompanyDetails.objects(user_id=company_id).only('employees','clock_in_options').first()
        end_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
        employee_attendance = EmployeeAttendance.objects(company_id=company_id,attendance_date__gte=start_date,attendance_date__lte=end_date)
        data =[]
        for item in employee_attendance:
            sum_of_break = 0
            if item.break_history:
                for bh in item.break_history:
                    if bh.already_ended:
                        sum_of_break += bh.break_difference

            if "total_hrs_worked" in item:
                    # Splitting days and time components
                    parts = item.total_hrs_worked.split(', ')
                    if len(parts) == 2:  # If days component is present
                        days = int(parts[0].split()[0])  # Extracting the number of days
                        time_str = parts[1]  # Extracting the time component
                    else:
                        days = 0
                        time_str = parts[0]

                    # Parsing hours, minutes, and seconds
                    (h, m, s) = time_str.split(':')

                    if sum_of_break > 0:
                        # Subtracting break time from total time
                        item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s)) - timedelta(minutes=int(sum_of_break))
                    else:
                        item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
            # if "total_hrs_worked" in item:
            #     (h, m, s) = item.total_hrs_worked.split(':')
            #     if sum_of_break > 0:
            #         item.total_hr_worked_excluding = d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))-timedelta(minutes=int(sum_of_break))
            #     else:
            #         item.total_hr_worked_excluding = d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))
                    
            data.append(item)        
        return render_template('company/attendance_report.html',employee_attendance=data,employees_details=company_employees,start=start_date,end=end_date)


def get_company_employees(current_user):
    return CompanyDetails.objects(user_id=current_user.id).only('employees', 'clock_in_options').first()

def parse_date(date_str, format='%d/%m/%Y'):
    return datetime.strptime(date_str, format)



def calculate_total_hours_worked(employee_attendance):
    total_hrs_worked = timedelta()
    for record in employee_attendance:
        if "total_hrs_worked" in record:
            parts = record.total_hrs_worked.split(', ')
            days = int(parts[0].split()[0]) if len(parts) == 2 else 0
            time_str = parts[1] if len(parts) == 2 else parts[0]
            h, m, s = time_str.split(':')
            total_hrs_worked += timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
    return total_hrs_worked

def process_employee_attendance(employee_attendance):
    processed_data = []
    for item in employee_attendance:
        sum_of_break = 0
        if item.break_history:
            for bh in item.break_history:
                if bh.already_ended:
                    sum_of_break += bh.break_difference
        if "total_hrs_worked" in item:
            parts = item.total_hrs_worked.split(', ')
            if len(parts) == 2:
                days = int(parts[0].split()[0])
                time_str = parts[1]
            else:
                days = 0
                time_str = parts[0]
            h, m, s = time_str.split(':')
            if sum_of_break > 0:
                item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s)) - timedelta(minutes=int(sum_of_break))
            else:
                item.total_hr_worked_excluding = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
        processed_data.append(item)
    return processed_data


@company.route('/attendancesummary',methods=["GET", "POST"])
@login_required
@roles_accepted('admin', 'company', 'supervisor', 'attendancemanager')
def attendance_summary():
    company_id = current_user.id
    company_employees = get_company_employees(current_user)
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    end_date = datetime.today().replace(minute=0, hour=0, second=0, microsecond=0)
    start_date = datetime.today().replace(minute=0, hour=0, second=0, microsecond=0)
    sub_company = None

    if request.method == 'POST':
        daterange = request.form.get('daterange')
        attendance_from, attendance_to = [date.strip() for date in daterange.split('-')]
        start_date = datetime.strptime(attendance_from, '%d/%m/%Y')
        end_date = datetime.strptime(attendance_to, '%d/%m/%Y')
        sub_company = request.form.get('sub_company')

    # Get holidays within the date range
    holidays = CompanyHolidays.objects(occasion_date__gte=start_date, occasion_date__lte=end_date)
    all_holidays = holidays.count()  # Get the number of holidays

    # Calculate Sundays and total days
    no_day_offs, total_days = count_sundays(start_date, end_date)

    company_employees['employees'] = filter_active_employees(company_employees['employees'], start_date, sub_company)
    attendance_data = []
    stats = get_employee_schedule_statistics(company_id, start_date, end_date, dynamic_config.env)

    for record in stats:
        absent = total_days - (record['absent_count'] + record['present_count'] + no_day_offs + all_holidays)
        attendance_data.append({
            'employee_details': EmployeeDetails.objects(_id=ObjectId(record['_id'])).first(),
            'attendance': total_days - no_day_offs - all_holidays,
            "late_count": record['late_count'],
            'days_present': record['present_count'],
            'days_absent': absent,
            'days_on_leave': record['absent_count']
        })

    return render_template(
        'company/attendance_summary.html',
        attendance_data=attendance_data,
        employees_details=company_employees,
        start=start_date,
        end=end_date,
        company_details=company_details,
        selected_sub_company=sub_company
    )


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@company.route('/resend_password/<emp_id>')
@login_required
def resend_password(emp_id):
    logger.info(f"Resend password requested for employee ID: {emp_id}")
    employee = EmployeeDetails.objects(_id=emp_id).first()
    if employee:
        user_exists = User.objects(_id=employee.user_id.id).first()
        if user_exists:
            new_user = []
            S = 10  # number of characters in the string.
            # call random.choices() string module to find the string in Uppercase + numeric data.
            random_password = ''.join(choices(string.ascii_uppercase + string.digits, k=S))
            user_exists.update(password=generate_password_hash(random_password, method='sha256'))
            new_user.append({"email": user_exists.email, "password": random_password})
            company_id = employee.company_id
            logger.info(f"New password generated and updated for user ID: {user_exists.id}")
            send_password_emails(new_user, str(company_id))
            logger.info(f"Password email sent to the user with email: {user_exists.email}")
            flash('Confirmation link has been sent to your registered email.', 'success')
        else:
            logger.warning(f"User not found for employee ID: {emp_id}")
            flash('User not found.', 'danger')
    else:
        logger.warning(f"Employee not found with ID: {emp_id}")
        flash('Employee not found.', 'danger')
    return redirect(url_for('company.employees_list'))


# @celery.task(track_started=True, result_extended=True, name='Hr-Resend-Password-Email')
def send_password_emails(new_users, company_id):
    logger.info("Starting send_password_emails task")
    app = create_app()  # create the Flask app
    mail = Mail(current_app)  # initialize Flask-Mail with default email server details

    company_details = CompanyDetails.objects(user_id=ObjectId(company_id)).only('email_config').first()
    if company_details.email_config:
        mail_server = company_details.email_config.company_email_host
        mail_port = company_details.email_config.company_email_port
        mail_use_tls = company_details.email_config.company_email_tls
        mail_username = company_details.email_config.company_email_user
        mail_password = company_details.email_config.company_email_password

        current_app.config.update(
            MAIL_SERVER=mail_server,
            MAIL_PORT=mail_port,
            MAIL_USE_TLS=mail_use_tls,
            MAIL_USERNAME=mail_username,
            MAIL_PASSWORD=mail_password
        )

        mail.init_app(current_app)
        logger.info("Mail configuration updated from company details")
    else:
        mail_server = app.config['MAIL_SERVER']
        mail_port = app.config['MAIL_PORT']
        mail_use_tls = app.config['MAIL_USE_TLS']
        mail_username = app.config['MAIL_USERNAME']
        mail_password = app.config['MAIL_PASSWORD']
        mail.init_app(app)
        logger.info("Mail configuration loaded from default app config")

    with current_app.app_context():
        for user in new_users:
            token = generate_confirmation_token(user['email'])
            confirm_url = url_for('auth.confirm_email', token=token, _external=True)
            html = render_template('email/employee_confirmation.html', confirm_url=confirm_url, current_password=user['password'])
            msg = Message('Please confirm your email! | Cubes HRMS', sender=("Cubes HRMS", mail_username), recipients=[user['email']])
            msg.html = html
            mail.send(msg)
            logger.info(f"Password email sent to: {user['email']}")

    logger.info("send_password_emails task completed")
    return True

@company.route('/createoffice/settings/', methods=['POST'])
def create_office():
    if request.method == 'POST':
        office_name = request.form.get('office_name')
        location_name = request.form.get("location-input")
        location_radius = request.form.get("location-radius")
        location_latitude = request.form.get("location-latitude")
        location_longitude = request.form.get("location-longitude")
        is_default = True if request.form.get("is_default") else False
        
        if office_name and location_name and location_radius:
            new_office =  CompanyOffices(office_name=office_name,
                                    location_name=location_name,
                                    location_radius=location_radius,
                                    location_latitude=location_latitude,
                                    location_longitude=location_longitude,
                                    is_default = is_default,
                                    company_id = current_user.id
                                    )
            new_office.save()
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__offices=new_office.id)
            if update_details:
                details = CompanyOffices.objects(company_id=current_user.id)
                js_data = loads(details.to_json())
                return dumps(js_data)
        else:
            msg =  '{ "html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
    else:
        return render_template('company/settings.html') 
    
@company.route('/adjustments', methods=['POST','GET'])
@roles_accepted('admin','company','expensemanager')
@login_required
def adjustments():
    if request.method=="POST":
        selected_of_month = datetime. strptime(request.form.get('selected_month'), '%Y-%m-%d')  if request.form.get('selected_month') else datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
    else:
        selected_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
    
    payroll_month = selected_of_month.strftime('%B');
    payroll_year = selected_of_month.year;    
    
    adjustment_details = CompanyPayrollAdjustment.objects(company_id=current_user.id,adjustment_month_on_payroll=payroll_month,adjustment_year_on_payroll=payroll_year)
    if not adjustment_details and current_user.type == "employee": 
        employee_details = EmployeeDetails.objects(user_id=current_user.id).only('company_id').first()
        adjustment_details = CompanyPayrollAdjustment.objects(company_id=employee_details.company_id,adjustment_month_on_payroll=payroll_month,adjustment_year_on_payroll=payroll_year)

    return render_template('company/adjustments/adjustments.html',adjustment_details=adjustment_details,start_of_month=selected_of_month)



@company.route('/create/adjustments', methods=['GET','POST'])
@roles_accepted('admin','company','expensemanager')
@login_required
def create_adjustments():
    company_details = CompanyDetails.objects(user_id=current_user.id).only('employees','adjustment_reasons','company_name','departments').first()
    company_id = current_user.id
    if not company_details: 
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        company_details = CompanyDetails.objects(user_id=employee_details.company_id).only('employees','adjustment_reasons').first()  
        company_id = employee_details.company_id
        
    if request.method == 'POST':
        employee_list = request.form.getlist('employees[]')
        flag = False
        if employee_list:
            for _employee in employee_list:
                employee_details_id = _employee 
                start_of_month = datetime. strptime(request.form.get('selected_month'), '%Y-%m-%d')  if request.form.get('selected_month') else datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
                total_adjustments = len(request.form.getlist("adjustment_reason[]"))
                if total_adjustments > 0:
                    adjustment_reason_list = request.form.getlist('adjustment_reason[]')
                    adjustment_amount_list = request.form.getlist('adjustment_amount[]')
                    adjustment_document_list = request.files.getlist('adjustment_document[]')

                    for item in range(0,total_adjustments):
                        adjustment_reason = adjustment_reason_list[item]
                        adjustment_amount = adjustment_amount_list[item]
                        adjustment_document = adjustment_document_list[item]
                        
                        if adjustment_reason:
                            flag = True
                            adjustment_reason_details = CompanyAdjustmentReasons.objects(_id=ObjectId(adjustment_reason)).first()
                            if adjustment_reason_details:
                                # Create a new record for payroll adjustment
                                # todo: Check if the payment is recurring; if recurring then create all the records of the terms with their respective amounts
                                recurring_payment = request.form.get('recurring_payment')
                                if recurring_payment:
                                    term =  request.form.get('recurring_month')
                                    monthly_amount = request.form.getlist('monthly_amount[]')
                                    rec_month = request.form.getlist('rec_month[]')
                                    
                                    for item in range(int(term)):
                                        start_of_month = datetime. strptime(rec_month[item], '%B %Y')
                                        new_data = CompanyPayrollAdjustment(
                                            company_id = company_id,
                                            employee_details_id = ObjectId(employee_details_id),
                                            adjustment_reason_id = adjustment_reason_details._id,
                                            adjustment_type = adjustment_reason_details.adjustment_type,
                                            adjustment_amount = monthly_amount[item],
                                            adjustment_on = start_of_month,
                                            adjustment_month_on_payroll = start_of_month.strftime('%B'),
                                            adjustment_year_on_payroll =  start_of_month.year                     
                                        )
                                        status = new_data.save()
                                        # todo: Check if the payroll is already existing; if yes then add the adjustments to payroll data of the employee
                                        employee_payroll_data = CompanyPayroll.objects(company_id=company_id,payroll_month=start_of_month.strftime('%B'),payroll_year=start_of_month.year,employee_details_id=ObjectId(employee_details_id)).first()
                                        if employee_payroll_data:
                                        # todo: based on adjustment type push to the appropriate list(adjustment_additions/adjustment_deductions)
                                        # todo: recalculate the salary_to_be_paid and total_additions & total_deductions     
                                            if adjustment_reason_details.adjustment_type == 'addition':
                                                total_addition = float(employee_payroll_data.total_additions) + float(monthly_amount[item])
                                                salary_to_be_paid = (float(employee_payroll_data.total_salary) +  float(total_addition))-float(employee_payroll_data.total_deductions)
                                                employee_payroll_data.update(add_to_set__adjustment_additions=status._id,total_additions=total_addition,salary_to_be_paid=salary_to_be_paid)
                                            if adjustment_reason_details.adjustment_type == 'deduction':
                                                total_deduction = float(employee_payroll_data.total_deductions) + float(monthly_amount[item])
                                                salary_to_be_paid = (float(employee_payroll_data.total_salary) +  float(employee_payroll_data.total_additions))-float(total_deduction)
                                                employee_payroll_data.update(add_to_set__adjustment_deductions=status._id,total_deductions=total_deduction,salary_to_be_paid=salary_to_be_paid)   
                                            # todo: added_to_payroll to true
                                            CompanyPayrollAdjustment.objects(_id=status._id).update(added_to_payroll=True)
                                else: 
                                    adjustment_document_name = ""
                                    if adjustment_document:
                                        adjustment_document_name = upload_adjustment_document(adjustment_document,company_details.company_name)    
                                    new_data = CompanyPayrollAdjustment(
                                            company_id = company_id,
                                            employee_details_id = ObjectId(employee_details_id),
                                            adjustment_reason_id = adjustment_reason_details._id,
                                            adjustment_type = adjustment_reason_details.adjustment_type,
                                            adjustment_amount = adjustment_amount,
                                            adjustment_document = adjustment_document_name,
                                            adjustment_on = start_of_month,
                                            adjustment_month_on_payroll = start_of_month.strftime('%B'),
                                            adjustment_year_on_payroll =  start_of_month.year                     
                                    )
                                    status = new_data.save()
                                    # todo: Check if the payroll is already existing; if yes then add the adjustments to payroll data of the employee
                                    employee_payroll_data = CompanyPayroll.objects(company_id=company_id,payroll_month=start_of_month.strftime('%B'),payroll_year=start_of_month.year,employee_details_id=ObjectId(employee_details_id)).first()
                                    if employee_payroll_data:
                                    # todo: based on adjustment type push to the appropriate list(adjustment_additions/adjustment_deductions)
                                    # todo: recalculate the salary_to_be_paid and total_additions & total_deductions     
                                        if adjustment_reason_details.adjustment_type == 'addition':
                                            total_addition = float(employee_payroll_data.total_additions) + float(adjustment_amount)
                                            salary_to_be_paid = (float(employee_payroll_data.total_salary) +  float(total_addition))-float(employee_payroll_data.total_deductions)
                                            employee_payroll_data.update(add_to_set__adjustment_additions=status._id,total_additions=total_addition,salary_to_be_paid=salary_to_be_paid)
                                        if adjustment_reason_details.adjustment_type == 'deduction':
                                            total_deduction = float(employee_payroll_data.total_deductions) + float(adjustment_amount)
                                            salary_to_be_paid = (float(employee_payroll_data.total_salary) +  float(employee_payroll_data.total_additions))-float(total_deduction)
                                            employee_payroll_data.update(add_to_set__adjustment_deductions=status._id,total_deductions=total_deduction,salary_to_be_paid=salary_to_be_paid)   
                                        # todo: added_to_payroll to true
                                        CompanyPayrollAdjustment.objects(_id=status._id).update(added_to_payroll=True)
                                    
                        # todo: Create a record in Activity Log 
                        activity_log = create_activity_log(request,current_user.id,company_id)      
        
        if flag:
            flash('Adjustments Created Successfully!', 'success')
            return redirect(url_for('company.adjustments'))
        else:
            flash('Something went Wrong. Please try again!', 'danger')
            return redirect(url_for('company.adjustments'))
        
    else:
        # company_details = CompanyDetails.objects(user_id=current_user.id).only('employees','adjustment_reasons').first()  
        start_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        return render_template('company/adjustments/create_adjustment.html',company_details=company_details,start_of_month=start_of_month)
        

@company.route('/delete/adjustment/<adjustment_id>')
@login_required
@roles_accepted('admin','company','expensemanager')
def delete_adjustment(adjustment_id):
    # Delete reference employee object
    adjustment_details=CompanyPayrollAdjustment.objects(_id=ObjectId(adjustment_id)).first()
    if adjustment_details: 
        # todo: Create a record in Activity Log 
        activity_log = create_activity_log(request,current_user.id,adjustment_details.company_id.id)    
        print(adjustment_details._id, "removed")
        adjustment_details.delete()
        if True:
            flash('Adjustment Deleted Successfully!', 'success')
            return redirect(url_for('company.adjustments'))
     
@company.route('/createreason/settings/', methods=['POST'])
def create_reason():
    if request.method == 'POST':
        adjustment_reason = request.form.get('adjustment_reason')
        adjustment_type = request.form.get("adjustment_type")
        
        if adjustment_reason and adjustment_type:
            new_adjustment_reason =  CompanyAdjustmentReasons(adjustment_reason=adjustment_reason,
                                    adjustment_type=adjustment_type,
                                    company_id = current_user.id
                                    )
            new_adjustment_reason.save()
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__adjustment_reasons=new_adjustment_reason.id)
            if update_details:
                details = CompanyAdjustmentReasons.objects(company_id=current_user.id)
                msg =  json.dumps({"status":"success","details":details.to_json()})
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg =  '{ "html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
    else:
        return render_template('company/settings.html')
    
#Employee List Page
# @company.route('/generate/payroll', methods=['POST'])
# @login_required
# @roles_accepted('admin','company')
# def generate_payroll():
#     selected_month = request.form.get('selected_month')
#     sub_company = request.form.get('sub_company') 
#     sm = datetime. strptime(selected_month, '%Y-%m-%d')
#     message = 'Payroll Generation for the month of ' + sm.strftime('%B %Y') + ' has '
#     if selected_month:

#         result = generate_bulk_payroll(selected_month,str(current_user.id), sub_company)
#         # result = generate_bulk_payroll(selected_month,str(current_user.id), sub_company)
        
#         #    result = add_bulk_open_leaves(leave_data,str(current_user.id))
#         if result[0]:
#             # task_scheduled_details = ScheduledBackgroundTask(celery_task_id=result.id,company_id=current_user.id,task_type='generate_bulk_payroll',message=message,uploaded_on=datetime.now())
#             # task_scheduled_details.save()
#             return {
#                 'sucess': "True", 
#                 'message': 'Sucess'
#             }
#         else:
#             return {
#                 'sucess': "False", 
#                 'message': result[1]
#             }
#     else:
#         return {
#                 'sucess': "False", 
#                 'message': "please select a month."
#         }



@company.route('/generate/payroll', methods=['POST'])
@login_required
@roles_accepted('admin', 'company')
def generate_payroll():
    selected_month = request.form.get('selected_month')
    sub_company = request.form.get('sub_company')

    # Check if the selected month is provided
    if not selected_month:
        return {
            'success': "False",
            'message': "Please select a month."
        }

    # Parse the selected month
    sm = datetime.strptime(selected_month, '%Y-%m-%d')
    message = 'Payroll Generation for the month of ' + sm.strftime('%B %Y') + ' has '

    # Parse the sub_company JSON string into a list
    if sub_company:
        try:
            sub_company_list = json.loads(sub_company)
            # Convert each company ID to ObjectId (if needed)
            sub_company_ids = [ObjectId(company_id) for company_id in sub_company_list]


        except Exception as e:
            return {
                'success': "False",
                'message': f"Error parsing sub_company: {str(e)}"
            }
    else:
        sub_company_ids = ''

    results = []  # Store results for each sub company
    if len(sub_company_list) == 0:
    # If empty, pass None for the company
        result = generate_bulk_payroll(selected_month, str(current_user.id), sub_company_list )
        results.append(result)
    else:
   
        sub_company_ids = [ObjectId(company_id) for company_id in sub_company_list]
        for company in sub_company_ids:
            result = generate_bulk_payroll(selected_month, str(current_user.id), company)
            results.append(result)


    # Process results
    all_success = all(res[0] for res in results)  # Check if all results are successful
    if all_success:
        return {
           'sucess': "True", 
            'message': 'Sucess'
        }
    else:
        # If any result is not successful, compile error messages
        error_messages = [res[1] for res in results if not res[0]]
        return {
            'sucess': "False", 
            'message': error_messages
        }


# @celery.task(track_started = True,result_extended=True,name='Generate-Payroll-Data')
def generate_bulk_payroll(_month, current_user, sub_company):
    selected_month = datetime. strptime(_month, '%Y-%m-%d')

    employees_details = CompanyDetails.objects(user_id=ObjectId(current_user)).first()

    print(sub_company)

    if sub_company == 'No need' :
        sub_company = None

    print(sub_company, 'after update')

    if ((sub_company) and (sub_company != 'No need' )) :
        sub_company_employees_details = list(
            filter(
                lambda x: x['employee_company_details']['working_sub_company'] 
                        and x['employee_company_details']['working_sub_company']['_id'] == ObjectId(sub_company),
                employees_details.employees
            )
        )

        # active_employees = list(filter(lambda x:x['employee_company_details']['status']==True,sub_company_employees_details))
        # active_employees = filter_active_employees(sub_company_employees_details.employees, selected_month, sub_company)
        active_employees = filter_active_employees(sub_company_employees_details, selected_month, sub_company)  #added By ashiq date : 20/09/2024 issues : subcompnay 

    else :
        # active_employees = list(filter(lambda x:x['employee_company_details']['status']==True,employees_details.employees))
        # active_employees = list(filter(lambda x:x['_id']==ObjectId('624fe7dfe715a9c4baa8045b'),employees_details.employees))
        active_employees = filter_active_employees(employees_details.employees, selected_month, None)

    
    overal_salary_to_be_paid = 0.0
    overal_salary_to_be_paid_ja = 0.0
    overal_salary_to_be_paid_aa = 0.0
    overal_salary_to_be_paid_rb = 0.0
    overal_salary_to_be_paid_cash = 0.0
    
    
    no_of_employees_ja = 0
    no_of_employees_aa = 0
    no_of_employees_rb = 0
    no_of_employees_cash = 0
    
    nxt_mnth = selected_month.replace(day=28) + timedelta(days=4)
    end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)

    #..................create a sif record wichi will letr be populated.............

    sif_exists = SIF.objects(
    company = employees_details,
    start_date = selected_month.strftime('%Y-%m-%d'),
    end_date = end_of_the_month.strftime('%Y-%m-%d'),
    sub_company = ObjectId(sub_company) if sub_company else None).all()

    if (len(sif_exists)):
        for sif_rec in sif_exists:
            sif_rec.delete()

    sif_record = SIF(
    company = employees_details,
    start_date = selected_month.strftime('%Y-%m-%d'),
    end_date = end_of_the_month.strftime('%Y-%m-%d'),
    sub_company = ObjectId(sub_company) if sub_company else None,
    created_by = ObjectId(current_user),
    created_on = datetime.now()
    )


    wps_strategey = WPS_Strategy()
    wps_factory = WPS_Factory(wps_strategey)

    #...............................................................................
    index = 0
    for employee in active_employees:
        if employee.employee_company_details.type == '0': # if the employee salary type is 0 i.e Full-time employee 
            # check if the data available in the DB, if yes delete and create a new record
            data_available = CompanyPayroll.objects(company_id=ObjectId(current_user),payroll_month=selected_month.strftime('%B'),payroll_year=selected_month.year,employee_details_id=employee._id).first()
            if data_available:
                if data_available.sif_details:
                    sif_details = CompanySif.objects(_id=data_available.sif_details._id).first()
                    if sif_details:
                        sif_details.delete()
                data_available.delete()
            # Create a new record including the adjustments as well 
            employee_payroll = CompanyPayroll()
            employee_payroll.employee_id = employee.employee_company_details.employee_id
            employee_payroll.company_id = ObjectId(current_user)
            employee_payroll.employee_details_id = employee._id
            employee_payroll.payroll_month = selected_month.strftime('%B')
            employee_payroll.payroll_year = selected_month.year
            # Salary Details
            employee_payroll.basic_salary = employee.employee_company_details.basic_salary
            employee_payroll.housing_allowance = employee.employee_company_details.housing_allowance
            employee_payroll.travel_allowance = employee.employee_company_details.travel_allowance
            employee_payroll.other_allowances = employee.employee_company_details.other_allowances
            employee_payroll.fuel_allowances = employee.employee_company_details.fuel_allowance
            employee_payroll.mobile_allowances = employee.employee_company_details.mobile_allowance
            employee_payroll.medical_allowances = employee.employee_company_details.medical_allowance
            employee_payroll.total_salary = employee.employee_company_details.total_salary
            
            # Todo: Check for Adjustments records and add to payroll deduction and additions
            adjustments_exists = CompanyPayrollAdjustment.objects(employee_details_id=employee._id,company_id=ObjectId(current_user),adjustment_month_on_payroll=selected_month.strftime('%B'),adjustment_year_on_payroll=selected_month.year)
            addition_amount = 0.0
            deduction_amount = 0.0
            if adjustments_exists:
                additions = []
                deductions = []
                for adjustment in adjustments_exists:
                    # Adjustment Additions
                    if adjustment.adjustment_type == 'addition':
                        additions.append(adjustment._id)
                        addition_amount = float(addition_amount) + float(adjustment.adjustment_amount)
                    # Adjustment Deduction
                    else:
                        deductions.append(adjustment._id)
                        deduction_amount = float(deduction_amount) + float(adjustment.adjustment_amount)
                        
                    # todo: Update the adjustment as approved to payroll so that we can disable the delete option for the adjustment;
                    CompanyPayrollAdjustment.objects(_id=adjustment._id).update(added_to_payroll=True)
                
                employee_payroll.adjustment_additions = additions
                employee_payroll.adjustment_deductions = deductions
                employee_payroll.total_deductions = deduction_amount
                employee_payroll.total_additions = addition_amount
            
            salary_to_be_paid = (float(employee.employee_company_details.total_salary) +  float(addition_amount))-float(deduction_amount)
            fixed_salary = float(employee.employee_company_details.total_salary)
            salary_with_deduction = float(employee.employee_company_details.total_salary) - float(deduction_amount)
            employee_payroll.salary_to_be_paid = salary_to_be_paid
            employee_payroll.generated_date = datetime.today()
            
            # Check to which exchage the emp belongs
            if hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name') and employee.employee_sif_details.company_exchange.exchange_name == "JOYALUKKAS EXCHANGE":
                overal_salary_to_be_paid_ja = overal_salary_to_be_paid_ja + salary_to_be_paid
                no_of_employees_ja = no_of_employees_ja + 1
                print(employee._id)
                
            elif hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name') and employee.employee_sif_details.company_exchange.exchange_name == "Al Ansari Exchange":
                overal_salary_to_be_paid_aa = overal_salary_to_be_paid_aa + salary_to_be_paid
                no_of_employees_aa = no_of_employees_aa + 1
                
            elif hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name') and employee.employee_sif_details.company_exchange.exchange_name == "RAK Bank":
                overal_salary_to_be_paid_rb = overal_salary_to_be_paid_rb + salary_to_be_paid
                no_of_employees_rb = no_of_employees_rb + 1
            
            elif hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name') and employee.employee_sif_details.company_exchange.exchange_name == "Cash":
                overal_salary_to_be_paid_cash = overal_salary_to_be_paid_cash + salary_to_be_paid
                no_of_employees_cash = no_of_employees_cash + 1
            
            # todo: Calculate on_leave_days
            # on_leave_days = EmployeeAttendance.objects(employee_details_id=employee._id,attendance_status="absent",attendance_date__gte=selected_month,attendance_date__lte=end_of_the_month).count()
            on_leave_days = 0
            unpaid_leaves = EmployeeAttendance.objects(Q(employee_details_id=employee._id) & Q(attendance_date__gte=selected_month) & Q(attendance_date__lte=end_of_the_month) & Q(attendance_status='absent') & (Q(leave_name='') | Q(leave_name__exists=False))).count()
            paid_days = EmployeeAttendance.objects(Q(employee_details_id=employee._id) & Q(attendance_date__gte=selected_month) & Q(attendance_date__lte=end_of_the_month) & Q(attendance_status='absent') & (Q(leave_name__ne='') & Q(leave_name__exists=True))).count()
            half_days = EmployeeAttendance.objects(employee_details_id=employee._id,half_day=True,attendance_date__gte=selected_month,attendance_date__lte=end_of_the_month).count()
            if half_days:
                half_day_count = math.ceil((half_days/2))
                on_leave_days = unpaid_leaves + half_day_count
            employee_payroll.unpaid_leaves = unpaid_leaves
            employee_payroll.half_days = half_days
            employee_payroll.paid_leaves = paid_days
            employee_payroll.start_date = selected_month.strftime('%Y-%m-%d')
            employee_payroll.end_date = end_of_the_month.strftime('%Y-%m-%d')
            employee_payroll.working_sub_company = ObjectId(sub_company) if sub_company  else None
            employee_payroll.save()
            
            #......................................................................................
            try :
                if ("FZE" in employee.employee_sif_details.company_exchange.exchange_name):
                    index = index + 1

                edr_record = wps_factory.generate_edr(employee, employee_payroll, index)


                bank_name = employee.employee_sif_details.company_exchange.exchange_name
        
                # check if edr_record type is of array
                if type(edr_record) is not list:
                    # Check if the bank key exists in sif.EDR_records
                    if bank_name in sif_record.EDR_records:
                        sif_record.EDR_records[bank_name].append(edr_record)
                    else:
                        sif_record.EDR_records[bank_name] = [edr_record]

                    print(edr_record)
                    
                    edr_record.save()

                else:
                    return edr_record

            except Exception as e:

                return [ False, str(e) ]  
            #.....................................................................................


            employee_sif = CompanySif()
            employee_sif.company_id = ObjectId(current_user)
            employee_sif.employee_id = employee.employee_company_details.employee_id
            employee_sif.employee_details_id = employee._id
            employee_sif.sif_type = "EDR"
            employee_sif.pay_start = selected_month.strftime('%Y-%m-%d')
            employee_sif.pay_end = end_of_the_month.strftime('%Y-%m-%d')
            
            employee_sif.pay_start_cbd = selected_month.strftime('%d/%m/%Y')
            employee_sif.pay_end_cbd = end_of_the_month.strftime('%d/%m/%Y')

            employee_sif.days_in_month = str((end_of_the_month).day)
            employee_sif.salary = str(salary_to_be_paid)
            employee_sif.fixed_salary = str(fixed_salary)
            employee_sif.on_leave_days = str(on_leave_days)
            employee_sif.variable_pay = abs(float(addition_amount)) 
            employee_sif.salary_with_deduction = str(salary_with_deduction)
            employee_sif.sif_month = selected_month
            employee_sif.sif_year = selected_month.year
            employee_sif.exchange = employee.employee_sif_details.company_exchange.exchange_name if (hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name')) else ''
            
            employee_sif.save()
            employee_payroll.update(sif_details=employee_sif._id)
    
    # todo: Generate sif SCR record as well
    # todo: Check if the previous SCR recors is present if yes delete and create new
    data_available = CompanySif.objects(company_id=ObjectId(current_user),sif_month=selected_month,sif_year=selected_month.year,sif_type='SCR')
    if data_available:
        data_available.delete()
    
    employee_sif = CompanySif()
    employee_sif.company_id = ObjectId(current_user)
    # employee_sif.employee_id = employee.employee_company_details.employee_id
    # employee_sif.employee_details_id = employee._id
    employee_sif.sif_type = "SCR"
    employee_sif.company_unique_id = employees_details.company_unique_id
    employee_sif.company_routing_code = employees_details.company_routing_code
    employee_sif.file_creation_date = datetime.now().strftime('%Y-%m-%d')
    employee_sif.file_date = datetime.now().strftime('%y%m%d')
    employee_sif.file_creation_time = datetime.now().strftime('%H%M')
    employee_sif.file_time = datetime.now().strftime('%H%M%S')
    
    employee_sif.salary_month = selected_month.strftime('%m%Y')
    employee_sif.edr_count_ja = no_of_employees_ja
    employee_sif.edr_count_aa = no_of_employees_aa
    employee_sif.edr_count_rb = no_of_employees_rb
    employee_sif.edr_count_cash = no_of_employees_cash
    
    employee_sif.overal_salary_to_be_paid_ja = overal_salary_to_be_paid_ja
    employee_sif.overal_salary_to_be_paid_aa = overal_salary_to_be_paid_aa
    employee_sif.overal_salary_to_be_paid_rb = overal_salary_to_be_paid_rb
    employee_sif.overal_salary_to_be_paid_cash = overal_salary_to_be_paid_cash
    
    employee_sif.currency = "AED"
    employee_sif.reference = employees_details.company_name
    employee_sif.sif_month = selected_month
    employee_sif.sif_year = selected_month.year
    
    employee_sif.save()

    #................generate scr and save.........................

    payroll_details = SimpleNamespace()
    payroll_details.start_date = selected_month.strftime('%Y-%m-%d')
    payroll_details.end_date = end_of_the_month.strftime('%Y-%m-%d')
    payroll_details.reference = employees_details.company_name

    try:
        if sub_company:
            sub_company_obj = SubCompanies.objects(_id = ObjectId(sub_company)).first()

            wps_factory.generate_scr(sub_company_obj, payroll_details, sif_record)    
        else:
            employer_details = CompanyDetails.objects(user_id=employees_details.user_id.id).first()

            wps_factory.generate_scr(employer_details, payroll_details, sif_record)    

        sif_record.save()

        # Optional: Save each SCR record separately if needed
        for scr in sif_record.SCRs.values():
            scr.save()

    except Exception as e:
        return [False, str(e)]
    #..................................................................
    
    return "True"
 
def create_adjustment_reason(company_id,adjustement_reason,adjustment_type):
    # Todo: Check for the time approver if exist create record else return false; 
    new_adjustment_reason = CompanyAdjustmentReasons()
    new_adjustment_reason.company_id = company_id
    new_adjustment_reason.adjustment_reason = adjustement_reason
    new_adjustment_reason.adjustment_type = adjustment_type
    new_adjustment_reason.save()
    update_details = CompanyDetails.objects(user_id=company_id).update(push__adjustment_reasons=new_adjustment_reason.id)
        
    return new_adjustment_reason                         

@company.route('/upload/attendance', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def upload_attendance():
    attendance_data = []
    file = request.files.getlist('files')
    selected_month = request.form.get('selected_month')
    sm = datetime. strptime(selected_month, '%Y-%m-%d')
    message = 'Bulk upload of Attendance for the month of ' + sm.strftime('%B %Y') + ' has '         
    # Start Parsing through CSV File
    if file:
            filename = secure_filename(file[0].filename)
            fn = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            fname = fn+str(uuid.uuid4())+file_ext
            if file_ext not in app.config['UPLOAD_FILE_EXTENSIONS']: 
                flash('Please insert document with desired format!')
                return redirect(url_for('company.payroll'))
            if not os.path.exists(app.config['UPLOAD_FILE_FOLDER']):
                os.makedirs(app.config['UPLOAD_FILE_FOLDER'])
            document_path = os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname)
            file[0].save(os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname))
            
        # Dialect helps in grouping together many specific formatting patterns like delimiter, skipinitialspace, quoting, escapechar into a single dialect name.
            csv.register_dialect('myDialect',
                            skipinitialspace=True,
                            quoting=csv.QUOTE_ALL)
            
            with open(document_path, 'r') as file:
                csvreader = csv.DictReader(file, dialect='myDialect')
                # header = next(csvreader)
                for row in csvreader:
                    attendance_data.append(dict(row))
            os.remove(document_path)
    # End Parsing through CSV File
            # print(attendance_data)
    if attendance_data:
        result = upload_attendance_data.delay(attendance_data,selected_month,str(current_user.id))
        if result:
            task_scheduled_details = ScheduledBackgroundTask(celery_task_id=result.id,company_id=current_user.id,task_type='missing_attendance_data',message=message,file_name=filename,uploaded_on=datetime.now())
            task_scheduled_details.save()
            # r = celery.AsyncResult(result.id)
            return "True"
    else:
        return "False"
    
@celery.task(track_started = True,result_extended=True,name='Missing-Attendance-Data')
def upload_attendance_data(attendance_data,selected_month,current_user):
    if attendance_data:
        bulk_attendance_data = []
        for item in attendance_data:
            attendance_date = datetime. strptime(item['attendance_date'], '%d/%m/%Y')
            employee_check_in_time = datetime.strptime(item['check_in_time_1'], '%d/%m/%Y %I:%M %p')
            employee_check_out_time = datetime.strptime(item['check_out_time_1'], '%d/%m/%Y %I:%M %p')
            employee_details = EmployeeDetails.objects(employee_company_details__employee_id=item['employee_id']).first()
            if employee_details:
                data_available = EmployeeAttendance.objects(company_id=ObjectId(current_user),attendance_date=attendance_date,employee_details_id=ObjectId(employee_details._id)).first()
                
                if data_available:
                    data_available.delete()
                employee_attendance = EmployeeAttendance()    
                employee_attendance.employee_id = employee_details.employee_company_details.employee_id
                employee_attendance.employee_details_id = ObjectId(employee_details._id)
                employee_attendance.attendance_date = attendance_date
                employee_attendance.company_id = ObjectId(current_user)
                employee_attendance.employee_check_in_at = employee_check_in_time
                employee_attendance.employee_check_out_at = employee_check_out_time
                employee_attendance.attendance_status = "present"
                employee_attendance.uploaded_on = selected_month
                
                bulk_attendance_data.append(employee_attendance)
       
        save_data = EmployeeAttendance.objects.insert(bulk_attendance_data)    
        if save_data:
            return True
    else:
    # empty File
      return False;    

@company.route('/createclockinoptions/settings/', methods=['POST'])
def create_clock_in_options():
    if request.method == 'POST':
        clock_in_from = request.form.get('ci_option_from')
        outside_office = True if request.form.get('outside_office') else False
        if clock_in_from:
            new_clock_in_opt =  CompanyClockInOptions(
                                    clock_in_from=clock_in_from,
                                    outside_office=outside_office,
                                    company_id = current_user.id
                                    )
            new_clock_in_opt.save()
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__clock_in_options=new_clock_in_opt.id)
            if update_details:  
                details = CompanyClockInOptions.objects(company_id=current_user.id)
                msg =  json.dumps({"status":"success","details":details.to_json()})
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg =  '{ "html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
    else:
        return render_template('company/settings.html')
    
@company.route('/edit/clockin/', methods=['POST'])
@login_required
@roles_accepted('company','supervisor','attendancemanager')
def edit_clock_in():
    if request.method == 'POST':
        attendance_id = request.form.get('attendance_id')
        if attendance_id:
            attendance_details = EmployeeAttendance.objects(_id=ObjectId(attendance_id)).first()
            new_clock_in = request.form.get('edited_clock_in')
            clock_in_time = datetime.strptime(new_clock_in, '%I:%M %p')
            updated_clock_in = attendance_details.employee_check_in_at.replace(hour=clock_in_time.hour,minute=clock_in_time.minute)
            
            # Calculate the late minutes if late by the employee;
            late_minutes = calculate_late_details_new(updated_clock_in,attendance_details.employee_details_id,attendance_details.attendance_date)
            
            if late_minutes > 0:
                is_late = True
                late_by_minutes = str(late_minutes)
                # Todo: Create a EmployeeTimeRequest record with the dedicated approver of the department if late exists
                time_request_exists = EmployeeTimeRequest.objects(company_id=attendance_details.employee_details_id.company_id,attendance_id=attendance_details._id,request_type="late").first()
                if not time_request_exists:
                    time_request = create_time_request(attendance_details.employee_details_id.company_id,attendance_details._id,attendance_details.employee_details_id.employee_company_details.department,'late')
                else:
                    time_request_exists.update(request_status="pending")
                    late_approval_status = True if attendance_details.late_approval_status else False
                    status = attendance_details.update(employee_check_in_at=updated_clock_in,is_late=is_late,late_by_minutes=late_by_minutes,late_approval_status=late_approval_status)
            else:
                is_late = False
                late_by_minutes = str(late_minutes)
                # Todo: Check if a EmployeeTimeRequest record exists with the dedicated approver of the department if late exists
                time_request_exists = EmployeeTimeRequest.objects(company_id=attendance_details.employee_details_id.company_id,attendance_id=attendance_details._id,request_type="late").first()
                if time_request_exists:
                    time_request_exists.delete()
            # todo: Create a record in Activity Log 
            activity_log = create_activity_log(request,current_user.id,attendance_details.employee_details_id.company_id)
                
            if hasattr(attendance_details,'employee_check_out_at'):
                total_hrs_worked = chop_microseconds(attendance_details.employee_check_out_at - attendance_details.employee_check_in_at)
                status = attendance_details.update(employee_check_in_at=updated_clock_in,total_hrs_worked=str(total_hrs_worked),is_late=is_late,late_by_minutes=late_by_minutes,push__activity_history=activity_log._id)
            else:
                status = attendance_details.update(employee_check_in_at=updated_clock_in,is_late=is_late,late_by_minutes=late_by_minutes,push__activity_history=activity_log._id)

            if status:               
                msg =  json.dumps({"status":"success"})
                msghtml = json.loads(msg)
                return msghtml
            else:
                msg =  json.dumps({"status":"failed"})
                msghtml = json.loads(msg)
                return msghtml
            
@company.route('/edit/clockout/', methods=['POST'])
@login_required
@roles_accepted('company','supervisor','attendancemanager')
def edit_clock_out():
    if request.method == 'POST':
        attendance_id = request.form.get('attendance_id')
        if attendance_id:
            attendance_details = EmployeeAttendance.objects(_id=ObjectId(attendance_id)).first()
            new_clock_out = request.form.get('edited_clock_out')
            clock_out_time = datetime.strptime(new_clock_out, '%I:%M %p')
            updated_clock_out = attendance_details.employee_check_out_at.replace(hour=clock_out_time.hour,minute=clock_out_time.minute) if hasattr(attendance_details,'employee_check_out_at') else attendance_details.employee_check_in_at.replace(hour=clock_out_time.hour,minute=clock_out_time.minute)
            # if hasattr(attendance_details,'employee_check_out_at'):
            total_hrs_worked = chop_microseconds(updated_clock_out - attendance_details.employee_check_in_at)
            
            # Todo: Check if the user left early
            # Start
            # Calculate the Early minutes if late by the employee;
            early_by_minutes = calculate_early_departure_details_new(updated_clock_out,attendance_details.employee_details_id,attendance_details.attendance_date)
            # todo: Create a record in Activity Log 
            activity_log = create_activity_log(request,current_user.id,attendance_details.employee_details_id.company_id)
            if early_by_minutes > 0:
                has_left_early = True
                early_by_minutes = str(early_by_minutes)
                # Todo: Create a EmployeeTimeRequest record with the dedicated approver of the department if Early exists
                time_request_exists = EmployeeTimeRequest.objects(company_id=attendance_details.employee_details_id,attendance_id=attendance_details._id,request_type="early").first()
                if not time_request_exists:
                    time_request = create_time_request(attendance_details.employee_details_id,attendance_details._id,attendance_details.employee_details_id.employee_company_details.department,'early')
                else:
                    time_request_exists.update(request_status="pending")
                early_approval_status = True if attendance_details.early_approval_status else False
                status = attendance_details.update(employee_check_out_at=updated_clock_out,total_hrs_worked=str(total_hrs_worked),has_left_early=has_left_early,early_by_minutes=early_by_minutes,early_approval_status=early_approval_status,push__activity_history=activity_log._id)
            else:
                has_left_early = False
                early_by_minutes = str(early_by_minutes)
                # Todo: Check if a EmployeeTimeRequest record exists with the dedicated approver of the department if Early exists
                time_request_exists = EmployeeTimeRequest.objects(company_id=attendance_details.employee_details_id,attendance_id=attendance_details._id,request_type="early").first()
                if time_request_exists:
                    time_request_exists.delete()
                status = attendance_details.update(employee_check_out_at=updated_clock_out,total_hrs_worked=str(total_hrs_worked),has_left_early=has_left_early,early_by_minutes=early_by_minutes,push__activity_history=activity_log._id)

            # End
            if status:
                msg =  json.dumps({"status":"success"})
                msghtml = json.loads(msg)
                return msghtml
            else:
                msg =  json.dumps({"status":"failed"})
                msghtml = json.loads(msg)
                return msghtml
            
def chop_microseconds(delta):
    return delta - timedelta(microseconds=delta.microseconds)

@company.route('/markattendance/', methods=['POST'])
@login_required
@roles_accepted('company','supervisor','attendancemanager')
def mark_attendance():
    if request.method == 'POST':
        # company_id = request.form.get('company_id')
        attendance_date = datetime.strptime(request.form.get('attendance_date'), '%d/%m/%Y') if request.form.get('attendance_date') else ''
        employee_details_id = request.form.get('employee_details_id')
        attendance_status = request.form.get('attendance_status')
        if attendance_status == "present":
            clock_in = datetime.strptime(request.form.get('clock_in_time'), '%I:%M %p') if request.form.get('clock_in_time') else ''
            has_clocked_out =request.form.get('has_clocked_out')   
            clock_out = datetime.strptime(request.form.get('clocked_out_time'), '%I:%M %p') if  request.form.get('clocked_out_time') else ''
            working_from = request.form.get('working_from')
            note = request.form.get('note')
            employee_details= EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
            if attendance_date and employee_details and clock_in and working_from:
                
                data_available = EmployeeAttendance.objects(company_id=employee_details.company_id,attendance_date=attendance_date,employee_details_id=ObjectId(employee_details_id)).first()
                if data_available:
                    data_available.delete()
        
            employee_attendance = EmployeeAttendance()    
            employee_attendance.employee_id = employee_details.employee_company_details.employee_id
            employee_attendance.employee_details_id = ObjectId(employee_details_id)
            employee_attendance.attendance_date = attendance_date
            employee_attendance.company_id = employee_details.company_id
            
            employee_attendance.employee_check_in_at = attendance_date.replace(hour=clock_in.hour,minute=clock_in.minute)
            
            if has_clocked_out:
                employee_attendance.employee_check_out_at = attendance_date.replace(hour=clock_out.hour,minute=clock_out.minute)
                total_hrs_worked = chop_microseconds(clock_out-clock_in)
                employee_attendance.total_hrs_worked = str(total_hrs_worked)
                
            employee_attendance.attendance_status = "present"
            employee_attendance.working_from = ObjectId(working_from)
            employee_attendance.clock_in_note = note
            
            status = employee_attendance.save()
        # Absent Module
        else:
            employee_details= EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
            if attendance_date and employee_details:
                
                data_available = EmployeeAttendance.objects(company_id=employee_details.company_id,attendance_date=attendance_date,employee_details_id=ObjectId(employee_details_id)).first()
                if data_available:
                    data_available.delete()
                    
            employee_attendance = EmployeeAttendance()    
            employee_attendance.employee_id = employee_details.employee_company_details.employee_id
            employee_attendance.employee_details_id = ObjectId(employee_details_id)
            employee_attendance.attendance_date = attendance_date
            employee_attendance.company_id = employee_details.company_id
            employee_attendance.attendance_status = "absent"
            status = employee_attendance.save()
            
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=employee_details.company_id,adjustment_reason="Unpaid Leaves").first()
            if not adjustment_reason:
                adjustment_reason = create_adjustment_reason(employee_details.company_id,"Unpaid Leaves","deduction")
                
            # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
            total_salary = employee_details.employee_company_details.total_salary
            
            current_month = attendance_date.strftime('%B')
            start_of_month = attendance_date.replace(day=1)
            nxt_mnth = attendance_date.replace(day=28) + timedelta(days=4)
            # subtracting the days from next month date to
            # get last date of current Month
            end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
            
            calendar_working_days = CompanyDetails.objects(user_id=employee_details.company_id).only('working_days').first()
            # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
            working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))

            no_of_working_days = int(working_days[0]['days']) if working_days else end_of_the_month.days() # By Default Set to 30 Days
                                
            adjustment_amount = round(int(total_salary)/no_of_working_days,0)
            
            
            new_data = CompanyPayrollAdjustment(
                    company_id = employee_details.company_id,
                    employee_details_id = ObjectId(employee_details_id),
                    adjustment_reason_id = adjustment_reason._id,
                    adjustment_type = adjustment_reason.adjustment_type,
                    adjustment_amount = str(adjustment_amount),
                    adjustment_on = start_of_month,
                    adjustment_month_on_payroll = start_of_month.strftime('%B'),
                    adjustment_year_on_payroll =  start_of_month.year,
                    attendance_date =  attendance_date,                   
            )   
            new_data.save()
            
        # todo: Create a record in Activity Log 
        activity_log = create_activity_log(request,current_user.id,employee_details.company_id)
        if status:
            msg =  json.dumps({"status":"success"})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))
    

@company.route('/update/leavecycle/', methods=['POST'])
def update_leave_cycle():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            #Create Employee Login Details
            company_details.leave_cycle = request.form.get('leave_cycle')
            if request.form.get('leave_cycle') == 'custom_cycle':
                date_range = request.form.get('daterange').split(' - ')
                leave_cycle_start_date = datetime. strptime(date_range[0], '%B %d')
                leave_cycle_end_date = datetime. strptime(date_range[1], '%B %d')
                company_details.leave_cycle_start_date = leave_cycle_start_date
                company_details.leave_cycle_end_date = leave_cycle_end_date
            company_details.save()
            flash('Company Leave Cycle Settings Updated Successfully!', 'success')
            return redirect(url_for('company.company_settings'))
    else:
        return render_template('company/settings.html')
    
@company.route('/createleavepolicy/settings/', methods=['POST'])
def create_leave_policy():
    if request.method == 'POST':
        leave_policy_name = request.form.get('leave_policy_name')
        allowance_type = request.form.get("allowance_type")
        leave_type = request.form.get("leave_type")
        allow_on_probation = True if request.form.get("allow_on_probation") == "yes" else False
        carry_over = True if request.form.get("carry_over") == "yes" else False
        # validate the received values
        if leave_policy_name:
            if(allowance_type == "onetime"):
                non_probabtion_allowance_days = request.form.get("non_probabtion_allowance_days")
                probabtion_allowance_days = request.form.get("probabtion_allowance_days")
                leave_policy =  CompanyLeavePolicies(leave_policy_name=leave_policy_name,
                            non_probabtion_allowance_days=non_probabtion_allowance_days,
                            probabtion_allowance_days=probabtion_allowance_days,
                            allowance_type=allowance_type,
                            leave_type=leave_type,
                            allow_on_probation=allow_on_probation,
                            carry_over = carry_over,
                            company_id = current_user.id
                            )
            else:
                allowance_days = request.form.get("allowance_days")
                leave_policy =  CompanyLeavePolicies(leave_policy_name=leave_policy_name,
                                        allowance_days=allowance_days,
                                        allowance_type=allowance_type,
                                        leave_type=leave_type,
                                        allow_on_probation=allow_on_probation,
                                        carry_over = carry_over,
                                        company_id = current_user.id
                                        )

            leave_policy.save()
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__leave_policies=leave_policy.id)
            if update_details:
                details = CompanyLeavePolicies.objects(company_id=current_user.id)
                js_data = loads(details.to_json())
                return dumps(js_data)
        
        else:
            msg =  '{ "html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
        
       
    else:
        return render_template('company/settings.html') 

@company.route('/update/employeeleaves/', methods=['POST'])
def update_employee_leave():
    if request.method == 'POST':
        employee_details_id = request.form.get('emp_details_id')
        leave_id = request.form.get('leave_id')
        balance_days = request.form.get('balance_days')
        employee_leave_policy_id = request.form.get('employee_leave_policy_id')
        new_balance_days = request.form.get('new_balance_days')
        
        employee_details = EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
        leave_policy = CompanyLeavePolicies.objects(_id=ObjectId(leave_id)).first()
        
        if employee_details and leave_policy:
            #Check if the data alreasy exist then update
            if employee_leave_policy_id:
                employee_leave_policy = EmployeeLeavePolicies.objects(_id=ObjectId(employee_leave_policy_id)).first()
                status = employee_leave_policy.update(balance=float(new_balance_days))
            else:
                employee_leave_policy = EmployeeLeavePolicies()
                employee_leave_policy.company_id = current_user.id
                employee_leave_policy.employee_details_id = employee_details._id
                employee_leave_policy.leave_policy_id = leave_policy._id
                employee_leave_policy.balance = float(balance_days)
                employee_leave_policy.save()
                status = employee_details.update(push__employee_leave_policies=employee_leave_policy._id)
            
            if status:
                flash('Leave Policy Updated Successfully!', 'success')
                return redirect(url_for('company.edit_employee_details',emp_id=employee_details._id))
    else:
        flash('There was some error please try again later!', 'danger')
        return redirect(url_for('company.employees_list'))
    
@company.route('/getemployeesbydept', methods=['GET'])
def get_employees_by_department():
    selected_department = request.args.get('selected_department')
    if selected_department =="All" or selected_department =="all":
        employee_details = EmployeeDetails.objects(company_id=current_user.id).only('first_name','last_name','_id')
    else:    
        employee_details = EmployeeDetails.objects(company_id=current_user.id,employee_company_details__department=selected_department).only('first_name','last_name','_id')
    managers_details = EmployeeDetails.objects(company_id=current_user.id,employee_company_details__designation__icontains="MANAGER").only('first_name','last_name','_id')
    hod_details = EmployeeDetails.objects(company_id=current_user.id,employee_company_details__department__icontains="HOD").only('first_name','last_name','_id')
    
    if employee_details or managers_details:
        # attendance_data = loads(attendance_details.to_json())
        msg =  json.dumps({'status':'success','details':employee_details.to_json(),'managers':managers_details.to_json(),'hod_details':hod_details.to_json()})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml
    
@company.route('/createleaveapprover/settings/', methods=['POST'])
def create_leave_approvers():
    if request.method == 'POST':
        # employee_details_id = request.form.get('emp_details_id')
        dept_name = request.form.get('approval_department')
        approval_level = request.form.get('approval_level')
        approvers_list = request.form.getlist('leave_approver[]')
        
        # Create CompanyLeaveApprovers Record
        company_leave_approver = CompanyLeaveApprovers()
        company_leave_approver.company_id = current_user.id
        company_leave_approver.department_name = dept_name
        company_leave_approver.department_approval_level = approval_level
        
        status = company_leave_approver.save()
        
        # Employee Leave Approver
        for i in range(int(approval_level)):
            employee_leave_approver = EmployeeLeaveApprover()
            employee_leave_approver.company_id = current_user.id
            employee_leave_approver.department_name = dept_name
            employee_leave_approver.employee_approval_level = str(i+1)
            employee_leave_approver.employee_details_id = ObjectId(approvers_list[i])
            employee_leave_approver.company_approval_id = company_leave_approver._id
            employee_leave_approver.save()
            # Data in List of Reference
            company_leave_approver.update(push__approvers=employee_leave_approver._id)
            # Employee Details Set is_approver flag to true
            EmployeeDetails.objects(_id=ObjectId(approvers_list[i])).update(is_approver=True)
        
        status = CompanyDetails.objects(user_id=current_user.id).update(push__leave_approvers=company_leave_approver._id)
        if status:
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
        
@company.route('/updateleaveapprover/settings/', methods=['POST'])
def update_leave_approvers():
    if request.method == 'POST':
        dept_name = request.form.get('edit_department_name')
        new_approval_level = request.form.get('edit_approval_level')
        new_approvers_list = request.form.getlist('edit_leave_approver[]')
        edit_leave_app_id = request.form.get('edit_leave_app_id')
        
        # Fetch the current CompanyLeaveApprovers record
        company_leave_approver = CompanyLeaveApprovers.objects(_id=ObjectId(edit_leave_app_id)).first()
        if not company_leave_approver:
            return json.dumps({"status": "failed", "message": "Company leave approver record not found"})

        # Compare new_approvers to existing to find employee that are no more approvers
        for emp_leave_approver in company_leave_approver.approvers:
            if str(emp_leave_approver.employee_details_id._id) not in new_approvers_list:
                # Remove employee from the approvers list
                # Remove employee from the company_leave_approver list
                if hasattr(emp_leave_approver, 'employee_details_id'):
                    emp_details = emp_leave_approver.employee_details_id
                    emp_details.is_approver = False
                    emp_details.save()


        current_approval_level = company_leave_approver.department_approval_level
        
        # Check if the approval level has changed
        if new_approval_level != current_approval_level:
            approval_inc_by = int(new_approval_level) - int(current_approval_level)
            approval_dec_by = int(current_approval_level) - int(new_approval_level)
            
            # Handle increased approval levels
            if approval_inc_by > 0:
                for index in range(int(new_approval_level)):
                    approver_id = new_approvers_list[index] if index < len(new_approvers_list) else None
                    employee_leave_approver = EmployeeLeaveApprover.objects(
                        employee_approval_level=str(index+1),
                        department_name=dept_name,
                        company_id=current_user.id
                    ).first()

                    if employee_leave_approver:
                        if approver_id != str(employee_leave_approver.employee_details_id._id):
                            employee_leave_approver.update(employee_details_id=ObjectId(approver_id))
                            company_leave_approver.update(add_to_set__approvers=employee_leave_approver._id)
                    else:
                        if approver_id:
                            employee_leave_approver = EmployeeLeaveApprover(
                                company_id=current_user.id,
                                department_name=dept_name,
                                employee_approval_level=str(index+1),
                                employee_details_id=ObjectId(approver_id),
                                company_approval_id=company_leave_approver._id
                            )
                            employee_leave_approver.save()
                            company_leave_approver.update(push__approvers=employee_leave_approver._id)
                            emp_details = EmployeeDetails.objects(_id=ObjectId(approver_id)).first()
                            if (emp_details):
                                emp_details.update(is_approver=True)

            
            # Handle decreased approval levels
            elif approval_dec_by > 0:
                for index in range(int(new_approval_level), int(current_approval_level)):
                    employee_leave_approver = EmployeeLeaveApprover.objects(
                        employee_approval_level=str(index+1),
                        department_name=dept_name,
                        company_id=current_user.id
                    ).first()
                    
                    if employee_leave_approver:
                        company_leave_approver.update(pull__approvers=employee_leave_approver._id)
                        employee_leave_approver.delete()
            
            # Update the approval level in the company leave approver record
            company_leave_approver.update(department_approval_level=new_approval_level)

        # Handle case where the number of approvers hasn't changed but approvers themselves need updating
        else:
            for index, approver_id in enumerate(new_approvers_list):
                if index < len(company_leave_approver.approvers):
                    employee_leave_approver = EmployeeLeaveApprover.objects(
                        employee_approval_level=str(index+1),
                        department_name=dept_name,
                        company_id=company_leave_approver.company_id.id
                    ).first()
                    
                    if employee_leave_approver:
                        employee_leave_approver.update(employee_details_id=ObjectId(approver_id))
                        company_leave_approver.update(add_to_set__approvers=employee_leave_approver._id)
                        emp_details = EmployeeDetails.objects(_id=ObjectId(approver_id)).first()
                        if (emp_details):
                            emp_details.update(is_approver=True)

        msg = json.dumps({'status': 'success'})
        return json.loads(msg)


@company.route('/update/leaveapplicationstatus/', methods=['POST'])
def update_leave_application_status():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            disable_leave_application = False if company_details.disable_leave_application else True
            status = company_details.update(disable_leave_application=disable_leave_application)
        if status:
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
   
#Employee List Page
@company.route('/bulk/createopenleaves', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def bulk_upload_open_leaves():
    leave_data = []
    file = request.files.getlist('files')
    # Start Parsing through CSV File
    if file:
            filename = secure_filename(file[0].filename)
            fn = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            fname = fn+str(uuid.uuid4())+file_ext
            if file_ext not in app.config['UPLOAD_FILE_EXTENSIONS']: 
                flash('Please insert document with desired format!')
                return redirect(url_for('company.payroll'))
            if not os.path.exists(app.config['UPLOAD_FILE_FOLDER']):
                os.makedirs(app.config['UPLOAD_FILE_FOLDER'])
            document_path = os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname)
            file[0].save(os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname))
            
        # Dialect helps in grouping together many specific formatting patterns like delimiter, skipinitialspace, quoting, escapechar into a single dialect name.
            csv.register_dialect('myDialect',
                            skipinitialspace=True,
                            quoting=csv.QUOTE_ALL)
            
            with open(document_path, 'r') as file:
                csvreader = csv.DictReader(file, dialect='myDialect')
                for row in csvreader:
                    leave_data.append(dict(row))
            os.remove(document_path)
            
            if leave_data:
               result = add_bulk_open_leaves.delay(leave_data,str(current_user.id))
            #    result = add_bulk_open_leaves(leave_data,str(current_user.id))
            if result:
               message = 'Bulk upload of Open Leaves with uploaded file named ' + filename + ' has '     
               task_scheduled_details = ScheduledBackgroundTask(celery_task_id=result.id,company_id=current_user.id,task_type='employee_open_leave_data',file_name=filename,uploaded_on=datetime.now())
               task_scheduled_details.save()
               return "True"
    else:
        return "False"
    
#Create Employees Open Leave
@celery.task(track_started = True,result_extended=True,name='Employee-Open-Leave-Data')
def add_bulk_open_leaves(leave_data,current_user):
    for employee in leave_data:
        # Todo: Check if the employee exist with employee_id; if exist proceed with next
        employee_details = EmployeeDetails.objects(company_id=ObjectId(current_user),employee_company_details__employee_id=employee['employee_id']).first()
        if employee_details:
            print('Employee Exists')
            # Todo: Next; Check if the Leave Policy Exist; If exist proceed with Next
            company_leave_policy = CompanyLeavePolicies.objects(company_id=ObjectId(current_user),leave_policy_name=employee['leave_type']).first()
            if company_leave_policy:
                # Todo: Next; Check if the Leave policy is already setup for the user; if exist then update the balance else create a new record 
                employee_leave_policy = EmployeeLeavePolicies.objects(company_id=ObjectId(current_user),leave_policy_id=company_leave_policy._id,employee_details_id=employee_details._id).first()
                if employee_leave_policy:
                    # Todo: Update the balance
                    print("Employee Policy Exists") 
                    leave_balance = employee['open_balance'] if employee['open_balance'] else 0
                    employee_leave_policy.update(balance=float(leave_balance))
                else:
                    # Todo: Create a new empployee_leave_policy
                    leave_balance = employee['open_balance'] if employee['open_balance'] else 0
                    
                    print("Employee Doesn't Policy Exists") 
                    employee_leave_policy = EmployeeLeavePolicies()
                    employee_leave_policy.company_id = ObjectId(current_user)
                    employee_leave_policy.employee_details_id = employee_details._id
                    employee_leave_policy.leave_policy_id = company_leave_policy._id
                    employee_leave_policy.balance = float(leave_balance)
                    employee_leave_policy.save()
                    employee_details.update(push__employee_leave_policies=employee_leave_policy._id)
                    
    return True

#Employee List Page
@company.route('/process/attendance', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def process_attendance():
    selected_month = request.form.get('selected_month')
    start_of_month = datetime.strptime(selected_month, '%Y-%m-%d')
    nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
    # subtracting the days from next month date to
    # get last date of current Month
    end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
    
    bulk_attendance_data = []
    # Get all active employees
    employees_details = CompanyDetails.objects(user_id=ObjectId(current_user.id)).first()
    # active_employees = list(filter(lambda x:x['employee_company_details']['status']==True,employees_details.employees))
    active_employees = list(filter(lambda x:x['employee_company_details']['employee_id']=='10006',employees_details.employees))
    
    for current_date in range(int((end_of_the_month - start_of_month).days+1)):
        attendance_date = start_of_month + timedelta(current_date)
        current_attendance_date = (start_of_month + timedelta(current_date)).strftime('%d/%m/%Y')
        for employee in active_employees:
            # Check if the attendance data exist in the Employee Attendance Table
            attendance_data_exist = EmployeeAttendance.objects(employee_id=employee.employee_company_details.employee_id,company_id=current_user.id,attendance_date=attendance_date).first()
            # attendance_data_exist = list(filter(lambda x:(x['employee_id'],x['attendance_date'])==(employee.employee_company_details.employee_id,current_attendance_date),attendance_data))
            if not attendance_data_exist and employee.employee_company_details.type == '0':
                bulk_attendance_data.append(compute_absent_data_new(current_attendance_date,employee.employee_company_details.employee_id,current_user. id))
    if bulk_attendance_data:            
        save_data = EmployeeAttendance.objects.insert(bulk_attendance_data)    
    return "True"

def compute_absent_data_new(current_attendance_date,employee_id,current_user):
    gross_pay_per_day = 0 
    attendance_date = datetime.strptime(current_attendance_date, '%d/%m/%Y')
    e_id = employee_id
    employee = EmployeeDetails.objects(employee_company_details__employee_id=e_id).first()
    
    if not employee.employee_company_details.work_timing:
        default_work_timings = WorkTimings.objects(company_id=ObjectId(current_user),is_default=True).first()
    else:
        default_work_timings = employee.employee_company_details.work_timing
    
    is_holiday = CompanyHolidays.objects(company_id=ObjectId(current_user),occasion_date=attendance_date,is_working_day=False).first()
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee._id,schedule_from=attendance_date).first()
    current_week_day = attendance_date.weekday()
    is_non_working_day = True if (is_holiday or current_week_day in default_work_timings.week_offs or (existing_schedule.work_timings.is_day_off if existing_schedule else False )) else False
    leave_type='absent'
    if is_non_working_day:
        leave_type = 'holiday' if is_holiday else 'absent'
    is_week_off = True if current_week_day in default_work_timings.week_offs else False
    if is_week_off:
        leave_type ='dayoff'
    # data_available = EmployeeAttendance.objects(company_id=ObjectId(current_user),attendance_date=attendance_date,employee_details_id=employee._id)
    # if data_available:
    #     data_available.delete()
    
    # Todo: Check for the absent recors in Scheduler and create adjustments for unpaid absents
    if leave_type== 'absent':          
        start_of_month = datetime. strptime(current_attendance_date, '%d/%m/%Y')
            # start_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
        # subtracting the days from next month date to
        # get last date of current Month
        end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
        
        # has_any_unpaid_leave = CompanyEmployeeSchedule.objects(company_id=current_user,employee_id=employee._id,is_leave=True,schedule_from=attendance_date)
        # for item in has_any_unpaid_leave:
        #     company_leave_policy = CompanyLeavePolicies.objects(leave_policy_name=item.leave_name).first()
        #     if company_leave_policy:
        #         pprint(item.to_json())
        #         if company_leave_policy.leave_type == "unpaid":
        #             # Todo: Create a adjustment record by deducting the off day amount
        #             print("dd")
                    # Check if the adjustment reason is defined if not create a adjustment reason for Unpaid Leaves
        adjustment_reason = CompanyAdjustmentReasons.objects(company_id=current_user,adjustment_reason="Unpaid Leaves").first()
        if not adjustment_reason:
            adjustment_reason = create_adjustment_reason(current_user,"Unpaid Leaves","deduction")
        
        # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
        total_salary = employee.employee_company_details.total_salary
        
        current_month = start_of_month.strftime('%B')

        calendar_working_days = CompanyDetails.objects(user_id=current_user).only('working_days').first()
        # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
        working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))

        no_of_working_days = int(working_days[0]['days']) if working_days else end_of_the_month.days() # By Default Set to 30 Days
                            
        adjustment_amount = round(int(total_salary)/no_of_working_days,0)
        
        adjustment_exists = CompanyPayrollAdjustment.objects(company_id=current_user,
                                                employee_details_id=employee._id,
                                                adjustment_reason_id=adjustment_reason._id,
                                                attendance_date=attendance_date).first()
        if adjustment_exists:
            adjustment_exists.delete()
            
        new_data = CompanyPayrollAdjustment(
                company_id = current_user,
                employee_details_id = employee._id,
                adjustment_reason_id = adjustment_reason._id,
                adjustment_type = adjustment_reason.adjustment_type,
                adjustment_amount = str(adjustment_amount),
                adjustment_on = start_of_month,
                adjustment_month_on_payroll = start_of_month.strftime('%B'),
                adjustment_year_on_payroll =  start_of_month.year,
                attendance_date =  attendance_date,                   
        )   
        new_data.save()
                        
    employee_attendance = EmployeeAttendance()    
    employee_attendance.employee_id = employee.employee_company_details.employee_id
    employee_attendance.employee_details_id = employee._id
    employee_attendance.attendance_date = attendance_date
    employee_attendance.company_id = ObjectId(current_user)
    employee_attendance.leave_name = (existing_schedule.leave_name if hasattr(existing_schedule,'leave_name') else '') if existing_schedule else ''

    # Wages Details End
    if leave_type == 'holiday':
        employee_attendance.attendance_status = "holiday"
        employee_attendance.occasion_for = is_holiday.occasion_for
        # employee_attendance.gross_pay_per_day = 0
        
    elif leave_type == 'dayoff':
        employee_attendance.attendance_status = "dayoff"
        # employee_attendance.gross_pay_per_day = 0
    else:
        if employee.employee_company_details.type == '1':
            employee_attendance.attendance_status = "no-attendance"
        else:    
            employee_attendance.attendance_status = "absent"
        # employee_attendance.gross_pay_per_day = 0
    
    # employee_attendance.gross_pay_per_day = daily_salary
    # employee_attendance.save()
    # return {"status": True} 
    return employee_attendance

def calculate_late_details_new(employee_check_in_time,employee_details,attendance_date):
    
    # Todo: Check the Existing Scheduled Work Timings or get the default Work Timings
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from=attendance_date).first()
    late_by_minutes=0
    if existing_schedule:
        work_timings = WorkTimings.objects(_id=existing_schedule.work_timings._id).first()
    else:
        # Default Work Timings
        if not employee_details.employee_company_details.work_timing:
            work_timings = WorkTimings.objects(company_id=employee_details.company_id,is_default=True).first()
        else:
            work_timings = employee_details.employee_company_details.work_timing
    
        # work_timings = WorkTimings.objects(company_id=employee_details.company_id,is_default=True).first()
    
    office_start_at = work_timings.office_start_at
    late_arrival_later_than = work_timings.late_arrival_later_than
    default_checkin_time = datetime.strptime(office_start_at, '%I:%M %p')
    current_check_in_date = datetime.combine(attendance_date.date(),default_checkin_time.time())
    current_working_day_check_in = current_check_in_date + timedelta(minutes=int(late_arrival_later_than))
    
     # check if the employee checked_in early if he/she is early set checkin time at current day work_start time 
    employee_check_in_time = current_check_in_date if employee_check_in_time <= current_check_in_date else employee_check_in_time
    
    if employee_check_in_time > current_working_day_check_in:
        late_by_time = employee_check_in_time-current_check_in_date
        late_by_minutes = late_by_time.total_seconds()/60
        # Todo: Create a EmployeeTimeRequest record with the dedicated approver of the department
    return int(late_by_minutes)

def calculate_early_departure_details_new(employee_check_out_time,employee_details,attendance_date):
    
    # Todo: Check the Existing Scheduled Work Timings or get the default Work Timings
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,schedule_from=attendance_date).first()
    early_by_minutes=0
    if existing_schedule:
        work_timings = WorkTimings.objects(_id=existing_schedule.work_timings._id).first()
    else:
        # Default Work Timings
        if not employee_details.employee_company_details.work_timing:
            work_timings = WorkTimings.objects(company_id=employee_details.company_id,is_default=True).first()
        else:
            work_timings = employee_details.employee_company_details.work_timing
        # Default Work Timings
        # work_timings = WorkTimings.objects(company_id=employee_details.company_id,is_default=True).first()
    
    office_end_at = work_timings.office_end_at
    early_departure_earliar_than = work_timings.early_departure_earliar_than
    default_checkout_time =  datetime.strptime(office_end_at, '%I:%M %p')

    # This Condition will check if the checkout time is next day of the checkin time 
    if "AM" in office_end_at:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date()+timedelta(days=1),default_checkout_time.time())
        # Checkout with Grace
        current_working_day_check_out = current_check_out_date + timedelta(minutes=-int(early_departure_earliar_than))
    else:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date(),default_checkout_time.time())
        # Checkout with Grace
        current_working_day_check_out = current_check_out_date + timedelta(minutes=-int(early_departure_earliar_than))
    
    if employee_check_out_time < current_working_day_check_out:
        early_by_time = current_check_out_date-employee_check_out_time
        early_by_minutes = early_by_time.total_seconds()/60
    
    return int(early_by_minutes)

@company.route('/createtimeapprover/settings/', methods=['POST'])
def create_time_approvers():
    if request.method == 'POST':
        dept_name = request.form.get('time_approval_department')
        time_approver = request.form.get('time_approver')
        
        # Create CompanyLeaveApprovers Record
        company_time_approver = CompanyTimeApprovers()
        company_time_approver.company_id = current_user.id
        company_time_approver.department_name = dept_name
        company_time_approver.approver = ObjectId(time_approver)
        company_time_approver.save()
        EmployeeDetails.objects(_id=ObjectId(time_approver)).update(is_time_approver=True)
        status = CompanyDetails.objects(user_id=current_user.id).update(push__time_approvers=company_time_approver._id)
        if status:
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
        
def create_time_request(company_id,attendance_id,department,request_type):
    # Todo: Check for the time approver if exist create record else return false; 
    company_time_approver = CompanyTimeApprovers.objects(company_id=company_id,department_name=department).first()
    if company_time_approver:
        employee_time_request = EmployeeTimeRequest()
        employee_time_request.company_id = company_id
        employee_time_request.attendance_id = attendance_id
        employee_time_request.approver_id = company_time_approver._id
        employee_time_request.request_type = request_type
        
        employee_time_request.save()
        
    return True

@company.route('/leaveadjustments', methods=['GET', 'POST'])
@login_required
def leave_adjustments():
    if request.method == 'POST':
        attendance_range = request.form.get('daterange').split(' - ')
        start_date = datetime. strptime(attendance_range[0], '%d/%m/%Y')
        end_date = datetime. strptime(attendance_range[1], '%d/%m/%Y')
        adjustment_details = EmployeeLeaveAdjustment.objects(company_id=current_user.id, created_at__gte=start_date, created_at__lte=end_date)
        return render_template('company/adjustments/leave_adjustments.html',adjustment_details=adjustment_details, start=start_date, end=end_date)
    
    now = datetime.today()
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Get the last day of the current month
    last_day = calendar.monthrange(now.year, now.month)[1]

    # Get the end date of the current month
    end_date = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    adjustment_details = EmployeeLeaveAdjustment.objects(company_id=current_user.id, created_at__gte=start_date, created_at__lte=end_date)
    return render_template('company/adjustments/leave_adjustments.html',adjustment_details=adjustment_details, start=start_date, end=end_date)

@company.route('/create/leaveadjustments', methods=['GET','POST'])
@login_required
def create_leave_adjustments():
    if request.method == 'POST':
        flag = False
        employee_details_id = request.form.get('employee_name')
        # start_of_month = datetime. strptime(request.form.get('selected_month'), '%Y-%m-%d')  if request.form.get('selected_month') else datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        total_adjustments = len(request.form.getlist("adjustment__leave_type[]"))
        if total_adjustments > 0:
            adjustment_leave_type_list = request.form.getlist('adjustment__leave_type[]')
            adjustment_days_list = request.form.getlist('adjustment_days[]')
            adjustment_comment_list = request.form.getlist('adjustment_comment[]')
            
            for item in range(0,total_adjustments):
                adjustment_leave_type = adjustment_leave_type_list[item]
                adjustment_days = adjustment_days_list[item]
                adjustment_comment = adjustment_comment_list[item]
                
                if adjustment_leave_type:
                    flag = True
                    adjustment_type_details = EmployeeLeavePolicies.objects(_id=ObjectId(adjustment_leave_type)).first()
                    if adjustment_type_details:
                        # Create a new record for Leave adjustment
                        new_data = EmployeeLeaveAdjustment(
                                   company_id = current_user.id,
                                   employee_details_id = ObjectId(employee_details_id),
                                   employee_leave_pol_id = adjustment_type_details._id,
                                   adjustment_type = 'increment' if float(adjustment_days) > 0 else 'decrement',
                                   adjustment_days = adjustment_days,
                                   adjustment_comment = adjustment_comment,
                                   before_adjustment=  str(adjustment_type_details.balance),
                                   after_adjustment = str(float(adjustment_type_details.balance)+float(adjustment_days))            
                        )
                        status = new_data.save()
                        company_details =  EmployeeLeavePolicies.objects(company_id=current_user.id,_id=ObjectId(adjustment_leave_type)).update(push__employee_leave_adjustments=new_data._id,balance=float(adjustment_type_details.balance)+float(adjustment_days)) 
                        
            if flag:
                flash('Adjustments Created Successfully!', 'success')
                return redirect(url_for('company.create_leave_adjustments'))
            else:
                flash('Something went Wrong. Please try again!', 'danger')
                return redirect(url_for('company.create_leave_adjustments'))
        
    else:
        company_details = CompanyDetails.objects(user_id=current_user.id).only('employees','adjustment_reasons').first()
        start_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        return render_template('company/adjustments/create_leave_adjustment.html',company_details=company_details,start_of_month=start_of_month)


@company.route('/update_leave_application', methods=['POST'])
def modify_leave_application():
    try:
        requestData = request.get_json()  # Parses the JSON body
        print(requestData)
        
        # Process the request data as needed
        leave_application = EmployeeLeaveApplication.objects(_id=ObjectId(requestData['id'])).first()
        leave_adjustment= leave_application.leave_adjustment

        # Convert date strings to datetime objects
        new_from = datetime.strptime(requestData['new_from'].replace('-', '/'), '%Y/%m/%d')
        new_to = datetime.strptime(requestData['new_to'].replace('-', '/'), '%Y/%m/%d')
        old_from = datetime.strptime(requestData['from'], '%d/%m/%Y')
        old_to = datetime.strptime(requestData['to'], '%d/%m/%Y')

        if (new_from > new_to):
            return jsonify(
                {
                    "status": "error",
                    "message": "Start Date can't he bigger then from date."
                }
                )
        

        no_of_days = (new_to - new_from).days + 1

        if (leave_adjustment):
            before_adjustment = leave_application.balance_before_approval
            after_adjustment = str(float(before_adjustment) - int(no_of_days))
            leave_adjustment.update(adjustment_days =str(no_of_days),
                                    before_adjustment=str(before_adjustment),
                                    after_adjustment=after_adjustment,
                                    adjustment_comment = requestData['adjustment_comment'],
                                    modified_by=current_user.id, modified_on=datetime.now())

            leave_adjustment.save()

            current_leave_balance = float(leave_application.balance_before_approval)
            #undoing leave balance so we can do the new balance

            if (current_leave_balance >= no_of_days):
                new_balance =current_leave_balance - no_of_days
            
                leave_policy_details = EmployeeLeavePolicies.objects(_id=leave_application.employee_leave_policy._id).first()
                if leave_policy_details:
                    leave_policy_details.update(balance=new_balance)

                leave_application.update(leave_from=new_from, leave_till=new_to, no_of_days=str(no_of_days),
                                modified_by=current_user.id, modified_on=datetime.now(),
                                leave_status="modified", balance_before_approval=str(before_adjustment),
                                balance_after_approval=after_adjustment,approved_on=datetime.now())
                leave_application.save()

                work_timings = WorkTimings.objects(is_day_off=True,company_id=leave_application.company_id.id).first()
                
                # Add new leave schedules
                if new_from < old_from:
                    add_leave_schedules(new_from, old_from - timedelta(days=1), leave_application, work_timings)
                if new_to > old_to:
                    add_leave_schedules(old_to + timedelta(days=1), new_to, leave_application, work_timings)

                # Remove outdated leave schedules
                if new_from > old_from:
                    remove_leave_schedules(old_from, new_from - timedelta(days=1), leave_application, work_timings)
                if new_to < old_to:
                    remove_leave_schedules(new_to + timedelta(days=1), old_to, leave_application, work_timings)

            else:

                messgae = 'Asking more leave than what is avalable'

                response = {
                    "status": "error",
                    "message": messgae
                }
            
                return jsonify(response), 200

        else:

            message = """This leave application can't be modified, try creating a new leave request.
            Hint: Leave applications that were approved before the patch this feature was rolled in 
            can't be modified."""

            response = {
                "status": "error",
                "message": message
            }
            
            return jsonify(response), 200

        response = {
            "status": "success",
            "message": "successfully modified leave application",
        }
        return jsonify(response), 200
    except Exception as e:
        # Handle errors
        print(e)
        response = {
            "status": "error",
            "message": str(e)
        }
        return jsonify(response), 200


@company.route('/getemployeesleavepolicies', methods=['GET'])
def get_employees_leave_policies():
    selected_employee = request.args.get('selected_employee')
    leave_policies = EmployeeLeavePolicies.objects(company_id=current_user.id,employee_details_id=ObjectId(selected_employee))
    if leave_policies:
        details = {}
        data = []
        for item in leave_policies:
            details = {
                'emp_leave_policy_id' : str(item._id),
                'leave_policy_name' : item.leave_policy_id.leave_policy_name,
                'balance' :  item.balance
            }
            data.append(details)
        msg =  json.dumps({"status":"success","details":data})
        # attendance_data = loads(attendance_details.to_json())
        # msg =  json.dumps({'status':'success','details':leave_policies.to_json()})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml
    
    
@company.route('/leavesapplications')
@login_required
def leaves_applications():
    leave_applications = EmployeeLeaveApplication.objects(company_id=current_user.id)
    return render_template('company/leaves_applications.html',leave_applications=leave_applications)

@company.route('/payroll', methods=['POST','GET'])
@login_required
@roles_accepted('admin','company')
def payroll_view(): 
    sub_company = None
    selected_sub_company=None
    if request.method=="POST":
        selected_of_month = datetime. strptime(request.form.get('selected_month'), '%Y-%m-%d')  if request.form.get('selected_month') else datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        sub_company = request.form.get('sub_company')
        selected_sub_company = request.form.get('sub_company')
        if selected_sub_company == "all company":
            sub_company = None  # Pass None when "All Company" is selected
        else:
            sub_company = selected_sub_company 
    else:
        selected_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
    
    payroll_month = selected_of_month.strftime('%B');
    payroll_year = selected_of_month.year;

    payroll_details = None
    if (sub_company):
        payroll_details = CompanyPayroll.objects(company_id=current_user.id,payroll_month=payroll_month,payroll_year=payroll_year, working_sub_company=ObjectId(sub_company))
    else:
        payroll_details = CompanyPayroll.objects(company_id=current_user.id,payroll_month=payroll_month,payroll_year=payroll_year)


    company_details = CompanyDetails.objects(user_id=current_user.id).only('company_name','company_logo', 'sub_companies','Currency').first()
    return render_template('company/payroll_view.html',start_of_month=selected_of_month,
                           payroll_details=payroll_details,company_details=company_details, 
                           sub_company=sub_company, selected_sub_company = selected_sub_company)


def dereference_dbrefs(scrs, className):
    for key, value in scrs.items():
        if isinstance(value, DBRef):
            scrs[key] = className.objects(id=value.id).first()
    return scrs



@company.route('/wps', methods=['POST','GET'])
@login_required
@roles_accepted('admin','company')
def payroll_wps_view(): 
    sub_company = None
    selected_sub_company=None
    if request.method == "POST":
        selected_month = datetime.strptime(request.form.get('selected_month'), '%Y-%m-%d') if request.form.get('selected_month') else datetime.today().replace(day=1, minute=0, hour=0, second=0, microsecond=0)
        selected_sub_company = request.form.get('sub_company')

        if selected_sub_company == "all company":
            sub_company = None  # Pass None when "All Company" is selected
        else:
            sub_company = selected_sub_company 
    else:
        selected_month = datetime.today().replace(day=1, minute=0, hour=0, second=0, microsecond=0)
    
    payroll_month = selected_month.strftime('%B')
    payroll_year = selected_month.year

    nxt_mnth = selected_month.replace(day=28) + timedelta(days=4)
    end_of_the_month = nxt_mnth - timedelta(days=nxt_mnth.day)

    sdr_details = CompanySif.objects(company_id=current_user.id, sif_month=selected_month, sif_year=payroll_year, sif_type="SCR").first()

    company_details = CompanyDetails.objects(user_id=current_user.id).only('sub_companies').first()
    company_details_name = CompanyDetails.objects(user_id=current_user.id).first()
    sif_record = SIF.objects(start_date=selected_month, end_date=end_of_the_month, company = company_details.id).first()

    company_name_details = company_details_name.company_name

    if sub_company:
        payroll_details = CompanyPayroll.objects(company_id=current_user.id, payroll_month=payroll_month, payroll_year=payroll_year, working_sub_company=ObjectId(sub_company))
        sif_record = SIF.objects(sub_company=ObjectId(sub_company), start_date=selected_month, end_date=end_of_the_month).first()
        
        if sif_record:
            edrs_valus, scrs_values, table_head, scrs = get_data_for_WPS_view(sif_record)

            edrs_valus = preprocess_data(edrs_valus) #Added By Ashiq Date : 19/sep/2024 Issues : Date formate 


            # return render_template('company/payroll_wps_view_new.html', selected_sub_company = ObjectId(sub_company),
            #                        start_of_month=selected_month, company_details=company_details,
            #                        edr_data=sif_record.EDR_records, scr_data=scrs, sdr_details=sdr_details,
            #                        table_head = table_head, edrs_valus = edrs_valus, scrs_values = scrs_values
            #                        )   
            return render_template(
                    'company/payroll_wps_view.html',
                    company_details=company_details,
                    start_of_month=selected_month,
                    selected_sub_company=selected_sub_company,
                    payroll_details=payroll_details,
                    sdr_details=sdr_details,
                    edr_data=sif_record.EDR_records, 
                    scr_data=scrs,
                    table_head = table_head, 
                    edrs_valus = edrs_valus, 
                    scrs_values = scrs_values,
                    company_name_details = company_name_details
                )   #Added By ashiq  Date:13/sep/2024  Issues  : wps 
        
    else:
        sub_company = ObjectId(request.form.get('sub_company')) if sub_company else None

        payroll_details = CompanyPayroll.objects(company_id=current_user.id, payroll_month=payroll_month, payroll_year=payroll_year)

        if sif_record and not sif_record.sub_company:
            #Added By Ashiq Date : 13/sep/2024 Issues : wps 
            edrs_valus, scrs_values, table_head, scrs = get_data_for_WPS_view(sif_record)
            cleaned_company_name =  company_name_details .replace('\xa0', ' ').strip()
            edrs_valus = preprocess_data(edrs_valus)  #Added By Ashiq Date : 19/sep/2024 Issues : Date formate 
           
            if cleaned_company_name  == 'BAIT AL FEN GEN. TR.':
                return render_template(
                    'company/payroll_wps_view.html',
                    company_details=company_details,
                    start_of_month=selected_month,
                    selected_sub_company=selected_sub_company,
                    payroll_details=payroll_details,
                    sdr_details=sdr_details,
                    company_name_details = company_name_details 

                )
            else  :
                return render_template(
                    'company/payroll_wps_view.html',
                    company_details=company_details,
                    start_of_month=selected_month,
                    selected_sub_company=selected_sub_company,
                    payroll_details=payroll_details,
                    sdr_details=sdr_details,
                    edr_data=sif_record.EDR_records, 
                    scr_data=scrs,
                    table_head = table_head, 
                    edrs_valus = edrs_valus, 
                    scrs_values = scrs_values,
                    company_name_details = company_name_details
                )

        # if sif_record and not sif_record.sub_company:
        #     edrs_valus, scrs_values, table_head, scrs = get_data_for_WPS_view(sif_record)

        #     return render_template('company/payroll_wps_view.html', company_details=company_details, start_of_month=selected_month,
        #                     selected_sub_company = sub_company, payroll_details=payroll_details, sdr_details=sdr_details,)
        
        #     return render_template('company/payroll_wps_view_new.html', selected_sub_company = ObjectId(sub_company),
        #                             start_of_month=selected_month, company_details=company_details,
        #                             edr_data=sif_record.EDR_records, scr_data=scrs, sdr_details=sdr_details,
        #                             table_head = table_head, edrs_valus = edrs_valus, scrs_values = scrs_values
        #                             )

    return render_template('company/payroll_wps_view.html', company_details=company_details, start_of_month=selected_month,
                            selected_sub_company = selected_sub_company, payroll_details=payroll_details, sdr_details=sdr_details, company_name_details = company_name_details)

@company.route('/payrollinfo', methods=['GET'])
def get_payroll():
    employee_id = request.args.get('employee_id')
    selected_month =  request.args.get('selected_month')
    selected_year =  request.args.get('selected_year')
    
    # start_of_month = selected_month.replace(year=selected_month.year)
    # end_of_month = selected_month.replace(day = calendar.monthrange(start_of_month.year, start_of_month.month)[1])
    additions = []
    deductions = []
    payroll_data = CompanyPayroll.objects(company_id=current_user.id,payroll_month=selected_month,payroll_year=int(selected_year),employee_details_id=ObjectId(employee_id)).first()
    if payroll_data:
        if payroll_data.adjustment_additions:
            for item in payroll_data.adjustment_additions:
                additions.append({
                                'reason':item.adjustment_reason_id.adjustment_reason,
                                'amount':item.adjustment_amount
                })
        if payroll_data.adjustment_deductions:
            for item in payroll_data.adjustment_deductions:
                deductions.append({
                                'reason':item.adjustment_reason_id.adjustment_reason,
                                'amount':item.adjustment_amount
                })
    #     gross_pay = payroll_data.total_salary + additions - deductions
    # sum(c.a for c in c_list)
    # print(gp_with_deduction)
    employee_details = EmployeeDetails.objects(_id=ObjectId(employee_id)).exclude('employee_bank_details','documents').first()

    company_details = CompanyDetails.objects(user_id=current_user.id).only('Currency').first()
    
    if payroll_data and employee_details:   
        employee_data = loads(employee_details.to_json())
        js_data = {
                'status': 'success',
                'employee_details':employee_data,
                'payroll_data':loads(payroll_data.to_json()),
                # 'gross_pay':gross_pay,
                'additions':additions,
                'deductions':deductions,
                'company_details':company_details.Currency
                }
    else:
        employee_details = EmployeeDetails.objects(_id=ObjectId(employee_id)).exclude('employee_bank_details','documents').first()
        employee_data = loads(employee_details.to_json())
        js_data = {
                'status': 'failed',
                'employee_details':employee_data,
                }
    return dumps(js_data)   

@company.route('/monthlyattendancereport',methods=["GET","POST"])
@login_required
@roles_accepted('admin','company')
def monthly_attendance_report():
    company_employees = get_company_employees(current_user)

    if request.method=="POST":
        # company_employees = CompanyDetails.objects(user_id=current_user.id).only('employees').first()
        attendance_range = request.form.get('daterange').split(' - ')
        employee_details_id = request.form.get('employee_id')
        start_date = datetime. strptime(attendance_range[0], '%d/%m/%Y')
        end_date = datetime. strptime(attendance_range[1], '%d/%m/%Y')
        total_hrs_worked = timedelta()
        data = []
        if employee_details_id:
            employee_attendance = EmployeeAttendance.objects(company_id=current_user.id,attendance_date__gte=start_date,attendance_date__lte=end_date,employee_details_id=ObjectId(employee_details_id))

            set_of_absent_days = get_set_of_absent_days(employee_attendance, start_date, end_date)
            
            for i in employee_attendance:
                if "total_hrs_worked" in i:
                    (h, m, s) = i.total_hrs_worked.split(':')
                    d = timedelta(hours=int(h), minutes=int(m), seconds=float(s))
                    total_hrs_worked += d

            start_date_counter = start_date

            for item in employee_attendance:
                if (item.attendance_date != start_date_counter):
                    if start_date_counter in set_of_absent_days:
                        absent_record = EmployeeAttendance(attendance_status="absent", attendance_date = start_date_counter,
                                                            employee_details_id=item.employee_details_id)
                        data.append(absent_record)
                
                day = timedelta(days=1)
                start_date_counter += day

                sum_of_break = sum(bh.break_difference for bh in item.break_history if bh.already_ended)
                if "total_hrs_worked" in item:
                    hrs_worked_str = item.total_hrs_worked.split(', ')[-1]  # Extracting the time component
                    (days_str, time_str) = hrs_worked_str.split(' day, ') if 'day' in hrs_worked_str else (0, hrs_worked_str)
                    (h, m, s) = time_str.split(':')
                    days = int(days_str) if 'day' in hrs_worked_str else 0
                    d = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
                    if sum_of_break > 0:
                        item.total_hr_worked_excluding = d - timedelta(minutes=int(sum_of_break))
                    else:
                        item.total_hr_worked_excluding = d
                    total_hrs_worked += d
                    

                data.append(item)
            return render_template('company/attendance_report.html',employee_attendance=data,
                                   selected_emp=ObjectId(employee_details_id),start=start_date,
                                   end=end_date,total_hrs_worked=chop_microseconds(total_hrs_worked),
                                   employees_details=company_employees)
                    
        else:
            employee_attendance = EmployeeAttendance.objects(company_id=current_user.id,attendance_date__gte=start_date,attendance_date__lte=end_date)
                    
            for item in employee_attendance:

                sum_of_break = sum(bh.break_difference for bh in item.break_history if bh.already_ended)
                if "total_hrs_worked" in item:
                    hrs_worked_str = item.total_hrs_worked.split(', ')[-1]  # Extracting the time component
                    (days_str, time_str) = hrs_worked_str.split(' day, ') if 'day' in hrs_worked_str else (0, hrs_worked_str)
                    (h, m, s) = time_str.split(':')
                    days = int(days_str) if 'day' in hrs_worked_str else 0
                    d = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
                    if sum_of_break > 0:
                        item.total_hr_worked_excluding = d - timedelta(minutes=int(sum_of_break))
                    else:
                        item.total_hr_worked_excluding = d
                    total_hrs_worked += d

                data.append(item)
            return render_template('company/monthly_attendance_report.html',employee_attendance=data,
                               start=start_date,end=end_date, employees_details=company_employees)
        # attendance_date = datetime. strptime(request.form.get('attendance_range[0]'), '%d/%m/%Y')  if request.form.get('attendance_date') else datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
    else:

        # company_employees = CompanyDetails.objects(user_id=current_user.id).only('employees','clock_in_options').first()
        start_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
        end_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
        employee_attendance = EmployeeAttendance.objects(company_id=current_user.id,attendance_date__gte=start_date,attendance_date__lte=end_date)
        data =[]


        for item in employee_attendance:
            sum_of_break = sum(bh.break_difference for bh in item.break_history if bh.already_ended)
            if "total_hrs_worked" in item:
                hrs_worked_str = item.total_hrs_worked.split(', ')[-1]  # Extracting the time component
                (days_str, time_str) = hrs_worked_str.split(' day, ') if 'day' in hrs_worked_str else (0, hrs_worked_str)
                (h, m, s) = time_str.split(':')
                days = int(days_str) if 'day' in hrs_worked_str else 0
                d = timedelta(days=days, hours=int(h), minutes=int(m), seconds=float(s))
                if sum_of_break > 0:
                    item.total_hr_worked_excluding = d - timedelta(minutes=int(sum_of_break))
                else:
                    item.total_hr_worked_excluding = d

            data.append(item)
        return render_template('company/monthly_attendance_report.html',employee_attendance=data,start=start_date,end=end_date, employees_details=company_employees)


@company.route('/assign/roles/', methods=['POST'])
def assign_roles():
    if request.method == 'POST':
        employee_list = request.form.getlist('employees[]')
        roles_list = request.form.getlist('roles[]')

    if employee_list and roles_list:
        for employee_detail_id in employee_list:
            for role in roles_list:
                role_details = Role.objects(name=role).first()
                if not role_details:
                    role_details = Role()
                    role_details.name=role
                    role_details.save()
                # todo: Create a company assigned role record; then assign role on user level
                employee_details = EmployeeDetails.objects(_id=ObjectId(employee_detail_id)).first()
                # todo: Check if the user is already assigned with the role; if not assign;
                    
                if employee_details:
                    role_exists = CompanyRole.objects(employee_details_id=employee_details._id,company_id=current_user.id,role = role_details._id).first()
                    if not role_exists:
                        company_role = CompanyRole()
                        company_role.employee_details_id = employee_details._id
                        company_role.company_id = current_user.id
                        company_role.role = role_details._id
                        status = company_role.save()
                        
                        if status:
                        # todo: push company assigned reocrd to company document(company_roles)
                            CompanyDetails.objects(user_id=current_user.id).update(add_to_set__company_roles=company_role._id)
                        # todo: Assign the role to user 
                            User.objects(id=ObjectId(employee_details.user_id.id)).update(add_to_set__roles=role_details._id)

    if True:
        msg =  json.dumps({'status':'success'})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml
    
@company.route('/activitylog',methods=["GET","POST"])
@login_required
def activity_log():
    if request.method=="POST":
        attendance_range = request.form.get('daterange').split(' - ')
        start_date = datetime.strptime(attendance_range[0], '%d/%m/%Y')
        end_date = datetime.strptime(attendance_range[1], '%d/%m/%Y').replace(minute=0, hour=0, second=0,microsecond=0)
        activitylogs = ActivityLog.objects(company_id=current_user.id,created_at__gt=start_date,created_at__lte=end_date+timedelta(days=1))
    else:
        start_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
        end_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
        activitylogs = ActivityLog.objects(company_id=current_user.id,created_at__gte=start_date,created_at__lte=end_date+timedelta(days=1))
    
    return render_template('company/activity_logs.html',activitylogs=activitylogs,start=start_date,end=end_date)


@company.route('/memos',methods=["GET","POST"])
@login_required
def memos():
    if request.method=="POST":
        memo_title = request.form.get('memo_title') 
        memo_description = request.form.get('memo_description')
        memo_priority = request.form.get('memo_priority')
        memo_expiry = datetime.strptime(request.form.get('memo_expiry'), '%d/%m/%Y') if request.form.get('memo_expiry') else datetime.today().replace(minute=0, hour=0, second=0,microsecond=0) + timedelta(days=30)
        
        has_file = request.form.get('has_file')
        
        memo_details = CompanyMemo()
        memo_details.company_id = current_user.id
        memo_details.memo_title = memo_title
        memo_details.memo_description = memo_description
        memo_details.memo_priority = memo_priority
        memo_details.memo_expiry = memo_expiry
        if has_file == 'true':
            file = request.files['files']
            if file:
                memo_attachment = upload_memo_document(file)
                memo_details.memo_attachment = memo_attachment
        status = memo_details.save()
        CompanyDetails.objects(user_id=current_user.id).update(add_to_set__company_memos=memo_details._id)
        # Send email to employees notifying the memo created by the company
        send_memo_emails.delay(str(current_user.id),str(memo_details._id))
        if True:
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml   
    else:
        memo_details = CompanyMemo.objects(company_id=current_user.id)
        return render_template('company/memo.html',memo_details=memo_details)

def upload_memo_document(file):
    fname=''
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1]
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in app.config['UPLOAD_DOCUMENT_EXTENSIONS']: 
            flash('Please insert document with desired format!')
            return redirect(url_for('company.add_employee'))
        if not os.path.exists(app.config['UPLOAD_MEMO_DOCUMENT_FOLDER']):
            os.makedirs(app.config['UPLOAD_MEMO_DOCUMENT_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_MEMO_DOCUMENT_FOLDER'], fname))
    return fname;

#Delete Event
@company.route('/deletememo', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def delete_memo():
    # Delete reference employee object
    memo_id = request.form.get('id')
    memo_details = CompanyMemo.objects(_id=ObjectId(memo_id)).first()
    
    if memo_details:
        status = memo_details.delete()
        company_details=CompanyDetails.objects(user_id=current_user.id).update_one(pull__company_memos=ObjectId(memo_id))
        if company_details:
            msg =  json.dumps({"status":"success"})
            msghtml = json.loads(msg)
            return msghtml
    # Failed
    msg =  json.dumps({"status":"failed"})
    msghtml = json.loads(msg)
    return msghtml

#Employee List Page
@company.route('/bulk/bankdetails', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def bulk_upload_bank_details():
    bank_data = []
    file = request.files.getlist('files')
    # Start Parsing through CSV File
    if file:
            filename = secure_filename(file[0].filename)
            fn = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            fname = fn+str(uuid.uuid4())+file_ext
            if file_ext not in app.config['UPLOAD_FILE_EXTENSIONS']: 
                flash('Please insert document with desired format!')
                return redirect(url_for('company.payroll'))
            if not os.path.exists(app.config['UPLOAD_FILE_FOLDER']):
                os.makedirs(app.config['UPLOAD_FILE_FOLDER'])
            document_path = os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname)
            file[0].save(os.path.join(app.config['UPLOAD_FILE_FOLDER'], fname))
            
        # Dialect helps in grouping together many specific formatting patterns like delimiter, skipinitialspace, quoting, escapechar into a single dialect name.
            csv.register_dialect('myDialect',
                            skipinitialspace=True,
                            quoting=csv.QUOTE_ALL)
            
            with open(document_path, 'r') as file:
                csvreader = csv.DictReader(file, dialect='myDialect')
                for row in csvreader:
                    bank_data.append(dict(row))
            os.remove(document_path)
            
            if bank_data:
            #    result = add_bulk_open_leaves.delay(bank_data,str(current_user.id))
               result = add_bulk_bank_details(bank_data,str(current_user.id))
            # if result:
            #    task_scheduled_details = ScheduledBackgroundTask(celery_task_id=result.id,company_id=current_user.id,task_type='bank_details',file_name=filename,uploaded_on=datetime.now())
            #    task_scheduled_details.save()
            return "True"
    else:
        return "False"
    
#Create Employees Open Leave
# @celery.task(track_started = True,result_extended=True,name='Bank-Details-Data')
def add_bulk_bank_details(bank_data, current_user):
    for data in bank_data:
        # Skip records with null or missing values
        if not data.get('Bank'):
            continue

        # Check if bank details already exist
        bank_details = BankDetails.objects(bank_name=data['Bank'], routing_code=data['Routing_Number']).first()
        if not bank_details:
            new_bank_details = BankDetails()
            new_bank_details.bank_name = data['Bank']
            new_bank_details.routing_code = data['Routing_Number']

            # Assign ObjectId directly
            new_bank_details.company_id = ObjectId(str(current_user))

            new_bank_details.save()
    return True

@company.route('/update/sif/', methods=['POST'])
def update_siF_details():
    if request.method == 'POST':
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            company_details.company_unique_id = request.form.get('company_unique_id')
            company_details.company_routing_code = request.form.get('company_routing_code')
            company_details.save()
            flash('Company SIF Settings Updated Successfully!', 'success')
            return redirect(url_for('company.company_settings'))
    else:
        return render_template('company/settings.html') 

@company.route('/calculateEOSB/', methods=['POST'])
def calculate_EOSB():
    if request.method == 'POST':
            employee_details_id = request.form.get('employee_details_id')
            date_of_dept = request.form.get('date_of_departure')
            reason_for_dept = request.form.get('reason_for_departure')
            contract_type = request.form.get('contract_type')
            graduity_amount = 0.0
            employee_details = EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
            per_day_basic_pay = float(employee_details.employee_company_details.basic_salary)/30.0
            
            if employee_details:
                date_of_joining = datetime.strptime(employee_details.employee_company_details.date_of_joining, '%d/%m/%Y')
                date_of_dept = datetime.strptime(request.form.get('date_of_departure'), '%d/%m/%Y')
                served_days = (date_of_dept - date_of_joining).days
                
                served_years = int(served_days/365)
                served_day = served_days%365
                if served_years < 1:
                    # Is not entitled
                    msg =  '{"status":"failed"}'
                    msghtml = json.loads(msg)
                    return msghtml

                if contract_type == "limited":
                    # Todo: Limited Contract Type
                    # Todo: If an employee has served for more than one year but less than five years, he is entitled to full gratuity pay based on 21 days’ salary for each year of work.
                    if served_years>=1 and served_years <5:
                        # Todo: Desired Formula -> perday basic salary * 21 * no of years served
                        graduity_amount = per_day_basic_pay*21*served_years
                    
                    # Todo: If an employee has served more than five years, he is entitled to full gratuity of 30 days’ salary for each year of work following the first five years.
                    if served_years >=5:
                        # Todo: Desired Formula -> perday basic salary * 30 * no of years served
                        graduity_amount = per_day_basic_pay*30*served_years
                # Todo: New Unlimited Contract Type
                if contract_type == "new_unlimited":
                # Todo: If a worker has served for less than 1 year, he is not entitled to any gratuity pay.
                    # Todo: If a worker has served for more than 1 year but less than 5 years, he is entitled to full gratuity pay based on 21 days' salary for each year of work.
                    if served_years>=1 and served_years <5:
                       graduity_amount = per_day_basic_pay*21*served_years
                        
                    # Todo: If a worker has served more than 5 years, he is entitled to full gratuity of 30 days' salary for each year of work following the first five years.
                    if served_years >=5:
                            # Todo: Desired Formula -> perday basic salary * 30 * 5 years
                            initial_graduity_amount = per_day_basic_pay*21*5
                            above_years = served_years-5
                            graduity_amount = initial_graduity_amount + (per_day_basic_pay*30*above_years)
                            
                details = {
                'graduity_amount' : graduity_amount,
                'served_years' : served_years,
                'days':served_day,
                'per_day_basic_pay' :  per_day_basic_pay
                }         
                # Todo: Unlimited Contract Type
                msg =  json.dumps({"status":"success","details":details})
                msghtml = json.loads(msg)
                return msghtml
            else:
                msg =  '{"status":"failed"}'
                msghtml = json.loads(msg)
                return msghtml
    else:
        return render_template('company/settings.html') 
    
@company.route('/endofservice')
@login_required
def end_of_service():
    employees_details = CompanyDetails.objects(user_id=current_user.id).first()
    return render_template('company/end_of_service.html',employees_details=employees_details)

@company.route('/getemployeesdetails', methods=['GET'])
def get_employees_details():
    selected_employee = request.args.get('selected_employee')
    employee_details = EmployeeDetails.objects(company_id=current_user.id,_id=ObjectId(selected_employee)).first()
    details = {}
    d = []
    for item in employee_details.employee_leave_policies:
        details = {
            'emp_leave_policy_id' : str(item._id),
            'leave_policy_name' : item.leave_policy_id.leave_policy_name,
            'balance' :  item.balance,
            'type': str.upper(item.leave_policy_id.leave_type)
        }
        d.append(details)
    if employee_details:
        msg =  json.dumps({"status":"success","details":employee_details.to_json(),"leave_policies":d})
        return msg
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml
    
#Employee List Page
@company.route('/leaveslist')
@login_required
# @roles_accepted('admin','company','peoplemanager')
def leaves_list():
    employees = CompanyDetails.objects(user_id=current_user.id).only('employees','leave_policies').first()
    return render_template('company/leaves_list.html', employees=employees)

@company.route('/createletter',methods=["GET","POST"])
@login_required
def create_letter_template():
    if request.method == "POST":
        print(request.form.get('editor_values'))
        data= request.form.get('editor_values')
        
        template_loader = jinja2.FileSystemLoader('project/templates/')
        template_env = jinja2.Environment(loader=template_loader)

        template = template_env.get_template('company/test.html')
        output_text = template.render(data=data)

        path_wkhtmltopdf = r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
        pdfkit.from_string(output_text, 'pdf_generated.pdf', configuration=config)  
        
        
        return True
    else:
        employees_details = CompanyDetails.objects(user_id=current_user.id).first()
        return render_template('company/create_letters.html',employees_details=employees_details)

@company.route('/uploadlogos',methods=["GET","POST"])
def upload_logos():
    fname=''
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1]
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in app.config['UPLOAD_EXTENSIONS']: 
            flash('Please insert image with desired format!')
            return redirect(url_for('company.add_employee'))
        if not os.path.exists(app.config['UPLOAD_LETTER_FOLDER']+'/'+current_user.email):
            os.makedirs(app.config['UPLOAD_LETTER_FOLDER']+'/'+current_user.email)
        file.save(os.path.join(app.config['UPLOAD_LETTER_FOLDER'],current_user.email, fname))
        full_path = os.path.join('static/uploads/letters',current_user.email, fname)
    return full_path;

#Employee List Page
@company.route('/upload/signature', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def upload_signature():
    file = request.files.getlist('files')
    employee_details_id = request.form.get('employee_details_id')
    if file and employee_details_id:
        upload_file_data = upload_signature(file[0])
        company_signature = CompanySignature()
        company_signature.company_id = current_user.id
        company_signature.employee_details_id = ObjectId(employee_details_id)
        company_signature.signature_path = upload_file_data
        result = company_signature.save()    
        
        CompanyDetails.objects(user_id=current_user.id).update(add_to_set__company_signatures=company_signature._id)
        # Dialect helps in grouping together many specific formatting patterns like delimiter, skipinitialspace, quoting, escapechar into a single dialect name.
        if result:
            return "True"
    else:
        return "False"
    
def upload_signature(file):
    fname=''
    # file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1]
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in app.config['UPLOAD_EXTENSIONS']: 
            flash('Please insert image with desired format!')
            return redirect(url_for('company.add_employee'))
        if not os.path.exists(app.config['UPLOAD_LETTER_FOLDER']):
            os.makedirs(app.config['UPLOAD_LETTER_FOLDER'])
        file.save(os.path.join(app.config['UPLOAD_LETTER_FOLDER'], fname))
        full_path = os.path.join('static/uploads/letters', fname)
    return fname;

@company.route('/createexchange/settings/', methods=['POST'])
def create_exchange():
    if request.method == 'POST':
        exchange_name = request.form.get('exchange_name')
        company_routing_code = request.form.get("company_routing_code")
        
        if exchange_name and company_routing_code:
            new_company_exchange =  CompanyExchange(exchange_name=exchange_name,
                                    company_routing_code=company_routing_code,
                                    company_id = current_user.id
                                    )
            new_company_exchange.save()
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__company_exchanges=new_company_exchange.id)
            if update_details:
                details = CompanyExchange.objects(company_id=current_user.id)
                msg =  json.dumps({"status":"success","details":details.to_json()})
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg =  '{ " html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
    else:
        return render_template('company/settings.html')
    
@company.route('/createcompanyprofile/settings/', methods=['POST'])
def create_company_profiile():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        company_unique_id = request.form.get("company_unique_id")
        company_account_number = request.form.get("company_account_number")
        company_routing_code = request.form.get("company_routing_code")
        
        if company_name and company_unique_id and company_account_number and company_routing_code:
            new_sub_company =  SubCompanies(company_name=company_name,
                                    company_unique_id=company_unique_id,
                                    company_account_number=company_account_number,
                                    company_routing_code=company_routing_code,
                                    company_id = current_user.id
                                    )
            new_sub_company.save()
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__sub_companies=new_sub_company.id)
            if update_details:
                details = SubCompanies.objects(company_id=current_user.id)
                msg =  json.dumps({"status":"success","details":details.to_json()})
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg =  '{ " html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
    else:
        return render_template('company/settings.html')


@company.route('/deletemultipleaccess/settings', methods=['POST'])
def delete_multiple_access():
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    existing_multiple_access_docs = MutipleAcces.objects(company_id=current_user.id).all()
    
    data_id = request.form.get('dataId')
    
    if not data_id:
        return jsonify({'status': 'failed', 'message': 'dataId is required'}), 400
    
    for doc in existing_multiple_access_docs:
     if current_user.id == doc.company_id:
        return jsonify({'status': 'failed', 'message': 'Cannot delete the current user\'s access'}), 200
    
    try:
        
        item = MutipleAcces.objects(_id=data_id).first()
        
        if item:
            item.delete()  # Deleting the item from the database
            return jsonify({'status': 'success', 'message': 'Multiple Access Deleted'}), 200
        else:
            return jsonify({'status': 'failed', 'message': 'Item not found'}), 404

    except Exception as e:
        return jsonify({'status': 'failed', 'message': str(e)}), 500



@company.route('/Creatmultiple/savemultipleaccess', methods=['POST'])
def create_multiple_access():
    # Fetch company details for the current user
    company_details = CompanyDetails.objects(user_id=current_user.id).first()

    if not company_details:
        return jsonify({'success': False, 'message': 'Company details not found for the user'})

    # Initialize a list to hold existing multiple access entries
    existing_multiple_access_data = []
    
    # Fetch existing MultipleAccess documents
    existing_multiple_access_docs = MutipleAcces.objects(company_id=current_user.id).all()

    for data in existing_multiple_access_docs:
        for listdata in data.MultipleAccessEntry:
            existing_multiple_access_data.append(MultipleAccessEntry(
                multiple_access_email_id=listdata.multiple_access_email_id,
                multiple_access_company_id=listdata.multiple_access_company_id,
                multiple_access_company_name=listdata.multiple_access_company_name,
                company_logo=listdata.company_logo,
            ))

    if request.method == 'POST':
        # Parse JSON data from the frontend
        data = request.get_json()
        employees = data.get('employees', [])

        if employees:
            success_count = 0
            skipped_count = 0

            for employee in employees:
                try:
                    # Extract employee information
                    company_id = employee.get('user_id')
                    email = employee.get('email')
                    company_logo = employee.get('company_logo', '')
                    company_name = employee.get('company_name', '')
                    url = employee.get('url', '')

                    # Convert company_id to ObjectId
                    company_id = ObjectId(company_id) if company_id else None
                    Main_company_id= ObjectId(current_user.id) if current_user.id else None

                    # Check for duplicate entries
                    if MutipleAcces.objects(email=email, company_id=company_id).first():
                        skipped_count += 1
                        continue

                    # Create and save the new document
                    new_doc = MutipleAcces(
                        email=email,
                        company_id=company_id,
                        Main_company_id=Main_company_id,
                        MultipleAccessEntry=existing_multiple_access_data,  # Pass the list
                    )
                    new_doc.save()
                    success_count += 1

                except Exception as e:
                    print(f"Error processing employee {employee}: {e}")
                    skipped_count += 1

            return jsonify({
                'success': True,
                'message': f'{success_count} employees updated successfully, {skipped_count} skipped',
            })

        return jsonify({'success': False, 'message': 'No employees selected'})

    return jsonify({'success': False, 'message': 'Invalid request method'})    

@company.route('/reimbursement')
@login_required
def reimbursement():
    company_details = CompanyDetails.objects(user_id=current_user.id).only('company_name').first()
    company_id = current_user.id
    if not company_details: 
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        company_details = CompanyDetails.objects(user_id=employee_details.company_id).only('company_name').first()  
        company_id = employee_details.company_id
    reimbursement_data = EmployeeReimbursement.objects(company_id=company_id)
    return render_template('company/adjustments/reimbursement.html',company_details=company_details,reimbursement_data=reimbursement_data)

@company.route('/update/reimbursement/', methods=['POST'])
def update_reimbursement():
    if request.method == 'POST':
        # company_details = CompanyDetails.objects(user_id=current_user.id).first()
        reimbursement_id = request.form.get('reimbursement_id')
        reimbursement_status = request.form.get('status')
        payroll_month = request.form.get('payroll_month')
        
        
        if reimbursement_id:
            reimbursement_data = EmployeeReimbursement.objects(_id=reimbursement_id).first()
            
            if reimbursement_status == 'approvedtopayroll':
                payroll_month = request.form.get('payroll_month')
                start_of_month = datetime. strptime(payroll_month, '%B %Y')
                new_data = CompanyPayrollAdjustment(
                    company_id = reimbursement_data.company_id,
                    employee_details_id = reimbursement_data.employee_details_id,
                    adjustment_reason_id = reimbursement_data.adjustment_reason_id,
                    adjustment_type = reimbursement_data.adjustment_type,
                    adjustment_amount = reimbursement_data.reimbursement_amount,
                    adjustment_on = start_of_month,
                    adjustment_month_on_payroll = start_of_month.strftime('%B'),
                    adjustment_year_on_payroll =  start_of_month.year                     
                )
                status = new_data.save()
                reimbursement_data.update(reimbursement_status="approved")
                if status:
                    msg =  json.dumps({'status':'success'})
                    msghtml = json.loads(msg)
                    return msghtml
            else:
                if reimbursement_data:
                    status = reimbursement_data.update(reimbursement_status=reimbursement_status)
                    if status:
                        msg =  json.dumps({'status':'success'})
                        msghtml = json.loads(msg)
                        return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
    
@company.route('/timeoffadjustments')
@login_required
def timeoff_adjustments():
    adjustment_details = CompanyTimeOffAdjustment.objects(company_id=current_user.id)
    return render_template('company/adjustments/timeoff_adjustments.html',adjustment_details=adjustment_details)

@company.route('/update/timeoff/', methods=['POST'])
def update_timeoff():
    if request.method == 'POST':
        # company_details = CompanyDetails.objects(user_id=current_user.id).first()
        time_off_id = request.form.get('time_off_id')
        time_off_status = request.form.get('status')
        
        if time_off_id:
            time_off_data = CompanyTimeOffAdjustment.objects(_id=time_off_id).first()
            
            if time_off_data and time_off_status == 'approved':
                leave_policy = request.form.get('leave_policy')
                if leave_policy:
                    employee_leave_policy = EmployeeLeavePolicies.objects(_id=ObjectId(leave_policy)).first()
                    if employee_leave_policy and employee_leave_policy.balance > 0: 
                        if time_off_data.adjustment_type == "decrement":
                            new_policy_balance = float(employee_leave_policy.balance)-float(time_off_data.time_off_balance)
                        else:
                            new_policy_balance = float(employee_leave_policy.balance)+float(time_off_data.time_off_balance)
                        
                        new_data = EmployeeLeaveAdjustment(
                                company_id = time_off_data.company_id,
                                employee_details_id = time_off_data.employee_details_id,
                                employee_leave_pol_id = employee_leave_policy._id, 
                                adjustment_type = time_off_data.adjustment_type,
                                adjustment_days = str(time_off_data.time_off_balance),
                                adjustment_comment = 'timeoff adjustment',
                                before_adjustment=  str(employee_leave_policy.balance),
                                after_adjustment = str(new_policy_balance)
                            )
                        status = new_data.save()
                        company_details =  EmployeeLeavePolicies.objects(company_id=time_off_data.company_id,_id=employee_leave_policy._id).update(push__employee_leave_adjustments=new_data._id,balance=new_policy_balance) 
                           
                time_off_data.update(time_off_status="approved")
                if status:
                    msg =  json.dumps({'status':'success'})
                    msghtml = json.loads(msg)
                    return msghtml
            else:
                if time_off_data:
                    status = time_off_data.update(time_off_status=time_off_status)
                    if status:
                        msg =  json.dumps({'status':'success'})
                        msghtml = json.loads(msg)
                        return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
 
#Employee List Page
@company.route('/generate/individualpayroll', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def generate_individual_payroll():
    employee_id = request.form.get('employee_id')
    payroll_type = request.form.get('payroll_type')
    if payroll_type == "date_wise":
        selected_date = request.form.get('selected_date_wise')
    else:
        selected_date = request.form.get('selected_month_wise')
    
    if employee_id:
        result = generate_individual_payroll(selected_date,employee_id,payroll_type)
        #    result = add_bulk_open_leaves(leave_data,str(current_user.id))
        # if result:
        #     task_scheduled_details = ScheduledBackgroundTask(celery_task_id=result.id,company_id=current_user.id,task_type='generate_bulk_payroll',uploaded_on=datetime.now())
        #     task_scheduled_details.save()
        return "True"
    else:
        return "False"

def generate_individual_payroll(_month,employee_id,payroll_type):
    # selected_month = datetime. strptime(_month, '%Y-%m-%d')
    employees_details = CompanyDetails.objects(user_id=current_user.id).first()
    
    active_employees = EmployeeDetails.objects(_id=ObjectId(employee_id))
    # active_employees = list(filter(lambda x:x['employee_company_details']['status']==True,employees_details.employees))
    # active_employees = list(filter(lambda x:x['_id']==ObjectId('624fe7dfe715a9c4baa8045b'),employees_details.employees))
    
    if payroll_type == "date_wise":
        selected_month = datetime. strptime(_month, '%d/%m/%Y')
    
    else:
        date_obj = datetime.strptime(_month, "%B %Y")
        selected_month = date_obj.replace(day=1)   
        
    overal_salary_to_be_paid = 0.0
    overal_salary_to_be_paid_ja = 0.0
    overal_salary_to_be_paid_aa = 0.0
    overal_salary_to_be_paid_rb = 0.0
    
    no_of_employees_ja = 0
    no_of_employees_aa = 0
    no_of_employees_rb = 0
    
    no_of_employees = 0
    nxt_mnth = selected_month.replace(day=28) + timedelta(days=4)
    end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
    
    for employee in active_employees:
        if employee.employee_company_details.type == '0': # if the employee salary type is 0 i.e Full-time employee 
            # check if the data available in the DB, if yes delete and create a new record
            data_available = CompanyPayroll.objects(company_id=current_user.id,payroll_month=selected_month.strftime('%B'),payroll_year=selected_month.year,employee_details_id=employee._id).first()
            if data_available:
                if data_available.sif_details:
                    sif_details = CompanySif.objects(_id=data_available.sif_details._id).first()
                    if sif_details:
                        sif_details.delete()
                data_available.delete()
            # Create a new record including the adjustments as well 
            employee_payroll = CompanyPayroll()
            employee_payroll.employee_id = employee.employee_company_details.employee_id
            employee_payroll.company_id = current_user.id
            employee_payroll.employee_details_id = employee._id
            employee_payroll.payroll_month = selected_month.strftime('%B')
            employee_payroll.payroll_year = selected_month.year
            # Salary Details
            employee_payroll.basic_salary = employee.employee_company_details.basic_salary
            employee_payroll.housing_allowance = employee.employee_company_details.housing_allowance
            employee_payroll.travel_allowance = employee.employee_company_details.travel_allowance
            employee_payroll.other_allowances = employee.employee_company_details.other_allowances 
            employee_payroll.fuel_allowances = employee.employee_company_details.fuel_allowance
            employee_payroll.mobile_allowances = employee.employee_company_details.mobile_allowance
            employee_payroll.medical_allowances = employee.employee_company_details.medical_allowance
            if payroll_type == "date_wise":
                per_day_basic_pay = float(employee.employee_company_details.total_salary)/(end_of_the_month.day)
                employee_payroll.per_day_basic_pay = per_day_basic_pay
                employee_payroll.no_of_prorated_days = selected_month.day
                employee_payroll.prorated_date = str(selected_month)
                total_salary = float(per_day_basic_pay)*float(selected_month.day)
                employee_payroll.total_prorated_salary = total_salary
                employee_payroll.payroll_type = "date_wise"
                
            else:
                total_salary = float(employee.employee_company_details.total_salary)
                employee_payroll.payroll_type = "month_wise"
                
           
            employee_payroll.total_salary = employee.employee_company_details.total_salary
            
            # Todo: Check for Adjustments records and add to payroll deduction and additions
            adjustments_exists = CompanyPayrollAdjustment.objects(employee_details_id=employee._id,company_id=current_user.id,adjustment_month_on_payroll=selected_month.strftime('%B'),adjustment_year_on_payroll=selected_month.year)
            addition_amount = 0.0
            deduction_amount = 0.0
            if adjustments_exists:
                additions = []
                deductions = []
                for adjustment in adjustments_exists:
                    # Adjustment Additions
                    if adjustment.adjustment_type == 'addition':
                        additions.append(adjustment._id)
                        addition_amount = float(addition_amount) + float(adjustment.adjustment_amount)
                    # Adjustment Deduction
                    else:
                        deductions.append(adjustment._id)
                        deduction_amount = float(deduction_amount) + float(adjustment.adjustment_amount)
                        
                    # todo: Update the adjustment as approved to payroll so that we can disable the delete option for the adjustment;
                    CompanyPayrollAdjustment.objects(_id=adjustment._id).update(added_to_payroll=True)
                
                employee_payroll.adjustment_additions = additions
                employee_payroll.adjustment_deductions = deductions
                employee_payroll.total_deductions = deduction_amount
                employee_payroll.total_additions = addition_amount
            
            salary_to_be_paid = (float(total_salary) +  float(addition_amount))-float(deduction_amount)
            employee_payroll.salary_to_be_paid = salary_to_be_paid
            
            fixed_salary = float(employee.employee_company_details.total_salary)
            salary_with_deduction = float(employee.employee_company_details.total_salary) - float(deduction_amount)
            employee_payroll.salary_to_be_paid = salary_to_be_paid
            
            employee_payroll.generated_date = datetime.today()
            
            # Check to which exchage the emp belongs
            if hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name') and employee.employee_sif_details.company_exchange.exchange_name == "Joyalukkas Exchange":
                overal_salary_to_be_paid_ja = overal_salary_to_be_paid_ja + salary_to_be_paid
                no_of_employees_ja = no_of_employees_ja + 1
                
            elif hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name') and employee.employee_sif_details.company_exchange.exchange_name == "Al Ansari Exchange":
                overal_salary_to_be_paid_aa = overal_salary_to_be_paid_aa + salary_to_be_paid
                no_of_employees_aa = no_of_employees_aa + 1
                
            elif hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name') and employee.employee_sif_details.company_exchange.exchange_name == "RAK Bank":
                overal_salary_to_be_paid_rb = overal_salary_to_be_paid_rb + salary_to_be_paid
                no_of_employees_rb = no_of_employees_rb + 1
            
            # todo: Calculate on_leave_days
            # on_leave_days = EmployeeAttendance.objects(employee_details_id=employee._id,attendance_status="absent",attendance_date__gte=selected_month,attendance_date__lte=end_of_the_month).count()
            on_leave_days = 0
            unpaid_leaves = EmployeeAttendance.objects(Q(employee_details_id=employee._id) & Q(attendance_date__gte=selected_month) & Q(attendance_date__lte=end_of_the_month) & Q(attendance_status='absent') & (Q(leave_name='') | Q(leave_name__exists=False))).count()
            paid_days = EmployeeAttendance.objects(Q(employee_details_id=employee._id) & Q(attendance_date__gte=selected_month) & Q(attendance_date__lte=end_of_the_month) & Q(attendance_status='absent') & (Q(leave_name__ne='') & Q(leave_name__exists=True))).count()
            half_days = EmployeeAttendance.objects(employee_details_id=employee._id,half_day=True,attendance_date__gte=selected_month,attendance_date__lte=end_of_the_month).count()
            if half_days:
                half_day_count = math.ceil((half_days/2))
                on_leave_days = unpaid_leaves + half_day_count
            employee_payroll.unpaid_leaves = unpaid_leaves
            employee_payroll.half_days = half_days
            employee_payroll.paid_leaves = paid_days
            
            employee_payroll.save()
            
            # todo: Calculate on_leave_days
            # company_leave_policies = CompanyLeavePolicies.objects(company_id=current_user.id,leave_type="unpaid").all()
            # unpaid_leaves_types = EmployeeLeavePolicies.objects(company_id=current_user.id,employee_details_id=employee._id,leave_policy_id__in=company_leave_policies).all()
            # status = EmployeeLeaveApplication.objects(company_id=current_user.id,employee_details_id=employee._id,employee_leave_policy__in=unpaid_leaves_types,leave_status="approved",leave_from__gte=selected_month,leave_till__lte=end_of_the_month).all()
            # on_leave_days = 0
            # for item in status:
            #     on_leave_days = on_leave_days + int(item.no_of_days)
            
            
            employee_sif = CompanySif()
            employee_sif.company_id = current_user.id
            employee_sif.employee_id = employee.employee_company_details.employee_id
            employee_sif.employee_details_id = employee._id
            employee_sif.sif_type = "EDR"
            employee_sif.pay_start = selected_month.strftime('%Y-%m-%d')
            employee_sif.pay_end = end_of_the_month.strftime('%Y-%m-%d')
            employee_sif.days_in_month = str((end_of_the_month).day)
            employee_sif.salary = str(salary_to_be_paid)
            employee_sif.fixed_salary = str(fixed_salary)
            employee_sif.on_leave_days = str(on_leave_days)
            employee_sif.variable_pay = abs(float(deduction_amount) - float(addition_amount)) 
            employee_sif.salary_with_deduction = str(salary_with_deduction)
            employee_sif.sif_month = selected_month
            employee_sif.sif_year = selected_month.year
            employee_sif.exchange = employee.employee_sif_details.company_exchange.exchange_name if (hasattr(employee.employee_sif_details,'company_exchange') and hasattr(employee.employee_sif_details.company_exchange,'exchange_name')) else ''
            
            employee_sif.save()
            employee_payroll.update(sif_details=employee_sif._id)
    
    #todo: Generate sif SCR record as well
    # todo: Check if the previous SCR recors is present if yes delete and create new
    data_available = CompanySif.objects(company_id=current_user.id,sif_month=selected_month,sif_year=selected_month.year,sif_type='SCR')
    if data_available:
        data_available.delete()
    
    employee_sif = CompanySif()
    employee_sif.company_id = current_user.id
    employee_sif.employee_id = employee.employee_company_details.employee_id
    employee_sif.employee_details_id = employee._id
    employee_sif.sif_type = "SCR"
    employee_sif.company_unique_id = employees_details.company_unique_id
    employee_sif.company_routing_code = employees_details.company_routing_code
    employee_sif.file_creation_date = datetime.now().strftime('%Y-%m-%d')
    employee_sif.file_date = datetime.now().strftime('%Y%m%d')
    employee_sif.file_creation_time = datetime.now().strftime('%H%M')
    employee_sif.file_time = datetime.now().strftime('%H%M%S')
    
    employee_sif.salary_month = selected_month.strftime('%m%Y')
    employee_sif.edr_count_ja = no_of_employees_ja
    employee_sif.edr_count_aa = no_of_employees_aa
    employee_sif.edr_count_rb = no_of_employees_rb
    
    employee_sif.overal_salary_to_be_paid_ja = overal_salary_to_be_paid_ja
    employee_sif.overal_salary_to_be_paid_aa = overal_salary_to_be_paid_aa
    employee_sif.overal_salary_to_be_paid_rb = overal_salary_to_be_paid_rb
    
    employee_sif.currency = "AED"
    employee_sif.reference = employees_details.company_name
    employee_sif.sif_month = selected_month
    employee_sif.sif_year = selected_month.year
    
    employee_sif.save()    
    
    return "True"
 
@company.route('/leaveencashment')
@login_required
def leave_encashment():
    employees_details = CompanyDetails.objects(user_id=current_user.id).first()
    return render_template('company/leave_encashment.html',employees_details=employees_details)

@company.route('/calculateleaveencashment/', methods=['POST'])
def calculate_leave_encashment():
    if request.method == 'POST':
            employee_details_id = request.form.get('employee_details_id')
            leave_policy = request.form.get('leave_policy')
           
            leave_encashment_amount = 0.0
            employee_details = EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
            per_day_basic_pay = float(employee_details.employee_company_details.basic_salary)/30.0
            
            if employee_details:
                leave_policy_details = EmployeeLeavePolicies.objects(_id=ObjectId(leave_policy)).first()
                if leave_policy_details:
                    leave_encashment_amount = (per_day_basic_pay*float(leave_policy_details.balance))
                            
                details = {
                'leave_encashment_amount' : leave_encashment_amount,
                'per_day_basic_pay' :  per_day_basic_pay
                }         
                # Todo: Unlimited Contract Type
                msg =  json.dumps({"status":"success","details":details})
                msghtml = json.loads(msg)
                return msghtml
            else:
                msg =  '{"status":"failed"}'
                msghtml = json.loads(msg)
                return msghtml
    else:
        return render_template('company/settings.html') 

@celery.task(track_started = True,result_extended=True,name='Check-Document-Expiration')
def check_document_expiration():
    # Define the table structure

    current_date = datetime.now()
    company_details = CompanyDetails.objects().all()
    for company_detail in company_details:
        expiry_documents = []
        expired_documents = []
        active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
        for employee in active_employees:
            for document in employee.documents:
                expiry_days = (document.document_expiry_on - current_date).days
                if document.days_before_expiry_alert:
                    expiry_alert_days = int(document.days_before_expiry_alert)
                else:
                    expiry_alert_days = 90

                # Check if document is about to expire or has expired
                if expiry_days == expiry_alert_days and document.email_alert_status == "not_sent":
                    status = "Document is about to expire or has expired!"
                    expiry_documents.append({"employee_name":str(employee.first_name)+ ' ' +str(employee.last_name),
                                             "emp_id":employee.employee_company_details.employee_id,
                                             "document_type":str(document.document_type),
                                             "expiry_on": document.document_expiry_on.strftime("%d %B %Y"),
                                             "employee_id": employee._id,
                                             "document_id": document._id
                                            })
                elif expiry_days < expiry_alert_days:
                    status = "Document has expired!"
                    expired_documents.append({"employee_name":str(employee.first_name)+ ' ' +str(employee.last_name),
                                             "emp_id":employee.employee_company_details.employee_id,
                                             "document_type":str(document.document_type),
                                             "expiry_on": document.document_expiry_on.strftime("%d %B %Y"),
                                             "employee_id": employee._id,
                                             "document_id": document._id
                                            })

        if company_detail.receiver_emails and expiry_documents:
            if company_detail.email_config:
                mail_server = company_detail.email_config.company_email_host
                mail_port = company_detail.email_config.company_email_port
                mail_use_tls = company_detail.email_config.company_email_tls
                mail_username = company_detail.email_config.company_email_user
                mail_password = company_detail.email_config.company_email_password
            
                current_app.config.update(
                MAIL_SERVER=mail_server,
                MAIL_PORT=mail_port,
                MAIL_USE_TLS=mail_use_tls,
                MAIL_USERNAME=mail_username,
                MAIL_PASSWORD=mail_password
                )
                
                mail.init_app(current_app)
            else:
                mail_server = app.config['MAIL_SERVER']
                mail_port = app.config['MAIL_PORT']
                mail_use_tls = app.config['MAIL_USE_TLS']
                mail_username = app.config['MAIL_USERNAME']
                mail_password = app.config['MAIL_PASSWORD']
                mail.init_app(app)
            
            # Split the comma-separated string of email addresses into a list
            receiver_emails_list = company_detail.receiver_emails.split(',')
            html = render_template('email/expiry_document.html', expiry_documents=expiry_documents,expired_documents=expired_documents)
            with current_app.app_context():
                msg = Message('Document(s) Expiry Alert | Cubes HRMS', sender =("Cubes HRMS", app.config['MAIL_USERNAME']), recipients = receiver_emails_list)
                msg.html = html
                try:
                    status = mail.send(msg)
                    email_status = "sent"
                except Exception as e:
                    email_status = "failed"
                    msg = str(e)
                    
                for expiry_document in expiry_documents:
                    if email_status == "sent":
                        employee_id = expiry_document["employee_id"]
                        document_id = expiry_document["document_id"]
                        # find the employee document and update the email alert fields
                        emp = EmployeeDetails.objects(_id=employee_id).first()
                        if emp:
                            document = next((doc for doc in emp.documents if doc._id == document_id), None)
                            if document:
                                document.email_alert_status = 'sent'
                                document.email_alert_sent_on = datetime.now()
                                emp.save()
                    else:
                        employee_id = expiry_document["employee_id"]
                        document_id = expiry_document["document_id"]
                         # find the employee document and update the email alert fields
                        emp = EmployeeDetails.objects(_id=employee_id).first()
                        if emp:
                            document = next((doc for doc in emp.documents if doc._id == document_id), None)
                            if document:
                                document.email_alert_status = 'failed'
                                document.email_alert_sent_on = datetime.now()
                                document.email_alert_message = msg
                                emp.save()
    return True
 
@celery.task(track_started = True,result_extended=True,name='Leave-Approval-Email')
def check_pending_leave_application():
    app = create_app()  # create the Flask app
    mail = Mail(current_app)  # initialize Flask-Mail with default email server details
    pipeline = [
    {
        "$group": {
            "_id": {
                "company_id": "$company_id",
                "approver_id": "$approver_id"
            },
            "applications": {"$push": "$$ROOT"}
        }
    }
    ]

    applications_by_company_approver = EmployeeLeaveRequest.objects(request_status="pending").aggregate(pipeline)
    for group in applications_by_company_approver:
        app = create_app()  # create the Flask app
        mail = Mail(current_app)  # initialize Flask-Mail with default email server details
        # print(f"Company ID: {group['_id']['company_id']}, Approver: {group['_id']['approver_id']}")
        _applications = []
        pending_applications = []
        approver_details = EmployeeLeaveApprover.objects(_id=group['_id']['approver_id']).first()
        for _app in group['applications']:
            # print(f"Application ID: {_app['_id']}")
            # print(f"Application ID: {approver_details.employee_details_id.first_name}")
            application_details = EmployeeLeaveApplication.objects(_id=ObjectId(_app['employee_leave_app_id'])).first()
            if application_details.current_aprrover.email_alert_status == "not_sent":
                _applications.append({
                            "employee_name": str(application_details.employee_details_id.first_name) + ' ' + str(application_details.employee_details_id.last_name),
                            "emp_id": application_details.employee_details_id.employee_company_details.employee_id,
                            "leave_type": str(application_details.employee_leave_policy.leave_policy_id.leave_policy_name),
                            "start": application_details.leave_from.strftime("%d %B %Y"),
                            "end": application_details.leave_till.strftime("%d %B %Y"),
                            "no_of_days": application_details.no_of_days,
                            "reason": application_details.reason,
                            "leave_approver": application_details.current_aprrover._id})
        if _applications:
            pending_applications.append({
                "aprrover_name": approver_details.employee_details_id.first_name,
                "aprrover_email": approver_details.employee_details_id.user_id.email,
                "applications": _applications
            })
            company_detail = CompanyDetails.objects(user_id=group['_id']['company_id']).first()
            if pending_applications:
                if company_detail.email_config:
                    mail_server = company_detail.email_config.company_email_host
                    mail_port = company_detail.email_config.company_email_port
                    mail_use_tls = company_detail.email_config.company_email_tls
                    mail_username = company_detail.email_config.company_email_user
                    mail_password = company_detail.email_config.company_email_password
                
                    current_app.config.update(
                    MAIL_SERVER=mail_server,
                    MAIL_PORT=mail_port,
                    MAIL_USE_TLS=mail_use_tls,
                    MAIL_USERNAME=mail_username,
                    MAIL_PASSWORD=mail_password
                    )
                    mail.init_app(current_app)
                else:
                    mail_server = app.config['MAIL_SERVER']
                    mail_port = app.config['MAIL_PORT']
                    mail_use_tls = app.config['MAIL_USE_TLS']
                    mail_username = app.config['MAIL_USERNAME']
                    mail_password = app.config['MAIL_PASSWORD']
                    mail.init_app(app)
                
                with current_app.app_context():
                    for _pending_application in pending_applications:
                        log_in_url = app.config['LOG_IN_URL_MAIL']
                        # log_in_url = url_for('auth.login', _external=True)

                        html = render_template('email/leave_approval.html', pending_applications=_pending_application,log_in_url=log_in_url)
                        # msg = Message('Document(s) Expiry Alert! | Cubes HRMS', sender = ("Cubes HRMS",app.config['MAIL_USERNAME']), recipients = _pending_application.aprrover_email)
                        msg = Message('Leave Application Approval Required! | Cubes HRMS', sender = ("Cubes HRMS",current_app.config['MAIL_USERNAME']), recipients = [_pending_application["aprrover_email"]])
                        msg.html = html
                        try:
                            status = mail.send(msg)
                            email_status = "sent"
                        except Exception as e:
                            email_status = "failed"
                            msg = str(e)
                            
                        for _pending_app in _pending_application["applications"]:
                            if email_status == "sent":
                                current_approver_id = _pending_app["leave_approver"]
                                # find the employee document and update the email alert fields
                                curr_leave_request = EmployeeLeaveRequest.objects(_id=current_approver_id).first()
                                if curr_leave_request:
                                    curr_leave_request.email_alert_status = 'sent'
                                    curr_leave_request.email_alert_sent_on = datetime.now()
                                    curr_leave_request.email_alert_sent_count = curr_leave_request.email_alert_sent_count + 1
                                    curr_leave_request.save()
                            else:
                                current_approver_id = _pending_app["leave_approver"]
                                # find the employee document and update the email alert fields
                                curr_leave_request = EmployeeLeaveRequest.objects(_id=current_approver_id).first()
                                if curr_leave_request:
                                    curr_leave_request.email_alert_status = 'failed'
                                    curr_leave_request.email_alert_sent_on = datetime.now()
                                    curr_leave_request.email_alert_message = msg
                                    curr_leave_request.save()
    # print(pending_applications)
    return True

@celery.task(track_started = True,result_extended=True,name='Memo-Creation-Email')
def send_memo_emails(company_id,memo_id):
    app = create_app()  # create the Flask app
    mail = Mail(current_app)  # initialize Flask-Mail with default email server details
    # Get Leave Application Details
    company_details = CompanyDetails.objects(user_id=ObjectId(company_id)).only('email_config','employees').first()
    employee_email_list = get_employees_emails(company_details.employees)
    # email="arsalaanmuallim28@gmail.com"
    # print(employee_email_list)
    if company_details.email_config:
        mail_server = company_details.email_config.company_email_host
        mail_port = company_details.email_config.company_email_port
        mail_use_tls = company_details.email_config.company_email_tls
        mail_username = company_details.email_config.company_email_user
        mail_password = company_details.email_config.company_email_password
       
        current_app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USERNAME=mail_username,
        MAIL_PASSWORD=mail_password
        )
        
        mail.init_app(current_app)
    else:
        mail_server = app.config['MAIL_SERVER']
        mail_port = app.config['MAIL_PORT']
        mail_use_tls = app.config['MAIL_USE_TLS']
        mail_username = app.config['MAIL_USERNAME']
        mail_password = app.config['MAIL_PASSWORD']
        mail.init_app(app)

    with current_app.app_context():
        memo_details = CompanyMemo.objects(_id=ObjectId(memo_id)).first()
        html = render_template('email/memo.html', memo_details=memo_details)
        msg = Message('New Memo Notification! | Cubes HRMS', sender = ("Cubes HRMS",app.config['MAIL_USERNAME']), recipients = [employee_email_list])
        msg.html = html
        mail.send(msg)
        return True
    
def get_employees_emails(employees):
    employee_emails = []
    for employee in employees:
        employee_details = EmployeeDetails.objects(_id=employee._id).first()
        if employee_details:
            user_email = employee_details.user_id.email
            if user_email:
                employee_emails.append(user_email)
    return employee_emails

@celery.task(track_started = True,result_extended=True,name='Weekly-Leave-Approval-Email')
def check_weekly_pending_leave_application():
    app = create_app()  # create the Flask app
    mail = Mail(current_app)  # initialize Flask-Mail with default email server details
    pipeline = [
    {
        "$group": {
            "_id": {
                "company_id": "$company_id",
                "approver_id": "$approver_id"
            },
            "applications": {"$push": "$$ROOT"}
        }
    }
    ]
    current_date = datetime.now()
    week_prior_date = current_date - timedelta(days=7)
    
    applications_by_company_approver = EmployeeLeaveRequest.objects(request_status="pending",email_alert_sent_on__gte=week_prior_date,email_alert_sent_on__lte=current_date).aggregate(pipeline)
    for group in applications_by_company_approver:
        app = create_app()  # create the Flask app
        mail = Mail(current_app)  # initialize Flask-Mail with default email server details
        # print(f"Company ID: {group['_id']['company_id']}, Approver: {group['_id']['approver_id']}")
        _applications = []
        pending_applications = []
        approver_details = EmployeeLeaveApprover.objects(_id=group['_id']['approver_id']).first()
        for _app in group['applications']:
            # print(f"Application ID: {_app['_id']}")
            # print(f"Application ID: {approver_details.employee_details_id.first_name}")
            application_details = EmployeeLeaveApplication.objects(_id=ObjectId(_app['employee_leave_app_id'])).first()
            # if application_details.current_aprrover.email_alert_status == "not_sent":
            _applications.append({
                        "employee_name": str(application_details.employee_details_id.first_name) + ' ' + str(application_details.employee_details_id.last_name),
                        "emp_id": application_details.employee_details_id.employee_company_details.employee_id,
                        "leave_type": str(application_details.employee_leave_policy.leave_policy_id.leave_policy_name),
                        "start": application_details.leave_from.strftime("%d %B %Y"),
                        "end": application_details.leave_till.strftime("%d %B %Y"),
                        "no_of_days": application_details.no_of_days,
                        "reason": application_details.reason,
                        "leave_approver": application_details.current_aprrover._id})
        if _applications:
            pending_applications.append({
                "aprrover_name": approver_details.employee_details_id.first_name,
                "aprrover_email": approver_details.employee_details_id.user_id.email,
                "applications": _applications
            })
            
            
        # print(pending_applications)
            company_detail = CompanyDetails.objects(user_id=group['_id']['company_id']).first()
            if pending_applications:
                if company_detail.email_config:
                    mail_server = company_detail.email_config.company_email_host
                    mail_port = company_detail.email_config.company_email_port
                    mail_use_tls = company_detail.email_config.company_email_tls
                    mail_username = company_detail.email_config.company_email_user
                    mail_password = company_detail.email_config.company_email_password
                
                    current_app.config.update(
                    MAIL_SERVER=mail_server,
                    MAIL_PORT=mail_port,
                    MAIL_USE_TLS=mail_use_tls,
                    MAIL_USERNAME=mail_username,
                    MAIL_PASSWORD=mail_password
                    )
                    mail.init_app(current_app)
                else:
                    mail_server = app.config['MAIL_SERVER']
                    mail_port = app.config['MAIL_PORT']
                    mail_use_tls = app.config['MAIL_USE_TLS']
                    mail_username = app.config['MAIL_USERNAME']
                    mail_password = app.config['MAIL_PASSWORD']
                    mail.init_app(app)
                
                with current_app.app_context():
                    for _pending_application in pending_applications:
                        # print(_pending_application["aprrover_email"])
                        # print(_pending_application["aprrover_name"])
                        log_in_url = app.config['LOG_IN_URL_MAIL']
                        # log_in_url = url_for('auth.login', _external=True)
                        html = render_template('email/leave_approval.html', pending_applications=_pending_application,log_in_url=log_in_url)
                        # msg = Message('Document(s) Expiry Alert! | Cubes HRMS', sender = ("Cubes HRMS",app.config['MAIL_USERNAME']), recipients = _pending_application.aprrover_email)
                        msg = Message('[Weekly Reminder] Leave Application Approval Required! | Cubes HRMS', sender = ("Cubes HRMS",current_app.config['MAIL_USERNAME']), recipients = [_pending_application["aprrover_email"]])
                        msg.html = html
                        try:
                            status = mail.send(msg)
                            email_status = "sent"
                        except Exception as e:
                            msg = str(e)
                            email_status = "failed"
                            
                        for _pending_app in _pending_application["applications"]:
                            if email_status == "sent":
                                current_approver_id = _pending_app["leave_approver"]
                                # find the employee document and update the email alert fields
                                curr_leave_request = EmployeeLeaveRequest.objects(_id=current_approver_id).first()
                                if curr_leave_request:
                                    curr_leave_request.email_alert_status = 'sent'
                                    curr_leave_request.email_alert_sent_on = datetime.now()
                                    curr_leave_request.email_alert_sent_count = curr_leave_request.email_alert_sent_count + 1
                                    curr_leave_request.save()
                            else:
                                current_approver_id = _pending_app["leave_approver"]
                                # find the employee document and update the email alert fields
                                curr_leave_request = EmployeeLeaveRequest.objects(_id=current_approver_id).first()
                                if curr_leave_request:
                                    curr_leave_request.email_alert_status = 'failed'
                                    curr_leave_request.email_alert_sent_on = datetime.now()
                                    curr_leave_request.email_alert_message = msg
                                    curr_leave_request.save()
    # print(pending_applications)
    return True





# @company.route('/MonthlyAccrualLeaves')
# def monthly_accrual_leaves():
#     current_date_1 = datetime.now()

#     # Subtract one month from the current date
#     previous_month_date = current_date_1 - relativedelta(months=1)
#     current_date = previous_month_date # Monthly Ending Date


#     # # Find the first day of the next month
#     # first_day_of_next_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
#     # # Subtract one day to get the end of the current month
#     # current_date = first_day_of_next_month - timedelta(days=1)
#     company_details = CompanyDetails.objects().all()

#     for company_detail in company_details:
#         leave_adjustments = []
#         active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
#         one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']
#         if one_time_leave_policies:
#             for employee in active_employees:
#                 if employee.employee_company_details.date_of_joining:
#                     try:
#                         date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
#                         # Further processing for valid dates
#                         date_of_joining=datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
#                         days_worked = (current_date - date_of_joining).days
#                         if days_worked < 365:
#                             # print("Less Than 1 Year of Joining");
#                             for leave_policy in one_time_leave_policies:
#                                 new_leave_balance = 0 
#                                 before_adjustment = 0
#                                 prorated_accruals = 0
#                                 employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
#                                 # Check if the current month is the joining month of the employee
#                                 # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
#                                 # no of days worked = current_date - joining_date
#                                 # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
#                                                         # OR
#                                 # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
#                                 # Check if the current month is the joining month
#                                 if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
#                                     # if days_worked < 365:  # Assuming probation period is less than a year
#                                     prorated_accruals = (days_worked / 30) * 2 
#                                     # else:
#                                     #     prorated_accruals = (days_worked / 30) * 2.5
#                                 if employee_leave_policy:
#                                         print(employee_leave_policy) 
#                                         before_adjustment = employee_leave_policy.balance
#                                         new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days))
#                                 else:
#                                         #create New with the new amount    
#                                         new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days)
#                                         employee_leave_policy = EmployeeLeavePolicies()
#                                         employee_leave_policy.company_id = company_detail.user_id
#                                         employee_leave_policy.employee_details_id = employee._id
#                                         employee_leave_policy.leave_policy_id = leave_policy._id
#                                         employee_leave_policy.balance = new_leave_balance
#                                         employee_leave_policy.save()
#                                         employee.update(push__employee_leave_policies=employee_leave_policy._id)
                                        
#                                 if  new_leave_balance > 0:     
#                                         previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
#                                         adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month  
#                                         # adjustment_comment = 'Monthly Accrual Adjustment for Month ' + datetime.now().strftime("%B %Y")
#                                         new_data = EmployeeLeaveAdjustment(
#                                                     company_id = company_detail.user_id,
#                                                     employee_details_id =  employee._id,
#                                                     employee_leave_pol_id = employee_leave_policy._id, 
#                                                     adjustment_type = 'increment',
#                                                     adjustment_days = str(new_leave_balance),
#                                                     adjustment_comment = adjustment_comment,
#                                                     before_adjustment=  str(employee_leave_policy.balance),
#                                                     after_adjustment = str(new_leave_balance)
#                                                 )
#                                         status = new_data.save()
#                                         company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
#                         else:
#                             # print("More Than 1 year of joining");
#                             for leave_policy in one_time_leave_policies:
#                                 new_leave_balance = 0 
#                                 before_adjustment = 0
#                                 prorated_accruals = 0
#                                 employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
#                                 # Check if the current month is the joining month of the employee
#                                 # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
#                                 # no of days worked = current_date - joining_date
#                                 # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
#                                                         # OR
#                                 # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
#                                 # Check if the current month is the joining month
#                                 if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
#                                         prorated_accruals = (days_worked / 30) * 2.5 
#                                 if employee_leave_policy:
#                                         before_adjustment = employee_leave_policy.balance
#                                         new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days))
#                                 else:
#                                         #create New with the new amount     
#                                         new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days)
#                                         employee_leave_policy = EmployeeLeavePolicies()
#                                         employee_leave_policy.company_id = company_detail.user_id
#                                         employee_leave_policy.employee_details_id = employee._id
#                                         employee_leave_policy.leave_policy_id = leave_policy._id
#                                         employee_leave_policy.balance = new_leave_balance
#                                         employee_leave_policy.save()
#                                         employee.update(push__employee_leave_policies=employee_leave_policy._id)
#                                 if  new_leave_balance > 0:       
#                                     previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
#                                     adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month
#                                     print(adjustment_comment)
#                                     new_data = EmployeeLeaveAdjustment(
#                                                 company_id = company_detail.user_id,
#                                                 employee_details_id =  employee._id,
#                                                 employee_leave_pol_id = employee_leave_policy._id, 
#                                                 adjustment_type = 'increment',
#                                                 adjustment_days = str(new_leave_balance),
#                                                 adjustment_comment = adjustment_comment,
#                                                 before_adjustment=  str(employee_leave_policy.balance),
#                                                 after_adjustment = str(new_leave_balance)
#                                             )
#                                     status = new_data.save()
#                                     company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
#                     except ValueError:
#                         # Handling for invalid date format
#                         continue
#     return True

# @app.route('/findduplicates')
# @login_required
# def findduplicates():
#     # Access the collection from the MongoDB database
#     collection = EmployeeLeaveAdjustment

#     # Aggregation pipeline to find duplicates based on 'employee_details_id', 'company_id', and 'adjustment_days'
#     pipeline = [
#         {
#             "$group": {
#                 "_id": {
#                     "employee_details_id": "$employee_details_id",  # Group by 'employee_details_id'
#                     "company_id": "$company_id",  # Group by 'company_id'
#                     "adjustment_days": "$adjustment_days"  # Group by 'adjustment_days'
#                 },
#                 "count": {"$sum": 1},  # Count the occurrences
#                 "docs": {"$push": "$$ROOT"}  # Keep the original documents
#             }
#         },
#         {
#             "$match": {
#                 "count": {"$gt": 1}  # Only select groups with more than 1 occurrence (duplicates)
#             }
#         },
#         {
#             # # Optional: Match documents based on 'created_at' date if you want to filter by date
#             # # Uncomment this part if you want to add date filtering
#             # "$match": {
#             #     "created_at": {
#             #         "$gte": ISODate("2024-01-01T00:00:00Z"),  # Adjust this date range as needed
#             #         "$lte": ISODate("2024-12-31T23:59:59Z")
#             #     }
#             # }
#         }
#     ]

#     # Run the aggregation
#     duplicates = list(collection.aggregate(pipeline))

#     # Send the result as a JSON response
#     return jsonify(duplicates)

# from mongoengine import Q
# from flask_pymongo import PyMongo
# @company.route('/findduplicates', methods=['GET'])
# @login_required
# def find_duplicates():
#     # Get company_id from the query parameters
#     company_id = request.args.get('company_id')

#     # Ensure that company_id is provided
#     if not company_id:
#         return jsonify({"error": "company_id is required"}), 400

#     # Access the collection from the MongoDB database and filter by company_id
#     collection = EmployeeLeaveAdjustment.objects(company_id=ObjectId(company_id))

#     # Aggregation pipeline to find duplicates based on specific fields
#     # pipeline = [
#     #     {
#     #         "$match": {
#     #             "company_id": ObjectId(company_id),
#     #         }
#     #     },
#     #     {
#     #         "$lookup": {
#     #             "from": "employee_details",
#     #             "localField": "employee_details_id",
#     #             "foreignField": "_id",
#     #             "as": "employee_info"
#     #         }
#     #     },
#     #     {
#     #         "$group": {
#     #             "_id": {
#     #                 "created_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
#     #                 "modified_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$modified_on"}},
#     #                 "modified_by": "$modified_by"
#     #             },
#     #             "count": {"$sum": 1},
#     #             "docs": {"$push": {
#     #                 "_id": "$_id",
#     #                 "employee_details_id": "$employee_details_id",
#     #                 "employee_name": {"$arrayElemAt": ["$employee_info.first_name", 0]},
#     #                 "adjustment_days": "$adjustment_days",
#     #                 "before_adjustment": "$before_adjustment",
#     #                 "after_adjustment": "$after_adjustment",
#     #                 "created_at": "$created_at",
#     #                 "modified_on": "$modified_on"
#     #             }}
#     #         }
#     #     },
#     #     {
#     #         "$match": {
#     #             "count": {"$gt": 1}
#     #         }
#     #     }
#     # ]
#     pipeline = [
#         {
#             "$match": {
#                 "company_id": ObjectId(company_id),
#             }
#         },
#         {
#             "$lookup": {
#                 "from": "employee_details",
#                 "localField": "employee_details_id",
#                 "foreignField": "_id",
#                 "as": "employee_info"
#             }
#         },
#         {
#             "$lookup": {
#                 "from": "employee_leave_application",
#                 "localField": "_id",
#                 "foreignField": "leave_adjustment",
#                 "as": "leave_info"
#             }
#         },
#         {
#             "$group": {
#                 "_id": {
#                     "created_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
#                     "modified_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$modified_on"}},
#                     "modified_by": "$modified_by"
#                 },
#                 "count": {"$sum": 1},
#                 "docs": {
#                     "$push": {
#                         "_id": "$_id",
#                         "employee_details_id": "$employee_details_id",
#                         "employee_name": {"$arrayElemAt": ["$employee_info.first_name", 0]},
#                         "adjustment_days": "$adjustment_days",
#                         "before_adjustment": "$before_adjustment",
#                         "after_adjustment": "$after_adjustment",
#                         "created_at": "$created_at",
#                         "modified_on": "$modified_on",
#                         # Include leave info fields
#                         "leave_from": {"$arrayElemAt": ["$leave_info.leave_from", 0]},
#                         "approved_on": {"$arrayElemAt": ["$leave_info.approved_on", 0]},
#                     }
#                 }
#             }
#         },
#         {
#             "$match": {
#                 "count": {"$gt": 1}
#             }
#         }
#     ]
#     # pipeline = [
#     #     {
#     #         "$match": {
#     #             "company_id": ObjectId(company_id),
#     #         }
#     #     },
#     #     {
#     #         "$lookup": {
#     #             "from": "employee_details",
#     #             "localField": "employee_details_id",
#     #             "foreignField": "_id",
#     #             "as": "employee_info"
#     #         }
#     #     },
#     #     {
#     #         "$lookup": {
#     #             "from": "employee_leave_application",
#     #             "localField": "_id",  # Assuming leave_adjustment is referenced by _id
#     #             "foreignField": "leave_adjustment",
#     #             "as": "leave_info"
#     #         }
#     #     },
#     #     # {
#     #     #     "$addFields": {
#     #     #         # Adding a comparison between created_at and leave_from (from leave_info)
#     #     #         "matching_leave_info": {
#     #     #             "$filter": {
#     #     #                 "input": "$leave_info",
#     #     #                 "as": "leave",
#     #     #                 "cond": {
#     #     #                     "$eq": [
#     #     #                         {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
#     #     #                         {"$dateToString": {"format": "%Y-%m-%d", "date": "$$leave.leave_from"}}
#     #     #                     ]
#     #     #                 }
#     #     #             }
#     #     #         }
#     #     #     }
#     #     # },
#     #     {
#     #         "$group": {
#     #             "_id": {
#     #                 "created_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
#     #                 "modified_date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$modified_on"}},
#     #                 "modified_by": "$modified_by"
#     #             },
#     #             "count": {"$sum": 1},
#     #             "docs": {
#     #                 "$push": {
#     #                     "_id": "$_id",
#     #                     "employee_details_id": "$employee_details_id",
#     #                     "employee_name": {"$arrayElemAt": ["$employee_info.first_name", 0]},
#     #                     "adjustment_days": "$adjustment_days",
#     #                     "before_adjustment": "$before_adjustment",
#     #                     "after_adjustment": "$after_adjustment",
#     #                     "created_at": "$created_at",
#     #                     "modified_on": "$modified_on",
#     #                     # Include matching leave info fields
#     #                     "leave_from": {"$arrayElemAt": ["$matching_leave_info.leave_from", 0]},
#     #                     "approved_on": {"$arrayElemAt": ["$matching_leave_info.approved_on", 0]},
#     #                 }
#     #             }
#     #         }
#     #     },
#     #     {
#     #     "$match": {
#     #         "count": {"$gt": 1}
#     #     }
#     # }
#     # ]




#     # Run the aggregation on the filtered collection
#     duplicates = list(collection.aggregate(pipeline))

#     # Sort docs within each duplicate by employee_name in ascending order
#     for duplicate in duplicates:
#         created_date = duplicate['_id']['created_date']
#         duplicate['docs'].sort(key=lambda x: (created_date, x['employee_name']))  # Sort by created_date then by employee name

#     # Render the template with the duplicates
#     return render_template('company/adjustments/duplicates.html', duplicates=duplicates)



# @company.route('/deleteadjustment123/<string:doc_id>', methods=['get'])
# @login_required
# def deleteadjustment123(doc_id):
#     try:
#         # Find and delete the document by ObjectId
#         adjustment = EmployeeLeaveAdjustment.objects(_id=ObjectId(doc_id)).first()
        
#         if adjustment:
#             adjustment.delete()
#             return jsonify({"success": True, "message": "Adjustment deleted successfully."}), 200
#         else:
#             return jsonify({"error": "Adjustment not found."}), 404
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500



# Added by Ashiq date : 25/09/2024   issues : accrual leave issues

# @company.route('/MonthlyAccrualLeaves/<int:day>/<int:month>/<int:year>')
# def monthly_accrual_leaves(day, month, year):
#     # Convert the day, month, and year into a datetime object
#     # current_date_1 = datetime(year, month, day)

#     # # Subtract one month from the current date
#     # previous_month_date = current_date_1 - relativedelta(months=1)
#     current_date = datetime(year, month, day)  # Monthly Ending Date

#     company_details = CompanyDetails.objects().all()

#     for company_detail in company_details:
#         leave_adjustments = []
#         active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
#         one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']
#         if one_time_leave_policies:
#             for employee in active_employees:
#                 if employee.employee_company_details.date_of_joining:
#                     try:
#                         date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
#                         days_worked = (current_date - date_of_joining).days
#                         if days_worked < 365:
#                             for leave_policy in one_time_leave_policies:
#                                 new_leave_balance = 0
#                                 prorated_accruals = 0
#                                 employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy, employee_details_id=employee._id).first()

#                                 # Check if the current month is the joining month
#                                 if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
#                                     prorated_accruals = (days_worked / 30) * 2

#                                 if employee_leave_policy:
#                                     new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days))
#                                 else:
#                                     new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days)
#                                     employee_leave_policy = EmployeeLeavePolicies()
#                                     employee_leave_policy.company_id = company_detail.user_id
#                                     employee_leave_policy.employee_details_id = employee._id
#                                     employee_leave_policy.leave_policy_id = leave_policy._id
#                                     employee_leave_policy.balance = new_leave_balance
#                                     employee_leave_policy.save()
#                                     employee.update(push__employee_leave_policies=employee_leave_policy._id)

#                                 if new_leave_balance > 0:
#                                     previous_month = (current_date  - timedelta(days=30)).strftime("%B %Y")
#                                     adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month

#                                     new_data = EmployeeLeaveAdjustment(
#                                         company_id=company_detail.user_id,
#                                         employee_details_id=employee._id,
#                                         employee_leave_pol_id=employee_leave_policy._id,
#                                         adjustment_type='increment',
#                                         adjustment_days=str(new_leave_balance),
#                                         adjustment_comment=adjustment_comment,
#                                         before_adjustment=str(employee_leave_policy.balance),
#                                         after_adjustment=str(new_leave_balance),
#                                         created_at= current_date.strftime("%d %B %Y %H:%M:%S")
#                                     )
#                                     status = new_data.save()
#                                     employee_leave_policy.update(push__employee_leave_adjustments=new_data._id, balance=new_leave_balance)
#                         else:
#                             for leave_policy in one_time_leave_policies:
#                                 new_leave_balance = 0
#                                 prorated_accruals = 0
#                                 employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy, employee_details_id=employee._id).first()

#                                 if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
#                                     prorated_accruals = (days_worked / 30) * 2.5

#                                 if employee_leave_policy:
#                                     new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days))
#                                 else:
#                                     new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days)
#                                     employee_leave_policy = EmployeeLeavePolicies()
#                                     employee_leave_policy.company_id = company_detail.user_id
#                                     employee_leave_policy.employee_details_id = employee._id
#                                     employee_leave_policy.leave_policy_id = leave_policy._id
#                                     employee_leave_policy.balance = new_leave_balance
#                                     employee_leave_policy.save()
#                                     employee.update(push__employee_leave_policies=employee_leave_policy._id)

#                                 if new_leave_balance > 0:
#                                     previous_month = (current_date - timedelta(days=30)).strftime("%B %Y")
#                                     adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month
#                                     new_data = EmployeeLeaveAdjustment(
#                                         company_id=company_detail.user_id,
#                                         employee_details_id=employee._id,
#                                         employee_leave_pol_id=employee_leave_policy._id,
#                                         adjustment_type='increment',
#                                         adjustment_days=str(new_leave_balance),
#                                         adjustment_comment=adjustment_comment,
#                                         before_adjustment=str(employee_leave_policy.balance),
#                                         after_adjustment=str(new_leave_balance),
#                                         created_at= current_date.strftime("%d %B %Y %H:%M:%S")
#                                     )
#                                     status = new_data.save()
#                                     employee_leave_policy.update(push__employee_leave_adjustments=new_data._id, balance=new_leave_balance)

#                     except ValueError:
#                         continue

#     # Format the current date and time to be displayed in the response
#     processed_datetime = current_date.strftime("%d %B %Y %H:%M:%S")
#     return f"Accrual Leaves Processed Successfully on {processed_datetime}"


# @company.route('/Monthlyadjustment/<int:day>/<int:month>/<int:year>/<company_id>')
# def monthly_adjustment_leaves(day, month, year):
#     current_date = datetime(year, month, day)
#     company_id=company_id
#     employee_details = EmployeeLeaveAdjustment.objects(
#         company_id=company_id, 
#         adjustment_date__lte=current_date
#     ).all()


    



@company.route('/MonthlyAccrualLeaves/<int:day>/<int:month>/<int:year>')
def monthly_accrual_leaves1(day, month, year):
    # Convert the day, month, and year into a datetime object
    current_date = datetime(year, month, day)  # Monthly Ending Date

    company_details = CompanyDetails.objects().all()

    for company_detail in company_details:
        leave_adjustments = []
        active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
        one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']
        
        if one_time_leave_policies:
            for employee in active_employees:
                if employee.employee_company_details.date_of_joining:
                    try:
                        date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
                        days_worked = (current_date - date_of_joining).days
                        
                        # If the employee has worked less than 365 days
                        if days_worked < 365:
                            for leave_policy in one_time_leave_policies:
                                new_leave_balance = 0
                                prorated_accruals = 0
                                employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy, employee_details_id=employee._id).first()

                                # Check if the current month is the joining month
                                if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
                                    prorated_accruals = (days_worked / 30) * 2.5

                                if employee_leave_policy:
                                    # Get the last leave adjustment for this employee policy
                                    last_adjustment = EmployeeLeaveAdjustment.objects(employee_leave_pol_id=employee_leave_policy._id).order_by('-created_at').first()
                                    
                                    # Check if the last adjustment was done today
                                    if last_adjustment and last_adjustment.created_at.strftime("%d %B %Y") == current_date.strftime("%d %B %Y"):
                                        continue  # Skip if adjustment was already made today
                                    
                                    new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days))
                                else:
                                    new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days)
                                    employee_leave_policy = EmployeeLeavePolicies()
                                    employee_leave_policy.company_id = company_detail.user_id
                                    employee_leave_policy.employee_details_id = employee._id
                                    employee_leave_policy.leave_policy_id = leave_policy._id
                                    employee_leave_policy.balance = new_leave_balance
                                    employee_leave_policy.save()
                                    employee.update(push__employee_leave_policies=employee_leave_policy._id)

                                if new_leave_balance > 0:
                                    previous_month = (current_date - timedelta(days=30)).strftime("%B %Y")
                                    adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month

                                    new_data = EmployeeLeaveAdjustment(
                                        company_id=company_detail.user_id,
                                        employee_details_id=employee._id,
                                        employee_leave_pol_id=employee_leave_policy._id,
                                        adjustment_type='increment',
                                        adjustment_days=str(new_leave_balance),
                                        adjustment_comment=adjustment_comment,
                                        before_adjustment=str(employee_leave_policy.balance),
                                        after_adjustment=str(new_leave_balance),
                                        created_at=current_date.strftime("%d %B %Y %H:%M:%S")
                                    )
                                    status = new_data.save()
                                    employee_leave_policy.update(push__employee_leave_adjustments=new_data._id, balance=new_leave_balance)
                        
                        # If the employee has worked 365 days or more
                        else:
                            for leave_policy in one_time_leave_policies:
                                new_leave_balance = 0
                                prorated_accruals = 0
                                employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy, employee_details_id=employee._id).first()

                                if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
                                    prorated_accruals = (days_worked / 30) * 2.5

                                if employee_leave_policy:
                                    # Get the last leave adjustment for this employee policy
                                    last_adjustment = EmployeeLeaveAdjustment.objects(employee_leave_pol_id=employee_leave_policy._id).order_by('-created_at').first()
                                    
                                    # Check if the last adjustment was done today
                                    if last_adjustment and last_adjustment.created_at.strftime("%d %B %Y") == current_date.strftime("%d %B %Y"):
                                        continue  # Skip if adjustment was already made today

                                    new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days))
                                else:
                                    new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days)
                                    employee_leave_policy = EmployeeLeavePolicies()
                                    employee_leave_policy.company_id = company_detail.user_id
                                    employee_leave_policy.employee_details_id = employee._id
                                    employee_leave_policy.leave_policy_id = leave_policy._id
                                    employee_leave_policy.balance = new_leave_balance
                                    employee_leave_policy.save()
                                    employee.update(push__employee_leave_policies=employee_leave_policy._id)

                                if new_leave_balance > 0:
                                    previous_month = (current_date - timedelta(days=30)).strftime("%B %Y")
                                    adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month
                                    new_data = EmployeeLeaveAdjustment(
                                        company_id=company_detail.user_id,
                                        employee_details_id=employee._id,
                                        employee_leave_pol_id=employee_leave_policy._id,
                                        adjustment_type='increment',
                                        adjustment_days=str(new_leave_balance),
                                        adjustment_comment=adjustment_comment,
                                        before_adjustment=str(employee_leave_policy.balance),
                                        after_adjustment=str(new_leave_balance),
                                        created_at=current_date.strftime("%d %B %Y %H:%M:%S")
                                    )
                                    status = new_data.save()
                                    employee_leave_policy.update(push__employee_leave_adjustments=new_data._id, balance=new_leave_balance)

                    except ValueError:
                        continue

    # Format the current date and time to be displayed in the response
    processed_datetime = current_date.strftime("%d %B %Y %H:%M:%S")
    return f"Accrual Leaves Processed Successfully on {processed_datetime}"



@celery.task(track_started = True,result_extended=True,name='Monthly-Accrual-Leaves')
def monthly_accrual_leaves():
    # logging.info("Running monthly leave accrual task.")
    # print("Monthly leave accrual task is running...")
    # return True

    current_date = datetime.now() # Monthly Ending Date
    # # Find the first day of the next month
    # first_day_of_next_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    # # Subtract one day to get the end of the current month
    # current_date = first_day_of_next_month - timedelta(days=1)
    company_details = CompanyDetails.objects().all()

    for company_detail in company_details:
        leave_adjustments = []
        active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
        one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']
        if one_time_leave_policies:
            for employee in active_employees:
                if employee.employee_company_details.date_of_joining:
                    try:
                        date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
                        # Further processing for valid dates
                        date_of_joining=datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
                        days_worked = (current_date - date_of_joining).days
                        if days_worked < 365:
                            # print("Less Than 1 Year of Joining");
                            for leave_policy in one_time_leave_policies:
                                new_leave_balance = 0 
                                before_adjustment = 0
                                prorated_accruals = 0
                                employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
                                # Check if the current month is the joining month of the employee
                                # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
                                # no of days worked = current_date - joining_date
                                # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
                                                        # OR
                                # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
                                # Check if the current month is the joining month
                                if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
                                    # if days_worked < 365:  # Assuming probation period is less than a year
                                    prorated_accruals = (days_worked / 30) * 2.5
                                    # else:
                                    #     prorated_accruals = (days_worked / 30) * 2.5
                                if employee_leave_policy:
                                        print(employee_leave_policy) 
                                        before_adjustment = employee_leave_policy.balance
                                        new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days))
                                else:
                                        #create New with the new amount    
                                        new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days)
                                        employee_leave_policy = EmployeeLeavePolicies()
                                        employee_leave_policy.company_id = company_detail.user_id
                                        employee_leave_policy.employee_details_id = employee._id
                                        employee_leave_policy.leave_policy_id = leave_policy._id
                                        employee_leave_policy.balance = new_leave_balance
                                        employee_leave_policy.save()
                                        employee.update(push__employee_leave_policies=employee_leave_policy._id)
                                        
                                if  new_leave_balance > 0:     
                                        previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
                                        adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month  
                                        # adjustment_comment = 'Monthly Accrual Adjustment for Month ' + datetime.now().strftime("%B %Y")
                                        new_data = EmployeeLeaveAdjustment(
                                                    company_id = company_detail.user_id,
                                                    employee_details_id =  employee._id,
                                                    employee_leave_pol_id = employee_leave_policy._id, 
                                                    adjustment_type = 'increment',
                                                    adjustment_days = str(new_leave_balance),
                                                    adjustment_comment = adjustment_comment,
                                                    before_adjustment=  str(employee_leave_policy.balance),
                                                    after_adjustment = str(new_leave_balance)
                                                )
                                        status = new_data.save()
                                        company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
                        else:
                            # print("More Than 1 year of joining");
                            for leave_policy in one_time_leave_policies:
                                new_leave_balance = 0 
                                before_adjustment = 0
                                prorated_accruals = 0
                                employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
                                # Check if the current month is the joining month of the employee
                                # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
                                # no of days worked = current_date - joining_date
                                # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
                                                        # OR
                                # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
                                # Check if the current month is the joining month
                                if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
                                        prorated_accruals = (days_worked / 30) * 2.5 
                                if employee_leave_policy:
                                        before_adjustment = employee_leave_policy.balance
                                        new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days))
                                else:
                                        #create New with the new amount     
                                        new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days)
                                        employee_leave_policy = EmployeeLeavePolicies()
                                        employee_leave_policy.company_id = company_detail.user_id
                                        employee_leave_policy.employee_details_id = employee._id
                                        employee_leave_policy.leave_policy_id = leave_policy._id
                                        employee_leave_policy.balance = new_leave_balance
                                        employee_leave_policy.save()
                                        employee.update(push__employee_leave_policies=employee_leave_policy._id)
                                if  new_leave_balance > 0:       
                                    previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
                                    adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month
                                    print(adjustment_comment)
                                    new_data = EmployeeLeaveAdjustment(
                                                company_id = company_detail.user_id,
                                                employee_details_id =  employee._id,
                                                employee_leave_pol_id = employee_leave_policy._id, 
                                                adjustment_type = 'increment',
                                                adjustment_days = str(new_leave_balance),
                                                adjustment_comment = adjustment_comment,
                                                before_adjustment=  str(employee_leave_policy.balance),
                                                after_adjustment = str(new_leave_balance)
                                            )
                                    status = new_data.save()
                                    company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
                    except ValueError:
                        # Handling for invalid date format
                        continue
    return True
                        
# @celery.task(track_started = True,result_extended=True,name='Yearly-Reset-Leaves')
# def yearly_reset_leaves():
#     current_date = datetime.now() # Monthly Ending Date
#     # # Find the first day of the next month
#     # first_day_of_next_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
#     # # Subtract one day to get the end of the current month
#     # current_date = first_day_of_next_month - timedelta(days=1)
#     company_details = CompanyDetails.objects().all()
#     employees_details = EmployeeDetails.objects.all()
#     for company_detail in company_details:
#         leave_adjustments = []    
#         active_employees = list(filter(lambda x:x['employee_company_details']['status']==True,employees_details.employees))
#         annual_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'annual']
#         # active_employees = list(filter(lambda x:x['_id']==ObjectId('62aae4481adf764c58786e54'),company_detail.employees))
#         for employee in active_employees:
#             for leave_policy in annual_leave_policies:
#                 new_leave_balance = leave_policy.allowance_days 
#                 before_adjustment = 0
#                 employee_leave_policy = EmployeeLeavePolicies.objects(employee_details_id=employee._id,leave_policy_id=leave_policy._id,company_id=company_detail.user_id).first()
#                 if employee_leave_policy:
#                         before_adjustment = employee_leave_policy.balance
#                         new_leave_balance = float(new_leave_balance)
#                         print(employee_leave_policy.leave_policy_id.leave_policy_name)
#                         print("new_leave_balance",new_leave_balance)
#                         previous_year = (datetime.now() - timedelta(days=30)).strftime("%Y")
#                         adjustment_comment = 'Yearly Reset of the Leave for Year ' +  previous_year
#                         new_data = EmployeeLeaveAdjustment(
#                                     company_id = company_detail.user_id,
#                                     employee_details_id =  employee._id,
#                                     employee_leave_pol_id = employee_leave_policy._id, 
#                                     adjustment_type = 'increment',
#                                     adjustment_days = str(new_leave_balance),
#                                     adjustment_comment = adjustment_comment,
#                                     before_adjustment=  str(employee_leave_policy.balance),
#                                     after_adjustment = str(new_leave_balance)
#                                 )
#                         status = new_data.save()
#                         company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
#     return True
@celery.task(track_started=True, result_extended=True, name='Yearly-Reset-Leaves')
def yearly_reset_leaves(reset_date=None):
    """
    Reset employee leave balances for the specified year based on the provided date.
    If no date is provided, default to the current date.
    """
    if reset_date:
        reset_date = datetime.strptime(reset_date, "%Y-%m-%d")
    else:
        reset_date = datetime.now()  # Use the current date if none provided

    reset_year = reset_date.year

    company_details = CompanyDetails.objects().all()
    employees_details = EmployeeDetails.objects().all()

    for company_detail in company_details:
        active_employees = list(
            filter(lambda x: x['employee_company_details']['status'] == True, employees_details.employees)
        )
        annual_leave_policies = [
            leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'annual'
        ]

        for employee in active_employees:
            for leave_policy in annual_leave_policies:
                new_leave_balance = leave_policy.allowance_days
                before_adjustment = 0

                employee_leave_policy = EmployeeLeavePolicies.objects(
                    employee_details_id=employee._id,
                    leave_policy_id=leave_policy._id,
                    company_id=company_detail.user_id
                ).first()

                if employee_leave_policy:
                    before_adjustment = employee_leave_policy.balance
                    new_leave_balance = float(new_leave_balance)

                    print(employee_leave_policy.leave_policy_id.leave_policy_name)
                    print("new_leave_balance", new_leave_balance)

                    adjustment_comment = 'Yearly Reset of the Leave for Year ' + str(reset_year)

                    new_data = EmployeeLeaveAdjustment(
                        company_id=company_detail.user_id,
                        employee_details_id=employee._id,
                        employee_leave_pol_id=employee_leave_policy._id,
                        adjustment_type='increment',
                        adjustment_days=str(new_leave_balance),
                        adjustment_comment=adjustment_comment,
                        before_adjustment=str(employee_leave_policy.balance),
                        after_adjustment=str(new_leave_balance)
                    )

                    status = new_data.save()
                    company_details = employee_leave_policy.update(
                        push__employee_leave_adjustments=new_data._id, balance=new_leave_balance
                    )

    return True




@company.route('/yearly_reset_leaves/<int:day>/<int:month>/<int:year>', methods=['GET'])
def yearly_reset_leaves_route(day, month, year):
    try:
        # Parse the reset date based on the URL parameters or use the current date if not provided
        reset_date = datetime(year, month, day)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    # Trigger the Celery task to reset leaves
    task = yearly_reset_leaves.delay(reset_date=reset_date)

    company_details = CompanyDetails.objects().all()
    employees_details = EmployeeDetails.objects().all()

    for company_detail in company_details:
        # Get active employees directly from employees_details
        active_employees = list(
            filter(lambda x: x['employee_company_details']['status'] == True, employees_details)
        )
        annual_leave_policies = [
            leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'annual'
        ]

        for employee in active_employees:
            for leave_policy in annual_leave_policies:
                new_leave_balance = leave_policy.allowance_days
                before_adjustment = 0

                employee_leave_policy = EmployeeLeavePolicies.objects(
                    employee_details_id=employee._id,
                    leave_policy_id=leave_policy._id,
                    company_id=company_detail.user_id
                ).first()

                if employee_leave_policy:
                    before_adjustment = employee_leave_policy.balance
                    new_leave_balance = float(new_leave_balance)

                    # Format the date to include it in the adjustment comment
                    formatted_date = reset_date.strftime('%Y-%m-%d')

                    # Get the current date and time for created_at
                    current_date = datetime.now()
                    created_at = datetime(year, month, day).strftime("%d %B %Y %H:%M:%S")  # Format: '09 December 2024 14:30:45'

                    # Check if an adjustment already exists for the same year, employee, and leave policy
                    existing_adjustment = EmployeeLeaveAdjustment.objects(
                        employee_details_id=employee._id,
                        employee_leave_pol_id=employee_leave_policy._id,
                        created_at__startswith=formatted_date  # Match the date part of created_at
                    ).first()

                    if existing_adjustment:
                        # If an adjustment already exists, skip creating a new one
                        continue

                    # Construct the adjustment comment including the formatted date
                    adjustment_comment = f"Yearly Reset of the Leave for Year {formatted_date}"

                    # Create the leave adjustment record
                    new_data = EmployeeLeaveAdjustment(
                        company_id=company_detail.user_id,
                        employee_details_id=employee._id,
                        employee_leave_pol_id=employee_leave_policy._id,
                        adjustment_type='increment',
                        adjustment_days=str(new_leave_balance),  # Convert the numeric value to a string
                        adjustment_comment=adjustment_comment,
                        before_adjustment=str(before_adjustment),  # Convert before_adjustment to a string
                        after_adjustment=str(new_leave_balance),   # Convert after_adjustment to a string
                        created_at=created_at  # Add the current date and time
                    )

                    status = new_data.save()

                    # Update the leave policy balance and append the adjustment to the employee's record
                    employee_leave_policy.update(
                        push__employee_leave_adjustments=new_data._id,
                        balance=new_leave_balance
                    )

    # Return response after triggering the task
    return jsonify({
        "status": "success",
        "message": f"Yearly reset leave task initiated for {reset_date.strftime('%Y-%m-%d')}",
        "task_id": task.id
    }), 200


from celery import shared_task
@shared_task
def run_monthly_accrual_leaves12():
    logging.info("Running monthly leave accrual task.")

    print("Monthly accrual leaves task is being executed111112222.")
    return "Accrual leaves processed successfully111111222!"




@company.route('/test')
@login_required
def test_route():
    current_date = datetime.now() # Monthly Ending Date
    # # Find the first day of the next month
    # first_day_of_next_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    # # Subtract one day to get the end of the current month
    # current_date = first_day_of_next_month - timedelta(days=1)
    # company_details = CompanyDetails.objects(user_id=current_user.id).all()

    # for company_detail in company_details:
    #     leave_adjustments = []
    #     active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
    #     one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']
    #     if one_time_leave_policies:
    #         for employee in active_employees:
    #             if employee.employee_company_details.date_of_joining:
    #                 try:
    #                     date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
    #                     # Further processing for valid dates
    #                     date_of_joining=datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
    #                     days_worked = (current_date - date_of_joining).days
    #                     if days_worked < 365:
    #                         # print("Less Than 1 Year of Joining");
    #                         for leave_policy in one_time_leave_policies:
    #                             new_leave_balance = 0 
    #                             before_adjustment = 0
    #                             prorated_accruals = 0
    #                             employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
    #                             # Check if the current month is the joining month of the employee
    #                             # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
    #                             # no of days worked = current_date - joining_date
    #                             # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
    #                                                     # OR
    #                             # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
    #                             # Check if the current month is the joining month
    #                             if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
    #                                 # if days_worked < 365:  # Assuming probation period is less than a year
    #                                 prorated_accruals = (days_worked / 30) * 2 
    #                                 # else:
    #                                 #     prorated_accruals = (days_worked / 30) * 2.5
    #                             if employee_leave_policy:
    #                                     print(employee_leave_policy) 
    #                                     before_adjustment = employee_leave_policy.balance
    #                                     new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days))
    #                             else:
    #                                     #create New with the new amount    
    #                                     new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days)
    #                                     employee_leave_policy = EmployeeLeavePolicies()
    #                                     employee_leave_policy.company_id = company_detail.user_id
    #                                     employee_leave_policy.employee_details_id = employee._id
    #                                     employee_leave_policy.leave_policy_id = leave_policy._id
    #                                     employee_leave_policy.balance = new_leave_balance
    #                                     employee_leave_policy.save()
    #                                     employee.update(push__employee_leave_policies=employee_leave_policy._id)
                                        
    #                             if  new_leave_balance > 0:     
    #                                     previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
    #                                     adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month  
    #                                     # adjustment_comment = 'Monthly Accrual Adjustment for Month ' + datetime.now().strftime("%B %Y")
    #                                     new_data = EmployeeLeaveAdjustment(
    #                                                 company_id = company_detail.user_id,
    #                                                 employee_details_id =  employee._id,
    #                                                 employee_leave_pol_id = employee_leave_policy._id, 
    #                                                 adjustment_type = 'increment',
    #                                                 adjustment_days = str(new_leave_balance),
    #                                                 adjustment_comment = adjustment_comment,
    #                                                 before_adjustment=  str(employee_leave_policy.balance),
    #                                                 after_adjustment = str(new_leave_balance)
    #                                             )
    #                                     status = new_data.save()
    #                                     company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
    #                     else:
    #                         # print("More Than 1 year of joining");
    #                         for leave_policy in one_time_leave_policies:
    #                             new_leave_balance = 0 
    #                             before_adjustment = 0
    #                             prorated_accruals = 0
    #                             employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
    #                             # Check if the current month is the joining month of the employee
    #                             # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
    #                             # no of days worked = current_date - joining_date
    #                             # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
    #                                                     # OR
    #                             # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
    #                             # Check if the current month is the joining month
    #                             if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
    #                                     prorated_accruals = (days_worked / 30) * 2.5 
    #                             if employee_leave_policy:
    #                                     before_adjustment = employee_leave_policy.balance
    #                                     new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days))
    #                             else:
    #                                     #create New with the new amount     
    #                                     new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days)
    #                                     employee_leave_policy = EmployeeLeavePolicies()
    #                                     employee_leave_policy.company_id = company_detail.user_id
    #                                     employee_leave_policy.employee_details_id = employee._id
    #                                     employee_leave_policy.leave_policy_id = leave_policy._id
    #                                     employee_leave_policy.balance = new_leave_balance
    #                                     employee_leave_policy.save()
    #                                     employee.update(push__employee_leave_policies=employee_leave_policy._id)
    #                             if  new_leave_balance > 0:       
    #                                 previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
    #                                 adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month
    #                                 print(adjustment_comment)
    #                                 new_data = EmployeeLeaveAdjustment(
    #                                             company_id = company_detail.user_id,
    #                                             employee_details_id =  employee._id,
    #                                             employee_leave_pol_id = employee_leave_policy._id, 
    #                                             adjustment_type = 'increment',
    #                                             adjustment_days = str(new_leave_balance),
    #                                             adjustment_comment = adjustment_comment,
    #                                             before_adjustment=  str(employee_leave_policy.balance),
    #                                             after_adjustment = str(new_leave_balance)
    #                                         )
    #                                 status = new_data.save()
    #                                 company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
    #                 except ValueError:
    #                     # Handling for invalid date format
    #                     continue
    # return True
    data = []
    # api_url = "http://192.168.1.246:875/ISAPI/AccessControl/AcsEvent?format=json&devIndex=BD8C1C48-80F8-44FA-AF92-B354FE0328B4"
    api_url = "http://192.168.1.186:586/ISAPI/ContentMgmt/DeviceMgmt/deviceList?format=json"
    auth = HTTPDigestAuth('admin', 'Admin@123')
    # Set headers with Basic Authentication
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "SearchDescription": {
            "position": 0,
            "maxResult": 100,
            "Filter": {
                "devType": "AccessControl",
                "protocolType": [
                    "ISAPI"
                ],
                "devStatus": [
                    "online",
                    "offline"
                ]
            }
        }
    }
    response = requests.post(api_url, json=data, headers=headers,auth=auth)
    # response = requests.post(api_url, auth=auth)
    
    if response.status_code == 200:
        data = response.json()
        return render_template('company/test.html', data=data)
    else:
        return "Authentication failed", 401
    # company_details = CompanyDetails.objects(user_id=current_user.id).all()

    # for company_detail in company_details:
    #     leave_adjustments = []
    #     active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
    #     one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']
    #     if one_time_leave_policies:
    #         for employee in active_employees:
    #             if employee.employee_company_details.date_of_joining:
    #                 try:
    #                     date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
    #                     # Further processing for valid dates
    #                     date_of_joining=datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
    #                     days_worked = (current_date - date_of_joining).days
    #                     if days_worked < 365:
    #                         # print("Less Than 1 Year of Joining");
    #                         for leave_policy in one_time_leave_policies:
    #                             new_leave_balance = 0 
    #                             before_adjustment = 0
    #                             prorated_accruals = 0
    #                             employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
    #                             # Check if the current month is the joining month of the employee
    #                             # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
    #                             # no of days worked = current_date - joining_date
    #                             # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
    #                                                     # OR
    #                             # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
    #                             # Check if the current month is the joining month
    #                             if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
    #                                 # if days_worked < 365:  # Assuming probation period is less than a year
    #                                 prorated_accruals = (days_worked / 30) * 2 
    #                                 # else:
    #                                 #     prorated_accruals = (days_worked / 30) * 2.5
    #                             if employee_leave_policy:
    #                                     print(employee_leave_policy) 
    #                                     before_adjustment = employee_leave_policy.balance
    #                                     new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days))
    #                             else:
    #                                     #create New with the new amount    
    #                                     new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days)
    #                                     employee_leave_policy = EmployeeLeavePolicies()
    #                                     employee_leave_policy.company_id = company_detail.user_id
    #                                     employee_leave_policy.employee_details_id = employee._id
    #                                     employee_leave_policy.leave_policy_id = leave_policy._id
    #                                     employee_leave_policy.balance = new_leave_balance
    #                                     employee_leave_policy.save()
    #                                     employee.update(push__employee_leave_policies=employee_leave_policy._id)
                                        
    #                             if  new_leave_balance > 0:     
    #                                     previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
    #                                     adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month  
    #                                     # adjustment_comment = 'Monthly Accrual Adjustment for Month ' + datetime.now().strftime("%B %Y")
    #                                     new_data = EmployeeLeaveAdjustment(
    #                                                 company_id = company_detail.user_id,
    #                                                 employee_details_id =  employee._id,
    #                                                 employee_leave_pol_id = employee_leave_policy._id, 
    #                                                 adjustment_type = 'increment',
    #                                                 adjustment_days = str(new_leave_balance),
    #                                                 adjustment_comment = adjustment_comment,
    #                                                 before_adjustment=  str(employee_leave_policy.balance),
    #                                                 after_adjustment = str(new_leave_balance)
    #                                             )
    #                                     status = new_data.save()
    #                                     company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
    #                     else:
    #                         # print("More Than 1 year of joining");
    #                         for leave_policy in one_time_leave_policies:
    #                             new_leave_balance = 0 
    #                             before_adjustment = 0
    #                             prorated_accruals = 0
    #                             employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
    #                             # Check if the current month is the joining month of the employee
    #                             # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
    #                             # no of days worked = current_date - joining_date
    #                             # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
    #                                                     # OR
    #                             # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
    #                             # Check if the current month is the joining month
    #                             if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
    #                                     prorated_accruals = (days_worked / 30) * 2.5 
    #                             if employee_leave_policy:
    #                                     before_adjustment = employee_leave_policy.balance
    #                                     new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days))
    #                             else:
    #                                     #create New with the new amount     
    #                                     new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days)
    #                                     employee_leave_policy = EmployeeLeavePolicies()
    #                                     employee_leave_policy.company_id = company_detail.user_id
    #                                     employee_leave_policy.employee_details_id = employee._id
    #                                     employee_leave_policy.leave_policy_id = leave_policy._id
    #                                     employee_leave_policy.balance = new_leave_balance
    #                                     employee_leave_policy.save()
    #                                     employee.update(push__employee_leave_policies=employee_leave_policy._id)
    #                             if  new_leave_balance > 0:       
    #                                 previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
    #                                 adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month
    #                                 print(adjustment_comment)
    #                                 new_data = EmployeeLeaveAdjustment(
    #                                             company_id = company_detail.user_id,
    #                                             employee_details_id =  employee._id,
    #                                             employee_leave_pol_id = employee_leave_policy._id, 
    #                                             adjustment_type = 'increment',
    #                                             adjustment_days = str(new_leave_balance),
    #                                             adjustment_comment = adjustment_comment,
    #                                             before_adjustment=  str(employee_leave_policy.balance),
    #                                             after_adjustment = str(new_leave_balance)
    #                                         )
    #                                 status = new_data.save()
    #                                 company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
    #                 except ValueError:
    #                     # Handling for invalid date format
    #                     continue
    # return True
    # # data = []
    # # # api_url = "http://192.168.1.246:875/ISAPI/AccessControl/AcsEvent?format=json&devIndex=BD8C1C48-80F8-44FA-AF92-B354FE0328B4"
    # # api_url = "http://192.168.1.247:875/ISAPI/ContentMgmt/DeviceMgmt/deviceList?format=json"
    # # auth = HTTPDigestAuth('admin', 'admin@123')
    # # # Set headers with Basic Authentication
    # # headers = {
    # #     'Content-Type': 'application/json',
    # # }
    # # data = {
    # #     "SearchDescription": {
    # #         "position": 0,
    # #         "maxResult": 100,
    # #         "Filter": {
    # #             "key": company_key,
    # #             "devType": "AccessControl",
    # #             "protocolType": [
    # #                 "ISAPI"
    # #             ],
    # #             "devStatus": [
    # #                 "online",
    # #                 "offline"
    # #             ]
    # #         }
    # #     }
    # # }
    # # response = requests.post(api_url, json=data, headers=headers,auth=auth)
    # # # response = requests.post(api_url, auth=auth)
    
    # # if response.status_code == 200:
    # #     data = response.json()
    # #     return render_template('company/test.html', data=data)
    # # else:
    # #     return "Authentication failed", 401

@company.route('/device_attendance_list')
@company.route('/device_attendance_list/<deviceIndex>/<search_result_position>', methods=['GET','POST'])
def device_attendance_list(deviceIndex, search_result_position=0,Inforecords=None):
    if Inforecords is None:
       Inforecords = []

    api_url = "http://192.168.1.247:245//ISAPI/AccessControl/AcsEvent?format=json&devIndex=" + deviceIndex
    auth = HTTPDigestAuth('admin', 'Admin@123')

    headers = {
        'Content-Type': 'application/json',
    }
    # Get the current date in UTC
    current_date = datetime.now(timezone.utc).date()

    # Start of the day
    start_of_day = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc)
    formatted_start_of_day = start_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')

    # End of the day
    end_of_day = datetime.combine(current_date, datetime.max.time(), tzinfo=timezone.utc)
    formatted_end_of_day = end_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')
    data = {
        "AcsEventCond": {
            "searchID": str(random.randint(0,9999999999)),
            "searchResultPosition": int(search_result_position),
            "maxResults": 300,
            "startTime": formatted_start_of_day,
            "endTime": formatted_end_of_day
        }
    }
    # response = requests.post(api_url, json=data, headers=headers, auth=auth)

    # Create example documents


    # record = AccessRecord(
    #     id=ObjectId(oid="667ffad450eb02c0aeaf7558"),
    #     internet_access=0,
    #     mac_addr="",
    #     rs485_no=0,
    #     access_channel=0,
    #     alarm_in_no=0,
    #     alarm_out_no=0,
    #     attendance_status="checkIn",
    #     card_no="",
    #     card_reader_kind=0,
    #     card_reader_no=1,
    #     card_type=1,
    #     case_sensor_no=0,
    #     device_no=0,
    #     distract_control_no=0,
    #     door_no=1,
    #     employee_no_string="5",
    #     local_controller_id=0,
    #     major=5,
    #     minor=38,
    #     multi_card_group_no=0,
    #     net_user="",
    #     remote_host_addr="0.0.0.0",
    #     report_channel=0,
    #     serial_no=278,
    #     status_value=1,
    #     swipe_card_type=0,
    #     time=datetime.strptime("2024-06-29T12:42:13+08:00", "%Y-%m-%dT%H:%M:%S%z"),
    #     record_type=0,
    #     verify_no=0,
    #     white_list_no=0
    # )
    # record.save()

    attandance = BioMetricActivity.with_employee_name()

    # if response.status_code == 200:
    #     records = response.json()["AcsEvent"]
    #     if records["numOfMatches"] > 0:
    #         Inforecords.extend(records["InfoList"])
    #         if records["responseStatusStrg"] == "MORE" and int(search_result_position) <= records["totalMatches"]:
    #             next_search_result_position = int(search_result_position) + records["numOfMatches"]
                # more_records = device_attendance_list(deviceIndex, next_search_result_position,Inforecords)

        #     return render_template('company/test2.html', data=attandance, deviceIndex=deviceIndex,current_search_position=search_result_position)
    #     # else:
    #         return render_template('company/test2.html', data=Inforecords, deviceIndex=deviceIndex)
    # else:
        # return render_template('company/test2.html', data=Inforecords, deviceIndex=deviceIndex)
    return render_template('company/test2.html', data=attandance, deviceIndex=deviceIndex)



@company.route('/device_persons_list')
@company.route('/device_persons_list/<deviceIndex>/<search_result_position>', methods=['GET','POST'])
def device_persons_list(deviceIndex, search_result_position=0,Inforecords=None):
    company_details = CompanyDetails.objects(user_id=current_user.id).first()
    data_ids = ()
    if Inforecords is None:
       Inforecords = []
    api_url = "http://192.168.1.186:586/ISAPI/AccessControl/UserInfo/Search?format=json&devIndex=" + deviceIndex
    auth = HTTPDigestAuth('admin', 'Admin@123')

    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "UserInfoSearchCond": {
            "searchID": "123",
            "searchResultPosition": 0,
            "maxResults": 300
        }
    }
    response = requests.post(api_url, json=data, headers=headers, auth=auth)



    users = BioMetricUserData.objects(deviceId=deviceIndex).all()

    if response.status_code == 200:
        records = response.json()["UserInfoSearch"]
        if records["numOfMatches"] > 0:
            Inforecords.extend(records["UserInfo"])
            if records["responseStatusStrg"] == "MORE" and int(search_result_position) <= records["totalMatches"]:
                next_search_result_position = int(search_result_position) + records["numOfMatches"]
                more_records = device_persons_list(deviceIndex, next_search_result_position,Inforecords)
            # Preprocess the data to get employee_ids
            data_ids = set(data_item['employeeNo'] for data_item in Inforecords)


    
            return render_template('company/test3.html', data=users, deviceIndex=deviceIndex,current_search_position=search_result_position,company_details=company_details,data_ids=data_ids)
        else:
            return render_template('company/test3.html', data=Inforecords, deviceIndex=deviceIndex)
    else:
        return render_template('company/test3.html', data=Inforecords, deviceIndex=deviceIndex)

@company.route('/real_time_device_attendance_list')
@company.route('/real_time_device_attendance_list/<deviceIndex>/<search_result_position>', methods=['GET','POST'])
def real_time_device_attendance_list(deviceIndex, search_result_position=0,Inforecords=None):
    if Inforecords is None:
       Inforecords = []
    api_url = "http://192.168.1.247:245//ISAPI/AccessControl/AcsEvent?format=json&devIndex=" + deviceIndex
    auth = HTTPDigestAuth('admin', 'Admin@123')

    headers = {
        'Content-Type': 'application/json',
    }
    # Get the current date in UTC
    current_date = datetime.now(timezone.utc).date()

    # Start of the day
    start_of_day = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc)
    formatted_start_of_day = start_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')

    # End of the day
    end_of_day = datetime.combine(current_date, datetime.max.time(), tzinfo=timezone.utc)
    formatted_end_of_day = end_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')
    data = {
        "AcsEventCond": {
            "searchID": str(random.randint(0,9999999999)),
            "searchResultPosition": int(search_result_position),
            "maxResults": 300,
            "startTime": formatted_start_of_day,
            "endTime": formatted_end_of_day
        }
    }
    response = requests.post(api_url, json=data, headers=headers, auth=auth)

    if response.status_code == 200:
        records = response.json()["AcsEvent"]
        if records["numOfMatches"] > 0:
            Inforecords.extend(records["InfoList"])
            if records["responseStatusStrg"] == "MORE" and int(search_result_position) <= records["totalMatches"]:
                next_search_result_position = int(search_result_position) + records["numOfMatches"]
                more_records = device_attendance_list(deviceIndex, next_search_result_position,Inforecords)
           
            return json.dumps(Inforecords)
            # return render_template('company/test2.html', data=Inforecords, deviceIndex=deviceIndex,current_search_position=search_result_position)
        else:
            return json.dumps(Inforecords)
    else:
        return json.dumps(Inforecords)

@company.route('/checkbgtasks/')
def check_bg_tasks():
    # bg_tasks = ScheduledBackgroundTask.objects(company_id=current_user.id)
    bg_tasks = ScheduledBackgroundTask.objects(company_id=current_user.id).order_by('-uploaded_on').select_related(max_depth=1)[:10]
    tasks = []
    for task in bg_tasks:
        task_dict = {}
        task_dict['task_type'] = task.task_type
        # task_dict['celery_task'] = task.celery_task_id._id
        task_dict['status'] = task.celery_task_id.status
        task_dict['message'] = task.message
        task_dict['uploaded_on'] = task.uploaded_on
        task_dict['date_done'] = task.celery_task_id.date_done
        task_dict['result'] = task.celery_task_id.result
        tasks.append(task_dict)
    return jsonify(tasks)   


@company.route('/markhalfattendance/', methods=['POST'])
@login_required
@roles_accepted('company','supervisor','attendancemanager')
def mark_half_attendance():
    if request.method == 'POST':
        attendance_id = request.form.get('attendance_id')
        attendance_details = EmployeeAttendance.objects(_id=ObjectId(attendance_id)).first()
        
        employee_details= EmployeeDetails.objects(_id=attendance_details.employee_details_id._id).first()
        
        adjustment_reason = CompanyAdjustmentReasons.objects(company_id=employee_details.company_id,adjustment_reason="Half Day Unpaid Leaves").first()
        if not adjustment_reason:
            adjustment_reason = create_adjustment_reason(employee_details.company_id,"Half Day Unpaid Leaves","deduction")
            
        # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
        total_salary = employee_details.employee_company_details.total_salary
        
        current_month = attendance_details.attendance_date.strftime('%B')
        start_of_month = attendance_details.attendance_date.replace(day=1)
        nxt_mnth = attendance_details.attendance_date.replace(day=28) + timedelta(days=4)
        # subtracting the days from next month date to
        # get last date of current Month
        end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
        
        calendar_working_days = CompanyDetails.objects(user_id=employee_details.company_id).only('working_days').first()
        # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
        working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))

        no_of_working_days = int(working_days[0]['days']) if working_days else end_of_the_month.days() # By Default Set to 30 Days
                            
        adjustment_amount = round((int(total_salary)/no_of_working_days)/2,0)
        
        new_data = CompanyPayrollAdjustment(
                company_id = employee_details.company_id,
                employee_details_id = employee_details._id,
                adjustment_reason_id = adjustment_reason._id,
                adjustment_type = adjustment_reason.adjustment_type,
                adjustment_amount = str(adjustment_amount),
                adjustment_on = start_of_month,
                adjustment_month_on_payroll = start_of_month.strftime('%B'),
                adjustment_year_on_payroll =  start_of_month.year,
                attendance_date =  attendance_details.attendance_date,                   
        )
        status = attendance_details.update(set__half_day = True) 
        new_data.save()
            
        # todo: Create a record in Activity Log 
        activity_log = create_activity_log(request,current_user.id,employee_details.company_id)
        if status:
            msg =  json.dumps({"status":"success"})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))

@company.route('/assign/superapprover/', methods=['POST'])
def assign_super_approver():
    if request.method == 'POST':
        employee_list = request.form.getlist('employees[]')
    if employee_list:
        for employee_detail_id in employee_list:
            # todo: Create a company assigned role record; then assign role on user level
            employee_details = EmployeeDetails.objects(_id=ObjectId(employee_detail_id)).first()
            super_leave_approver = SuperLeaveApprovers(
                                    company_id = current_user.id,
                                    employee_details_id = employee_details._id,
            ).save()
            status = employee_details.update(set__is_super_leave_approver = True) 
            CompanyDetails.objects(user_id=current_user.id).update(add_to_set__super_leave_approvers=super_leave_approver._id)

    if status:
        msg =  json.dumps({'status':'success'})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml
    
@company.route('/<adjustment_id>/adjustments', methods=['GET','POST'])
@login_required
def edit_adjustment(adjustment_id):

    if request.method == 'POST':
        status = False
        start_of_month = datetime. strptime(request.form.get('selected_month'), '%Y-%m-%d')  if request.form.get('selected_month') else datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        adjustment_reason = request.form.get('adjustment_reason')
        adjustment_amount = request.form.get('adjustment_amount')
        adjustment_document = request.files.get('adjustment_document')
        adjustment_details = CompanyPayrollAdjustment.objects(_id=ObjectId(adjustment_id)).first()
        adjustment_document_name = ""
        adjustment_reason_details = CompanyAdjustmentReasons.objects(_id=ObjectId(adjustment_reason)).first()
        if adjustment_document:
            adjustment_document_name = upload_adjustment_document(adjustment_document,company_details.company_name)   
        # todo: Check if the payroll is already created
        if adjustment_details:
            if adjustment_document_name !="":
               status = adjustment_details.update(
                                        adjustment_reason_id = adjustment_reason_details._id,
                                        adjustment_type = adjustment_reason_details.adjustment_type,
                                        adjustment_amount=adjustment_amount,
                                        adjustment_document_name=adjustment_document_name,
                                        adjustment_month_on_payroll = start_of_month.strftime('%B'),
                                        adjustment_year_on_payroll =  start_of_month.year    
                                        )
            else:
               status = adjustment_details.update(adjustment_reason_id = adjustment_reason_details._id,
                                        adjustment_type = adjustment_reason_details.adjustment_type,
                                        adjustment_amount=adjustment_amount,
                                        adjustment_month_on_payroll = start_of_month.strftime('%B'),
                                        adjustment_year_on_payroll =  start_of_month.year
                                        )
                
            # # todo: Create a record in Activity Log 
            # activity_log = create_activity_log(request,current_user.id,company_id)      
        
        if status:
            flash('Adjustments Edited Successfully!', 'success')
            return redirect(url_for('company.adjustments'))
        else:
            flash('Something went Wrong. Please try again!', 'danger')
            return redirect(url_for('company.adjustments'))
    else:
        adjustment_details = CompanyPayrollAdjustment.objects(_id=ObjectId(adjustment_id)).first()
        company_details = CompanyDetails.objects(user_id=current_user.id).only('employees','adjustment_reasons','company_name','departments').first()
        return render_template('company/adjustments/edit_adjustment.html',adjustment_details=adjustment_details,company_details=company_details)

@company.route('/addpersontodevice', methods=['POST'])
def add_person_to_device():
    UserInfo = []
     # Get the current date in UTC
    current_date = datetime.now(timezone.utc).date()
    # Calculate the end date 5 years from now
    end_date_5_years = current_date + timedelta(days=5 * 365)  # Assuming 365 days per year
    # Start of the day
    start_of_day = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc)
    formatted_start_of_day = start_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')
    # End of the day
    end_of_day = datetime.combine(end_date_5_years, datetime.max.time(), tzinfo=timezone.utc)
    formatted_end_of_day = end_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')

    employee_list = request.form.getlist('employees[]')
    deviceIndex = request.form.get("deviceIndex")
    if employee_list and deviceIndex:
        for employee_detail_id in employee_list:
            employee_details = EmployeeDetails.objects(_id=ObjectId(employee_detail_id)).only("first_name","last_name","employee_company_details.employee_id").first()
            # todo: 
            if employee_details:
                user_info  = {
                    "employeeNo" : employee_details.employee_company_details.employee_id,
                    "name" : employee_details.first_name + ' ' + employee_details.last_name,
                    "Valid": {
                        "beginTime": formatted_start_of_day,
                        "endTime": formatted_end_of_day
                    }
                }
                UserInfo.append(user_info)
        if UserInfo:
            request_data = {"UserInfo": UserInfo}
            api_url = "http://192.168.1.246:875/ISAPI/AccessControl/UserInfo/Record?format=json&devIndex=" + deviceIndex
            auth = HTTPDigestAuth('admin', 'admin@123')
            headers = {
                'Content-Type': 'application/json',
            }
            response = requests.post(api_url, json=request_data, headers=headers, auth=auth)

            if response.status_code == 200:
                msg =  json.dumps({'status':'success'})
                msghtml = json.loads(msg)
                return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml

#Create Backup Biometric Attendance
# @celery.task(track_started = True,result_extended=True,name='Employee-Open-Leave-Data')
@company.route('/tempbio')
@login_required
def temp_biometric_attendance_data():
    # Get all companies collection
    company_details = CompanyDetails.objects().all()
    for company_detail in company_details:
        for employee in company_detail.employees:
            print(employee.employee_company_details.employee_id)
            # todo: Get the device List to get the device UUID
            for device in company_detail.biometric_devices:
                # todo: Call an api with employee_id,device Params(UUID,IP,Username,Password) and startTime,endTime
                attendance_list = device_attendance_list_by_user(employee.employee_company_details.employee_id,device)
                if attendance_list:
                    # todo: Check for the First Checkin and Last Checkout in response(InfoList)                   
                   attendance_data = "" 
                   attendance_data = check_first_in_last_out(attendance_list,employee.employee_company_details.employee_id)
                   if attendance_data:
                      # TODO: Save the data in temp table in our employee_attendance csv format  
                       has_attendance_data = CompanyBiometricAttendance.objects(employee_id=employee.employee_company_details.employee_id,
                                                                                company_id=current_user.id,
                                                                                attendance_date=datetime.now().date()).first()
                       if has_attendance_data:
                            has_attendance_data.update(employee_check_in_at=attendance_data[employee.employee_company_details.employee_id]["checkin"],
                                                employee_check_out_at=attendance_data[employee.employee_company_details.employee_id]["checkout"])
                            break
                       else:                           
                            company_biometric_attendance = CompanyBiometricAttendance(
                                                            company_id=current_user.id,
                                                            employee_id=employee.employee_company_details.employee_id,
                                                            device_name=device.device_name,
                                                            device_ip_address=device.device_ip_address,
                                                            device_port=device.device_port,
                                                            attendance_date=datetime.now().date(),
                                                            attendance_status="present",
                                                            employee_check_in_at=attendance_data[employee.employee_company_details.employee_id]["checkin"],
                                                            employee_check_out_at=attendance_data[employee.employee_company_details.employee_id]["checkout"]
                                                            ) 
                            company_biometric_attendance.save() 
                            break
    return True

def check_first_in_last_out(attendance_list,employee_id):
    # Dictionary to store attendance data
    attendance_data = {}
    # Loop through each entry in InfoList
    for entry in attendance_list:
        if entry["employeeNoString"] == employee_id:
            attendance_status = entry["attendanceStatus"]
            time = entry["time"]
            # Parse the time string to a datetime object
            parsed_time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
            # Check if the entry is a check-in or check-out
            if attendance_status == "checkIn":
                employee_id = entry["employeeNoString"]
                if employee_id not in attendance_data:
                    attendance_data[employee_id] = {"checkin": parsed_time, "checkout": None}
            elif attendance_status == "checkOut":
                employee_id = entry["employeeNoString"]
                if employee_id in attendance_data:
                    attendance_data[employee_id]["checkout"] = parsed_time

    # # Print the first check-in and last check-out for each employee
    # for employee_id, times in attendance_data.items():
    #     print("Employee ID:", employee_id)
    #     print("First Check-in:", times["checkin"])
    #     print("Last Check-out:", times["checkout"])
    #     print("===")  # Separator between employees
    return attendance_data

def device_attendance_list_by_user(employee_id,current_device,search_result_position=0,Inforecords=None):
    if Inforecords is None:
       Inforecords = []
    current_device_ip = current_device.device_ip_address
    current_device_port = current_device.device_port
    
    if current_device.device_index:
        api_url = "http://"+current_device_ip+":"+current_device_port+"/ISAPI/AccessControl/AcsEvent?format=json&devIndex=" + current_device.device_index
    else:
        api_url = "http://"+current_device_ip+":"+current_device_port+"/ISAPI/AccessControl/AcsEvent?format=json"
    # api_url = "http://192.168.1.246:875/ISAPI/AccessControl/AcsEvent?format=json&devIndex=" + deviceIndex
    
    if current_device.device_username and current_device.device_password:
        auth = HTTPDigestAuth(current_device.device_username, current_device.device_password)
        headers = {
            'Content-Type': 'application/json',
        }
        # Get the current date in UTC
        current_date = datetime.now(timezone.utc).date()
        # Start of the day
        start_of_day = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone.utc)
        formatted_start_of_day = start_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')
        # End of the day
        end_of_day = datetime.combine(current_date, datetime.max.time(), tzinfo=timezone.utc)
        formatted_end_of_day = end_of_day.strftime('%Y-%m-%dT%H:%M:%S%z')
        data = {
            "AcsEventCond": {
                "searchID": str(random.randint(0,9999999999)),
                "searchResultPosition": int(search_result_position),
                "maxResults": 300,
                "startTime": formatted_start_of_day,
                "endTime": formatted_end_of_day,
                "employeeNoString": employee_id,
                "major": 0,
                "minor": 0
            }
        }
        response = requests.post(api_url, json=data, headers=headers, auth=auth)
        if response.status_code == 200:
            records = response.json()["AcsEvent"]
            if records["numOfMatches"] > 0:
                Inforecords.extend(records["InfoList"])
                if records["responseStatusStrg"] == "MORE" and int(search_result_position) <= records["totalMatches"]:
                    next_search_result_position = int(search_result_position) + records["numOfMatches"]
                    more_records = device_attendance_list_by_user(employee_id,current_device, next_search_result_position,Inforecords)
            
                return Inforecords
                # return render_template('company/test2.html', data=Inforecords, deviceIndex=deviceIndex,current_search_position=search_result_position)
            else:
                return Inforecords
    else:
        return Inforecords


@company.route('/createbiometricdevice/settings/', methods=['POST'])
def create_biometric_device():
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        device_ip_address = request.form.get("device_ip_address")
        device_port = request.form.get('device_port')
        device_username = request.form.get("device_username")
        device_password = request.form.get("device_password")
        
        if device_name and device_ip_address and device_port and device_username and device_password:
            new_biometric_device =  CompanyBiometricDevice(
                                    device_name=device_name,
                                    device_ip_address=device_ip_address,
                                    device_port=device_port,
                                    device_username=device_username,
                                    device_password=device_password,
                                    company_id = current_user.id
                                    )
            new_biometric_device.save()
            update_details = CompanyDetails.objects(user_id=current_user.id).update(push__biometric_devices=new_biometric_device.id)
            if update_details:
                details = CompanyBiometricDevice.objects(company_id=current_user.id)
                msg =  json.dumps({"status":"success","details":details.to_json()})
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg =  '{ "html":"<h3>Enter the required fields</h3>"}'
            msghtml = json.loads(msg)
            return msghtml["html"]
    else:

        return render_template('company/settings.html')

#Update Sub Company
@company.route('/update/company', methods=['POST'])
@login_required
@roles_accepted('admin','company')
def update_company():
    sub_company_id = request.form.get('sub_company_id')
    company_name = request.form.get('company_name')
    company_unique_id = request.form.get('company_unique_id')
    company_account_number = request.form.get('company_account_number')
    company_routing_code = request.form.get('company_routing_code')
    company_details =  SubCompanies.objects(_id=sub_company_id).update(
        company_name = company_name,
        company_unique_id = company_unique_id,
        company_account_number = company_account_number,
        company_routing_code = company_routing_code
    )

    if company_details: 
        flash('Company updated Successfully!', 'success')
    return redirect(url_for('company.company_settings'))   
        

def get_dbref_fields(dbref):
    if isinstance(dbref, DBRef):
        # Dereference the DBRef
        referenced_doc = SCR.objects.get(id=dbref.id)
        # Get the field names
        field_names = referenced_doc._fields.keys()
        return field_names
    return None


def delete_adjustments(adjustment_ids):
    """
    Safely delete the given adjustment records by taking care of linked payroll records.

    :param adjustment_ids: List of adjustment IDs to be deleted.
    """
    company_details = CompanyDetails.objects(user_id=current_user.id).only('employees','adjustment_reasons','company_name','departments').first()

    if not adjustment_ids:
        return "No adjustments to delete."

    for adjustment in adjustment_ids:
        # Fetch the adjustment record
        
        if not adjustment:
            continue

        # Get the related payroll record
        employee_payroll_data = CompanyPayroll.objects(
            company_id=adjustment.company_id,
            payroll_month=adjustment.adjustment_month_on_payroll,
            payroll_year=adjustment.adjustment_year_on_payroll,
            employee_details_id=adjustment.employee_details_id
        ).first()

        if employee_payroll_data:
            # Adjust the total additions or deductions based on the adjustment type
            if adjustment.adjustment_type == 'addition':
                employee_payroll_data.total_additions -= float(adjustment.adjustment_amount)
            elif adjustment.adjustment_type == 'deduction':
                employee_payroll_data.total_deductions -= float(adjustment.adjustment_amount)

            # Recalculate the salary to be paid
            employee_payroll_data.salary_to_be_paid = (
                float(employee_payroll_data.total_salary) +
                float(employee_payroll_data.total_additions) -
                float(employee_payroll_data.total_deductions)
            )

            # Remove the adjustment from the respective list
            if adjustment.adjustment_type == 'addition':
                employee_payroll_data.update(pull__adjustment_additions=adjustment.id)
            elif adjustment.adjustment_type == 'deduction':
                employee_payroll_data.update(pull__adjustment_deductions=adjustment.id)

            # Save the updated payroll data
            employee_payroll_data.save()

        # # Delete the adjustment document if it exists
        # if adjustment.adjustment_document:
        #     filename = secure_filename(file.filename)

        #     delete_adjustment_document(filename, company_details._id)  # Assuming you have this function defined

        # Finally, delete the adjustment record
        adjustment.delete()

        # Log the deletion action
        create_activity_log("Adjustment Deleted", current_user.id, adjustment.company_id)

    return "Adjustments deleted successfully."

#Added By Ashiq Date : 19/sep/2024 Issues : Date formate start
def preprocess_data(data):
    formatted_data = {}
    for bank, records in data.items():
        formatted_records = [
            [
                 value.strftime("%d/%m/%Y") if isinstance(value, date) else value
                for value in record
            ]
            for record in records
        ]
        formatted_data[bank] = formatted_records
    return formatted_data
#end
def delete_adjustment_document(file_name, company_name):
    """
    Delete the specified adjustment document from the file system.

    :param file_name: The name of the document to delete.
    :param company_name: The name of the company to locate the document folder.
    :return: Boolean indicating success or failure of the deletion.
    """
    if not file_name:
        return False

    # Construct the file path
    file_path = os.path.join(
        app.config['UPLOAD_DOCUMENT_FOLDER'], 
        company_name.strip(), 
        'adjustments', 
        file_name
    )
    
    try:
        # Check if the file exists and delete it
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        else:
            print(f"File {file_path} does not exist.")
            return False
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False
    