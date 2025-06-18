import calendar
from flask import Blueprint, jsonify, render_template,request,flash,redirect,url_for,json,session
from flask_login import login_required,logout_user
from flask_security import roles_accepted,current_user
from project.employee.model import EmployeeBreakHistory
from ..company.model  import EmployeeDetails,EmployeeAttendance,EmployeeLeaveApplication, EmployeeLeaveApprover, EmployeeLeavePolicies,EmployeeLeaveRequest,EmployeeTimeRequest,EmployeeLeaveAdjustment,EmployeeReimbursement, EmployeeCompanyDetails
from ..models  import User,CompanyLeaveApprovers,CompanyOffices, WorkTimings,CompanyDetails,CompanyEmployeeSchedule,CompanyHolidays,CompanyOvertimePolicies,CompanyTimeApprovers,CompanyAdjustmentReasons,CompanyPayrollAdjustment,CompanyTimeOffAdjustment,SuperLeaveApprovers
from werkzeug.utils import secure_filename
import os
from flask import current_app
import uuid
from werkzeug.security import generate_password_hash,check_password_hash
from bson import json_util, ObjectId
from datetime import date, datetime, timedelta,time
import pytz
from bson.json_util import loads,dumps
from .. import create_app,create_celery_app, mail
employee = Blueprint('employee', __name__)
from flask_mail import Message
from datetime import datetime
from datetime import datetime, timedelta
import math
celery = create_celery_app()
# from geopy.distance import geodesic 

def chop_microseconds(delta):
    return delta - timedelta(microseconds=0,milliseconds=0)



@employee.route('/')
@login_required
@roles_accepted('employee')
def index():
    return render_template('employee/index.html')

@employee.route('/profile')
@login_required
@roles_accepted('employee')
def profile():
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    departments = CompanyDetails.objects(user_id=employee_details.company_id).only('company_name').first()
    return render_template('employee/profile.html',employee_details=employee_details,departments=departments)

@employee.route('/edit/profile')
@login_required
@roles_accepted('employee')
def edit_profile():
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    return render_template('employee/edit_profile.html',employee_details=employee_details)

@employee.route('/update/profile/', methods=['POST'])
def update_profile():
    if request.method == 'POST':
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        if employee_details:
            #Create Employee Login Details
            employee_data = populate_employee_details(request)
            employee_details.update(**employee_data)
            file = request.files['profile_pic']
            if file:
                profile_pic = upload_profile_pic(file)
                employee_details.update(profile_pic = profile_pic)
            flash('Profile Details Updated Successfully!', 'success')
            return redirect(url_for('employee.edit_profile'))
    else:
        return redirect(url_for('employee.profile'))
    
def populate_employee_details(request):
    employee_details = {
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
        'facebook_link' :  request.form.get('facebook_link'),
        'linkedin_link' :  request.form.get('linkedin_link'),
        'twitter_link' :  request.form.get('twitter_link'),
        'about_me' :  request.form.get('about_me'),
        }
    return employee_details

def upload_profile_pic(file):
    fname=''
    file = request.files['profile_pic']
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1]
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in current_app.config['UPLOAD_EXTENSIONS']: 
            flash('Please insert image with desired format!')
            return redirect(url_for('company.add_employee'))
        if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
            os.makedirs(current_app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], fname))
    return fname;

@employee.route('/update/password/', methods=['POST'])
def update_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        user = User.objects(email=current_user.email).first()
        check = check_password_hash(user.password, current_password)
        if not user or not check_password_hash(user.password, current_password):
            flash('Wrong Current Password, Please try again.','danger')
            return redirect(url_for('auth.edit_profile'))
        else:    
            #Create Employee Login Details
            update_status = user.update(password = generate_password_hash(new_password, method='sha256'))
            if update_status:
                flash('Password Updated Successfully!', 'success')
                return redirect(url_for('employee.edit_profile'))
    else:
        return redirect(url_for('employee.profile'))
    
@employee.route('/employee/clockin/', methods=['POST'])
def clock_in():
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        employee_details_id = request.form.get('employee_details_id')
        employee_check_in_at = datetime.now()
        attendance_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
        current_latitude = request.form.get('current_latitude')
        current_longitude = request.form.get('current_longitude')
        working_from = request.form.get('working_from')
        working_office = request.form.get('working_office')
        note = request.form.get('notes')
        
        data_available = EmployeeAttendance.objects(company_id=ObjectId(company_id),attendance_date=attendance_date,employee_details_id=ObjectId(employee_details_id)).first()
        if data_available:
            data_available.delete()
        employee_details= EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
        employee_attendance = EmployeeAttendance()    
        employee_attendance.employee_id = employee_details.employee_company_details.employee_id
        employee_attendance.employee_details_id = ObjectId(employee_details_id)
        employee_attendance.attendance_date = attendance_date
        employee_attendance.company_id = ObjectId(company_id)
        employee_attendance.employee_check_in_at = employee_check_in_at
        employee_attendance.attendance_status = "present"
        employee_attendance.clock_in_coords = [{"lat":current_latitude,"lng":current_longitude}]
        employee_attendance.working_from = ObjectId(working_from)
        employee_attendance.clock_in_note = note
        employee_attendance.working_office = ObjectId(working_office)
        employee_attendance.has_next_day_clockout = True if session["has_next_day_clockout"] else False
        
        # Calculate the late minutes if late by the employee;
        late_minutes,final_datetime = calculate_late_details(employee_check_in_at,employee_details,attendance_date)
        if final_datetime:
           employee_attendance.has_next_day_clockout = True
        employee_attendance.next_day_co_final_datetime = final_datetime

        if late_minutes > 0:
            employee_attendance.is_late = True
            employee_attendance.late_by_minutes = str(late_minutes)
        else:
            employee_attendance.is_late = False
            employee_attendance.late_by_minutes = str(late_minutes)
            
        status = employee_attendance.save()
        if late_minutes > 0:
            # Todo: Create a EmployeeTimeRequest record with the dedicated approver of the department if late exists
            if employee_details.employee_company_details.type == '0':
                time_request = create_time_request(ObjectId(company_id),employee_attendance._id,employee_details.employee_company_details.department,'late')
        
        if status:
            msg =  json.dumps({"status":"success","checked_in_time":employee_check_in_at.strftime('%d %B %Y , %H:%M:%S %p')})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))





def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth.
    :param lat1: Latitude of the first point in decimal degrees.
    :param lon1: Longitude of the first point in decimal degrees.
    :param lat2: Latitude of the second point in decimal degrees.
    :param lon2: Longitude of the second point in decimal degrees.
    :return: Distance between the two points in meters.
    """
    # Radius of the Earth in meters
    R = 6371000  

    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Difference in coordinates
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    # Haversine formula
    a = math.sin(delta_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance




@employee.route('/employee/clockout/', methods=['POST'])
def clock_out():
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        employee_details_id = request.form.get('employee_details_id')
        employee_check_out_at = datetime.now()
        attendance_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0) if not session["has_next_day_clockout"] else (datetime.today() - timedelta(days=1)).replace(minute=0, hour=0, second=0, microsecond=0)
        current_latitude = request.form.get('current_latitude')
        current_longitude = request.form.get('current_longitude')
        note = request.form.get('notes')
        
        has_overtime,ot_by_minutes,ot_policy_multiplier,ot_type,ot_policy_on = False,0,'','',''
        attendance_data = EmployeeAttendance.objects(company_id=ObjectId(company_id),attendance_date=attendance_date,employee_details_id=ObjectId(employee_details_id)).first()
        if attendance_data:
            total_hrs_worked = chop_microseconds(employee_check_out_at-attendance_data.employee_check_in_at)
            attendance_data.total_hrs_worked = str(total_hrs_worked)
            attendance_data.employee_check_out_at = employee_check_out_at
            attendance_data.clock_out_note = note
            attendance_data.clock_out_coords = [{"lat":current_latitude,"lng":current_longitude}]
            
            # Check if the user clocked out Early or Has Any Overtime
            # Todo: Check if the user left early
            # Start
            # Calculate the Early minutes if late by the employee;
            early_by_minutes = calculate_early_departure_details(employee_check_out_at,attendance_data.employee_details_id,attendance_data.attendance_date)
            
            if early_by_minutes > 0:
                attendance_data.has_left_early = True
                attendance_data.early_by_minutes = str(early_by_minutes)
            else:
                attendance_data.has_left_early = False
                attendance_data.early_by_minutes = str(early_by_minutes)
            # End
            
            # Todo: Check if the user has Any overtime
            # overtime will be calculated only for full time employees
            if attendance_data.employee_details_id.employee_company_details.type == '0':
                has_overtime,ot_by_minutes,ot_policy_multiplier,ot_type,ot_policy_on = calculate_overtime_details(employee_check_out_at,attendance_data.employee_check_in_at,attendance_data.employee_details_id,attendance_date)
                if has_overtime:
                    attendance_data.has_overtime = has_overtime
                    attendance_data.ot_by_minutes = str(ot_by_minutes)
                    attendance_data.ot_policy_multiplier = ot_policy_multiplier
                    attendance_data.ot_type = ot_type
                    attendance_data.ot_policy_on = ot_policy_on
                    attendance_data.ot_approved = False  
            status = attendance_data.save()
            
            # Todo: Create a EmployeeTimeRequest record with the dedicated approver of the department if Early exists
            if early_by_minutes > 0:
                print("Early")
                time_request = create_time_request(ObjectId(company_id),attendance_data._id,attendance_data.employee_details_id.employee_company_details.department,'early')
            
        if status:
            msg =  json.dumps({"status":"success","checked_out_time":employee_check_out_at.strftime('%d %B %Y , %H:%M:%S %p'),"checked_in_time":attendance_data.employee_check_in_at.strftime('%d %B %Y , %H:%M:%S %p'),"has_overtime":has_overtime,"ot_by_minutes":ot_by_minutes,"attendance_id":str(attendance_data._id)})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))
    
@employee.route('/employee/break/', methods=['POST'])
def employee_break():
    if request.method == 'POST':
        status = False;
        break_difference = 0
        company_id = request.form.get('company_id')
        employee_details_id = request.form.get('employee_details_id')
        attendance_date = datetime.today().replace(minute=0, hour=0, second=0,microsecond=0)
        break_id = request.form.get('break_id')
        
        break_type = request.form.get('break_type')
        break_history = EmployeeBreakHistory.objects(already_ended=False,attendance_date=attendance_date,employee_details_id=ObjectId(employee_details_id),company_id=ObjectId(company_id)).first()
        if break_type == 'start' and not break_history:
            break_history = EmployeeBreakHistory()
            break_history.start_at = datetime.now()
            break_history.company_id = ObjectId(company_id)
            break_history.employee_details_id = ObjectId(employee_details_id)
            break_history.attendance_date = attendance_date
            status = break_history.save()
            update_details = EmployeeAttendance.objects(company_id=ObjectId(company_id),attendance_date=attendance_date,employee_details_id=ObjectId(employee_details_id)).update(push__break_history=break_history.id,on_break=True)
            
        
        if break_type == 'end' and break_id: #break_type: end
            break_history = EmployeeBreakHistory.objects(_id=ObjectId(break_id)).first()
            if break_history:
                already_ended = True
                end_at = datetime.now()
                diff = end_at - break_history.start_at#in minutes
                break_difference = diff.total_seconds()/60
                status = break_history.update(already_ended = already_ended,end_at=end_at,break_difference=break_difference)
                update_details = EmployeeAttendance.objects(company_id=ObjectId(company_id),attendance_date=attendance_date,employee_details_id=ObjectId(employee_details_id)).update(on_break=False)

        if status:
            msg =  json.dumps({"status":"success","break_id":str(break_history._id),"break_minutes":break_difference})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))
    
@employee.route('/breakhistory', methods=['GET'])
def break_history():
    attendance_id = request.args.get('attendance_id')
    attendance_details = EmployeeAttendance.objects(_id=ObjectId(attendance_id)).order_by("-break_difference").first()
    if attendance_details.break_history:
        details = {}
        data = []
        attendance_details.break_history=sorted(attendance_details.break_history, key=lambda k: k.start_at,reverse=True)
        for item in attendance_details.break_history:
            details = {
                'attendance_date' : item.attendance_date.strftime('%b %d'),
                'start_at' : item.start_at.strftime('%H:%M:%S %p'),
                'end_at' : item.end_at.strftime('%H:%M:%S %p') if item.end_at else '',
                'break_difference' :  item.break_difference if item.break_difference else '',
            }
            data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg =  json.dumps({'status':'success','details':data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml

@employee.route('/clockinhistory', methods=['GET'])
def clocked_in_history():
    attendance_id = request.args.get('attendance_id')
    attendance_details = EmployeeAttendance.objects(_id=ObjectId(attendance_id)).order_by("-break_difference").first()
    if attendance_details:
        details = {}
        data = []
        for item in attendance_details.clock_in_coords:
            details = {
                'lat' : item['lat'],
                'lng':item['lng']
            }
            data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg =  json.dumps({'status':'success','details':data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml

@employee.route('/clockouthistory', methods=['GET'])
def clocked_out_history():
    attendance_id = request.args.get('attendance_id')
    attendance_details = EmployeeAttendance.objects(_id=ObjectId(attendance_id)).order_by("-break_difference").first()
    if attendance_details:
        details = {}
        data = []
        for item in attendance_details.clock_out_coords:
            details = {
                'lat' : item['lat'],
                'lng':item['lng']
            }
            data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg =  json.dumps({'status':'success','details':data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml

@employee.route('/getClockindetails', methods=['GET'])
def get_clock_in_details():
    attendance_id = request.args.get('attendance_id')
    attendance_details = EmployeeAttendance.objects(_id=ObjectId(attendance_id)).order_by("-break_difference").first()
    if attendance_details:
        details = {}
        data = []
        details = {
            'attendance_id':str(attendance_details._id),
            'employee_check_in_at' : attendance_details.employee_check_in_at.strftime('%I:%M %p'),
            'employee_check_out_at' : attendance_details.employee_check_out_at.strftime('%I:%M %p') if hasattr(attendance_details,'employee_check_out_at') else '',
            'clock_in_note': attendance_details.clock_in_note if hasattr(attendance_details,'clock_in_note') else '',
            'clock_out_note': attendance_details.clock_out_note if hasattr(attendance_details,'clock_out_note') else '',
        }
        data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg =  json.dumps({'status':'success','details':data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml

@employee.route('/leaves', methods=['GET', 'POST'])
@login_required
@roles_accepted('employee')
def leaves():
    if request.method == 'POST':
        
        attendance_range = request.form.get('daterange').split(' - ')
        start_date = datetime. strptime(attendance_range[0], '%d/%m/%Y')
        end_date = datetime. strptime(attendance_range[1], '%d/%m/%Y')
        

        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        can_apply_leave = CompanyDetails.objects(user_id=employee_details.company_id).only('disable_leave_application').first()
        leave_applications = EmployeeLeaveApplication.objects(employee_details_id=employee_details._id)
        adjustment_details = EmployeeLeaveAdjustment.objects(employee_details_id=employee_details.id, 
                                                            created_at__gte=start_date,
                                                            created_at__lte=end_date)
        working_office_id = employee_details.employee_company_details.work_timing.id
    
        week_off_day = WorkTimings.objects(_id=working_office_id).first()

        week_off_days_list = []
        if week_off_day :
            for day_list in week_off_day.week_offs:
                # Check for Sunday (0) and convert it to 6 (for your mapping)
                if day_list == 0:
                    week_off_days_list.append(1)
                # Check for Monday (1) and convert it to 0 (for your mapping)
                elif day_list == 1:
                    week_off_days_list.append(2)
                # Similarly handle other days if necessary (optional, can be expanded)
                elif day_list == 2:
                    week_off_days_list.append(3)
                elif day_list == 3:
                    week_off_days_list.append(4)
                elif day_list == 4:
                    week_off_days_list.append(5)
                elif day_list == 5:
                    week_off_days_list.append(6)
                elif day_list == 6:
                    week_off_days_list.append(0)

        print(week_off_days_list)

        return render_template('employee/leaves.html',employee_details=employee_details, 
                        adjustment_details=adjustment_details, start=start_date, end=end_date,
                        leave_applications=leave_applications,can_apply_leave=can_apply_leave,week_off_days_list=week_off_days_list,
                        isLeaveAdjustmentActive=True)


    now = datetime.today()
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Get the last day of the current month
    last_day = calendar.monthrange(now.year, now.month)[1]

    # Get the end date of the current month
    end_date = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    can_apply_leave = CompanyDetails.objects(user_id=employee_details.company_id).only('disable_leave_application').first()
    leave_applications = EmployeeLeaveApplication.objects(employee_details_id=employee_details._id)
    adjustment_details = EmployeeLeaveAdjustment.objects(employee_details_id=employee_details.id)
    #week_off_day=WorkTimings(_id=employee_details.employee_company_details.working_office)
    working_office_id = employee_details.employee_company_details.work_timing.id
    
    week_off_day = WorkTimings.objects(_id=working_office_id).first()

    week_off_days_list = []
    if week_off_day :
        for day_list in week_off_day.week_offs:
            # Check for Sunday (0) and convert it to 6 (for your mapping)
            if day_list == 0:
                week_off_days_list.append(1)
            # Check for Monday (1) and convert it to 0 (for your mapping)
            elif day_list == 1:
                week_off_days_list.append(2)
            # Similarly handle other days if necessary (optional, can be expanded)
            elif day_list == 2:
                week_off_days_list.append(3)
            elif day_list == 3:
                week_off_days_list.append(4)
            elif day_list == 4:
                week_off_days_list.append(5)
            elif day_list == 5:
                week_off_days_list.append(6)
            elif day_list == 6:
                week_off_days_list.append(0)

    print(week_off_days_list)



    return render_template('employee/leaves.html',employee_details=employee_details, 
                           adjustment_details=adjustment_details, start=start_date, end=end_date,
                           leave_applications=leave_applications,can_apply_leave=can_apply_leave,week_off_days_list=week_off_days_list)

@employee.route('/applyleave', methods=['POST'])
def apply_leave():
    if request.method == 'POST':
        # employee_details_id = request.form.get('employee_details_id')
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        
        no_of_days = request.form.get('no_of_days')
        # leave_date = request.form.get('leave_date')
        # if leave_date == 'single':
        #     leave_from = datetime. strptime(request.form.get('singledaterange'),'%d/%m/%Y')
        #     leave_till = leave_from
        # if leave_date == 'multiple':
        leave_range = request.form.get('daterange').split(' - ')
        leave_from = datetime. strptime(leave_range[0], '%d/%m/%Y')
        leave_till = datetime. strptime(leave_range[1], '%d/%m/%Y')
        employee_leave_policy = request.form.get('leave_type')
        reason = request.form.get('reason')
        emergency_contact = request.form.get('emergency_contact')
        contact_address = request.form.get('contact_address')

        leave_application = EmployeeLeaveApplication()
        leave_application.employee_details_id = employee_details._id
        leave_application.no_of_days = no_of_days
        leave_application.leave_from = leave_from
        leave_application.leave_till = leave_till
        leave_application.employee_leave_policy=ObjectId(employee_leave_policy)
        leave_application.reason = reason
        leave_application.company_id = employee_details.company_id
        leave_application.current_approval_level = "1"

        leave_application.asked_leave_from = leave_from
        leave_application.asked_leave_till = leave_till
        leave_application.asked_no_of_days = no_of_days

        leave_application.emergency_contact = emergency_contact
        leave_application.contact_address = contact_address

        # Get the company approver level and store the ref id to employee leave application
        company_leave_approver = CompanyLeaveApprovers.objects(department_name=employee_details.employee_company_details.department,company_id=employee_details.company_id).first()
        if company_leave_approver:
            leave_application.company_approver = company_leave_approver._id
            leave_application.company_approval_level = company_leave_approver.department_approval_level

        # This department follows the deafult/all department approval level
        else:
            company_leave_approver = CompanyLeaveApprovers.objects(department_name="all",company_id=employee_details.company_id).first()
            if company_leave_approver:
                leave_application.company_approver = company_leave_approver._id
                leave_application.company_approval_level = company_leave_approver.department_approval_level

        status = leave_application.save()

        # Request the approver for the approval Create a record for EmployeeLeaveRequest
        request_approver = EmployeeLeaveRequest()
        request_approver.employee_leave_app_id =  leave_application._id
        request_approver.company_id =  employee_details.company_id

        # Get Approver Details Based on Level(Current Level=1,department=current department,company ID)
        approver = EmployeeLeaveApprover.objects(employee_approval_level="1",department_name=employee_details.employee_company_details.department,company_id=employee_details.company_id).first()
        if approver:
            request_approver.approver_id = approver._id
        # else Get the all department approver level
        else:
            approver = EmployeeLeaveApprover.objects(employee_approval_level="1",department_name="all",company_id=employee_details.company_id).first()
            if approver:
                request_approver.approver_id = approver._id

        request_approver.save()
        leave_application.update(current_aprrover=request_approver._id,add_to_set__approver_list=request_approver._id)
        # Send email to Level 1 application approver
        # send_leave_approval_email.delay(str(leave_application._id))
        # send_leave_approval_email(str(leave_application._id))

        try:
            send_leave_notification_email(str(leave_application._id))
        except Exception as e:
            print(e)

        if status:
            msg =  json.dumps({"status":"success"})
            print('sucessfully sent')
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml



@employee.route('/get-employee-leave-details', methods=['GET'])
@login_required
@roles_accepted('employee')
def get_employee_leave_details():

    employee_id = request.args.get('employee_id')

    
    employee_data=EmployeeDetails.objects(_id=employee_id).first()
    working_office_id = employee_data.employee_company_details.work_timing.id
    week_off_day = WorkTimings.objects(_id=working_office_id).first()

    week_off_days_list = []
    if week_off_day :
        for day_list in week_off_day.week_offs:
            # Check for Sunday (0) and convert it to 6 (for your mapping)
            if day_list == 0:
                week_off_days_list.append(1)
            # Check for Monday (1) and convert it to 0 (for your mapping)
            elif day_list == 1:
                week_off_days_list.append(2)
            # Similarly handle other days if necessary (optional, can be expanded)
            elif day_list == 2:
                week_off_days_list.append(3)
            elif day_list == 3:
                week_off_days_list.append(4)
            elif day_list == 4:
                week_off_days_list.append(5)
            elif day_list == 5:
                week_off_days_list.append(6)
            elif day_list == 6:
                week_off_days_list.append(0)
    # Dummy data (Replace with database query)
    employee_data = {
        "success": True,
        "data": {
            "week_off_days_list":week_off_days_list
        }
    }
    return jsonify(employee_data)


@employee.route('/leavesapprovals')
@login_required
@roles_accepted('employee')
def leaves_approvals():
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()

    if not employee_details:
        company_details = CompanyDetails.objects(user_id=current_user.id).first()
        if company_details:
            employee_details = company_details
            employee_details.is_super_leave_approver = True
            employee_details.company_id = company_details.user_id
            employee_details.is_approver = True
        else:
            flash("User profile not found.", 'danger')
            return redirect(url_for('employee.dashboard'))

    # Initialize lists
    super_leave_list, super_department_list, leave_list, all_leave_list = [], [], [], []
    department_list, leave_requests, super_approver_list, super_approver_details = [], [], [], []

    current_year = datetime.now().year
    year_start_date = datetime(current_year, 1, 1)
    year_end_date = datetime(current_year, 12, 31)

    if getattr(employee_details, 'is_super_leave_approver', False):
        (super_leave_list, super_department_list, all_leave_list,
         super_approver_list, super_approver_details) = process_super_approver(
            employee_details, current_year, year_start_date, year_end_date
        )

    if getattr(employee_details, 'is_approver', False):
        leave_list, department_list, leave_requests = process_regular_approver(employee_details, current_year)

    leave_applications = EmployeeLeaveApplication.objects(company_id=employee_details.company_id)
    if getattr(employee_details, 'is_super_leave_approver', False) or getattr(employee_details, 'is_approver', False):
        return render_template('employee/leaves_approval.html',
                               leave_requests=leave_requests,
                               leave_list=leave_list,
                               department_list=department_list,
                               all_leave_list=all_leave_list,
                               super_leave_list=super_leave_list,
                               super_department_list=super_department_list,
                               super_approver_list=super_approver_list,
                               super_approver_details=super_approver_details,
                               leave_applications=leave_applications)
    else:
        flash("Sorry, you do not have permission to view/(perform action on) this resource.", 'danger')
        return redirect(url_for('employee.dashboard'))


def process_super_approver(employee_details, current_year, year_start_date, year_end_date):
    super_leave_list, super_department_list, all_leave_list = [], [], []
    super_approver_list, super_approver_details = [], []

    try:
        super_approvers = SuperLeaveApprovers.objects(company_id=employee_details.company_id)
        super_approver_ids = [sa.employee_details_id.id for sa in super_approvers if hasattr(sa, 'employee_details_id') and sa.employee_details_id]

        approvers_de = EmployeeLeaveApprover.objects(employee_details_id__in=super_approver_ids).only('_id')
        approver_ids = [item._id for item in approvers_de]

        all_leave_list_cal = EmployeeLeaveApplication.objects(
            company_id=employee_details.company_id,
            asked_leave_from__gte=year_start_date,
            asked_leave_from__lte=year_end_date
        )

        all_leave_requests = EmployeeLeaveRequest.objects(
            company_id=employee_details.company_id,
            request_status="pending"
        )

        leave_requests_super_approved = EmployeeLeaveRequest.objects(
            company_id=employee_details.company_id,
            request_status="approved"
        )

        super_approver_list = [
            request for request in leave_requests_super_approved
            if request.employee_leave_app_id and hasattr(request.employee_leave_app_id, 'asked_leave_from')
        ]

        for subitem in super_approver_list:
            app = subitem.employee_leave_app_id
            if not app or not hasattr(app, 'asked_leave_from'):
                continue

            emp = app.employee_details_id
            if not emp or not hasattr(emp, 'employee_company_details'):
                continue

            dept = emp.employee_company_details.department

            leave_data = {
                'id': str(app._id),
                'title': f"{emp.first_name} {emp.last_name}",
                'userId': dept,
            }

            if subitem.request_status.lower() == "approved":
                leave_data.update({
                    'start': app.leave_from.strftime("%Y-%m-%d"),
                    'end': (app.leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                    'color': 'rgb(13, 205, 148)',
                })
            super_approver_details.append(leave_data)

            if dept not in super_department_list:
                super_department_list.append(dept)

        all_leave_list = [
            request for request in all_leave_requests
            if request.employee_leave_app_id and
               hasattr(request.employee_leave_app_id, 'asked_leave_from') and
               request.employee_leave_app_id.asked_leave_from.year == current_year
        ]

        for subitem in all_leave_list_cal:
            try:
                emp = subitem.employee_details_id
                if not emp or not hasattr(emp, 'employee_company_details'):
                    continue

                dept = emp.employee_company_details.department
                leave_data = {
                    'id': str(subitem._id),
                    'title': f"{emp.first_name} {emp.last_name}",
                    'userId': dept,
                }

                if subitem.leave_status.lower() == "pending":
                    leave_data.update({
                        'start': subitem.asked_leave_from.strftime("%Y-%m-%d"),
                        'end': (subitem.asked_leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                        'color': '#e3b113',
                    })
                elif subitem.leave_status.lower() == "approved":
                    leave_data.update({
                        'start': subitem.leave_from.strftime("%Y-%m-%d"),
                        'end': (subitem.leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                        'color': 'rgb(13, 205, 148)',
                    })
                super_leave_list.append(leave_data)

                if dept not in super_department_list:
                    super_department_list.append(dept)
            except (AttributeError, TypeError):
                continue

    except Exception as e:
        print(f"Error in process_super_approver: {str(e)}")

    return super_leave_list, super_department_list, all_leave_list, super_approver_list, super_approver_details


def process_regular_approver(employee_details, current_year):
    leave_list, department_list, leave_requests = [], [], []

    try:
        approvers = EmployeeLeaveApprover.objects(employee_details_id=employee_details._id).only('_id')
        if approvers:
            approver_ids = [item._id for item in approvers]

            leave_requests_pending = EmployeeLeaveRequest.objects(
                approver_id__in=approver_ids,
                request_status="pending"
            )

            leave_requests_approved = EmployeeLeaveRequest.objects(
                approver_id__in=approver_ids,
                request_status="approved"
            )

            filtered_pending = [
                req for req in leave_requests_pending
                if req.employee_leave_app_id and
                   hasattr(req.employee_leave_app_id, 'asked_leave_from') and
                   req.employee_leave_app_id.asked_leave_from.year == current_year
            ]

            leave_requests = filtered_pending + list(leave_requests_approved)

            for subitem in leave_requests:
                try:
                    emp_app = subitem.employee_leave_app_id
                    emp_detail = emp_app.employee_details_id
                    dept = emp_detail.employee_company_details.department

                    leave_data = {
                        'id': str(subitem._id),
                        'title': f"{emp_detail.first_name} {emp_detail.last_name}",
                        'userId': dept
                    }

                    if subitem.request_status.lower() == "pending":
                        leave_data.update({
                            'start': emp_app.asked_leave_from.strftime("%Y-%m-%d"),
                            'end': (emp_app.asked_leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                            'color': '#e3b113'
                        })
                    elif subitem.request_status.lower() == "approved":
                        leave_data.update({
                            'start': emp_app.leave_from.strftime("%Y-%m-%d"),
                            'end': (emp_app.leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                            'color': 'rgb(13, 205, 148)'
                        })

                    leave_list.append(leave_data)
                    if dept not in department_list:
                        department_list.append(dept)
                except (AttributeError, TypeError):
                    continue

    except Exception as e:
        print(f"Error in process_regular_approver: {str(e)}")

    return leave_list, department_list, leave_requests

# @employee.route('/leavesapprovals')
# @login_required
# @roles_accepted('employee')
# def leaves_approvals():
#     # employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
#     # Get all the aprrovers id 
#     employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
#     if not employee_details:
#         employee_details = CompanyDetails.objects(user_id=current_user.id).first()
#         employee_details.is_super_leave_approver = True
#         employee_details.company_id = employee_details.user_id
#         employee_details.is_approver = True
#     super_leave_list = []
#     super_department_list = []
#     leave_list = []
#     all_leave_list = []
#     department_list = []
#     leave_requests = []    

#     if employee_details.is_super_leave_approver:
#         all_leave_list_cal = EmployeeLeaveApplication.objects(company_id=employee_details.company_id)
#         all_leave_list = EmployeeLeaveRequest.objects(company_id=employee_details.company_id)

#         for subitem in all_leave_list_cal:

#             if subitem.leave_status == "pending":
#                 super_leave_list.append(
#                     {'id':str(subitem._id),
#                      'title': subitem.employee_details_id.first_name +' '+ subitem.employee_details_id.last_name,
#                      'start':subitem.asked_leave_from.strftime("%Y-%m-%d"),
#                      'end':(subitem.asked_leave_till+timedelta(days=1)).strftime("%Y-%m-%d"),
#                     #  'display': 'block',
#                      'color':'#e3b113',
#                      'userId':subitem.employee_details_id.employee_company_details.department,

#                     })
                
#                 super_department_list.append(subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list

#             elif subitem.leave_status == "approved":
#                 super_leave_list.append(
#                     {'id':str(subitem._id),
#                     'title': subitem.employee_details_id.first_name +' '+ subitem.employee_details_id.last_name,
#                     'start':subitem.leave_from.strftime("%Y-%m-%d"),
#                     'color':'rgb(13, 205, 148)',
#                     'userId':subitem.employee_details_id.employee_company_details.department,

#                     })  
#                 super_department_list.append(subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list
 
#     approvers = EmployeeLeaveApprover.objects(employee_details_id=employee_details._id).only('_id')
#     if approvers:
#     # Look for application request based on approver ids with pending status
#         data = []
#         for item in approvers:
#             data.append(item._id)
#         leave_requests = EmployeeLeaveRequest.objects(approver_id__in=data)
            
#         for subitem in leave_requests:
            
#             if subitem.request_status == "pending":
#                 leave_list.append(
#                     {'id':str(subitem._id),
#                     'title': subitem.employee_leave_app_id.employee_details_id.first_name +' '+ subitem.employee_leave_app_id.employee_details_id.last_name,
#                     'start':subitem.employee_leave_app_id.asked_leave_from.strftime("%Y-%m-%d"),
#                     'end':(subitem.employee_leave_app_id.asked_leave_till+timedelta(days=1)).strftime("%Y-%m-%d"),
#                     #  'display': 'block',
#                     'color':'#e3b113',
#                     'userId':subitem.employee_leave_app_id.employee_details_id.employee_company_details.department,
                   
#                     })
                
#                 department_list.append(subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list

#             elif subitem.request_status == "approved":
#                 leave_list.append(
#                     {'id':str(subitem._id),
#                     'title': subitem.employee_leave_app_id.employee_details_id.first_name +' '+ subitem.employee_leave_app_id.employee_details_id.last_name,
#                     'start':subitem.employee_leave_app_id.leave_from.strftime("%Y-%m-%d"),
#                     'end':(subitem.employee_leave_app_id.leave_till+timedelta(days=1)).strftime("%Y-%m-%d"),
#                     # 'display': 'block',
#                     # 'color':'rgba(255, 173, 0, 1)'
#                     # 'eventColor': 'rgb(13, 205, 148)',
#                     'color':'rgb(13, 205, 148)',
#                     'userId':subitem.employee_leave_app_id.employee_details_id.employee_company_details.department,

                   
#                     })   
#                 department_list.append(subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list
#     if employee_details.is_super_leave_approver or employee_details.is_approver:
#         return render_template('employee/leaves_approval.html',leave_requests=leave_requests,
#                                leave_list=leave_list,department_list=department_list,all_leave_list=all_leave_list,
#                                super_leave_list=super_leave_list,super_department_list=super_department_list)
#     else:
#         flash("Sorry, You do not have permission to view/(perform action on) this resource.",'danger')
#         # return render_template('employee/leaves_approval.html',leave_requests=leave_requests,leave_list=leave_list,department_list=department_list,all_leave_list=all_leave_list,super_leave_list=super_leave_list,super_department_list=super_department_list)
    
@employee.route('/leavescalender')
@login_required
@roles_accepted('company')
def leaves_calender():
    # employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    # Get all the aprrovers id 
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    if not employee_details:
        employee_details = CompanyDetails.objects(user_id=current_user.id).first()
        employee_details.is_super_leave_approver = True
        employee_details.company_id = employee_details.user_id
        employee_details.is_approver = True
    super_leave_list = []
    super_department_list = []
    leave_list = []
    all_leave_list = []
    department_list = []
    leave_requests = []    
    if employee_details.is_super_leave_approver:
        all_leave_list_cal = EmployeeLeaveApplication.objects(company_id=employee_details.company_id)
        all_leave_list = EmployeeLeaveRequest.objects(company_id=employee_details.company_id)
        for subitem in all_leave_list_cal:
            if subitem.leave_status == "pending":
                super_leave_list.append(
                    {'id':str(subitem._id),
                     'title': subitem.employee_details_id.first_name +' '+ subitem.employee_details_id.last_name,
                     'start':subitem.asked_leave_from.strftime("%Y-%m-%d"),
                     'end':(subitem.asked_leave_till+timedelta(days=1)).strftime("%Y-%m-%d"),
                    #  'display': 'block',
                     'color':'#e3b113',
                     'userId':subitem.employee_details_id.employee_company_details.department
                    })               
                super_department_list.append(subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list

            elif subitem.leave_status == "approved":
                super_leave_list.append(
                    {'id':str(subitem._id),
                    'title': subitem.employee_details_id.first_name +' '+ subitem.employee_details_id.last_name,
                    'start':subitem.leave_from.strftime("%Y-%m-%d"),
                    'color':'rgb(13, 205, 148)',
                    'userId':subitem.employee_details_id.employee_company_details.department
                    })  
                super_department_list.append(subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list
 
    approvers = EmployeeLeaveApprover.objects(employee_details_id=employee_details._id).only('_id')
    # Look for application request based on approver ids with pending status
    data = []
    for item in approvers:
        data.append(item._id)
    leave_requests = EmployeeLeaveRequest.objects(company_id=employee_details.company_id)        
    for subitem in leave_requests:
        if subitem.request_status == "pending":
            leave_list.append(
                {'id':str(subitem._id),
                'title': subitem.employee_leave_app_id.employee_details_id.first_name +' '+ subitem.employee_leave_app_id.employee_details_id.last_name,
                'start':subitem.employee_leave_app_id.asked_leave_from.strftime("%Y-%m-%d"),
                'end':(subitem.employee_leave_app_id.asked_leave_till+timedelta(days=1)).strftime("%Y-%m-%d"),
                #  'display': 'block',
                'color':'#e3b113',
                'userId':subitem.employee_leave_app_id.employee_details_id.employee_company_details.department
                })
            
            department_list.append(subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list

        elif subitem.request_status == "approved":
            leave_list.append(
                {'id':str(subitem._id),
                'title': subitem.employee_leave_app_id.employee_details_id.first_name +' '+ subitem.employee_leave_app_id.employee_details_id.last_name,
                'start':subitem.employee_leave_app_id.leave_from.strftime("%Y-%m-%d"),
                'end':(subitem.employee_leave_app_id.leave_till+timedelta(days=1)).strftime("%Y-%m-%d"),
                # 'display': 'block',
                # 'color':'rgba(255, 173, 0, 1)'
                # 'eventColor': 'rgb(13, 205, 148)',
                'color':'rgb(13, 205, 148)',
                'userId':subitem.employee_leave_app_id.employee_details_id.employee_company_details.department
                })   
            department_list.append(subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list
    if employee_details.is_super_leave_approver or employee_details.is_approver:
        return render_template('company/employee/leave_calendar.html',leave_requests=leave_requests,
                               leave_list=leave_list,department_list=department_list,all_leave_list=all_leave_list,
                               super_leave_list=super_leave_list,super_department_list=super_department_list)


@employee.route('/approveleaverequest', methods=['POST'])
def approve_leave_request():
    leave_request_id = request.form.get('leave_request_id')
    comment = request.form.get('approver_comment')
    
    if not leave_request_id:
        return json.dumps({"status": "success"})
        
    # Get leave request details
    leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
    if not leave_request_details:
        return json.dumps({"status": "success"})
        
    # Get leave application details
    leave_application_details = EmployeeLeaveApplication.objects(_id=leave_request_details.employee_leave_app_id._id).first()
    
    # Add comment if provided
    if comment:
        leave_request_details.update(comment=comment)
        leave_application_details.update(push__approver_comments=leave_request_details._id)
    
    # Handle date edits if applicable
    has_edited = request.form.get('edit_leave_date')
    start_date = leave_application_details.leave_from
    end_date = leave_application_details.leave_till
    no_of_days = leave_application_details.no_of_days
    
    if has_edited:
        try:
            new_leave_range = request.form.get('daterange').split(' - ')
            start_date = datetime.strptime(new_leave_range[0], '%d/%m/%Y')
            end_date = datetime.strptime(new_leave_range[1], '%d/%m/%Y')
            
            # Calculate working days excluding Sundays
            working_days = count_working_days(start_date, end_date)
            no_of_days = str(working_days)
            
            print(f"Edited leave period: {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
            print(f"Working days (excluding Sundays): {working_days}")
            
            # Update leave application with new dates
            update_result = leave_application_details.update(
                leave_from=start_date,
                leave_till=end_date,
                no_of_days=no_of_days,
                asked_leave_from=start_date,  # Also update the asked dates
                asked_leave_till=end_date
            )
            
            leave_application_details.reload()
            
            # Special logging for cross-year leave requests
            if end_date.year > start_date.year:
                print(f"Processing cross-year leave request from {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
                
                # Calculate days in each year
                days_in_current_year = count_working_days(start_date, datetime(start_date.year, 12, 31))
                days_in_next_year = count_working_days(datetime(end_date.year, 1, 1), end_date)
                
                print(f"Working days in {start_date.year}: {days_in_current_year}")
                print(f"Working days in {end_date.year}: {days_in_next_year}")
                print(f"Total working days: {working_days}")
        except Exception as e:
            print(f"Error updating leave dates: {e}")
    
    # Process approval logic
    current_approval_level = leave_application_details.current_approval_level
    company_approval_level = leave_application_details.company_approval_level
    
    # Check if this is the final approver
    if current_approval_level == company_approval_level:
        return handle_final_approval(leave_request_details, leave_application_details, comment, has_edited, start_date, end_date, no_of_days)
    else:
        return forward_to_next_approver(leave_request_details, leave_application_details, current_approval_level)


def handle_final_approval(leave_request_details, leave_application_details, comment, has_edited, start_date, end_date, no_of_days):
    """Handle the final approval process for leave requests"""
    # Check if leave spans to next year
    check_cross_year_leave(leave_application_details)
    
    # Special handling for Dec 21, 2024 to Jan 21, 2025 period
    if (start_date.year == 2024 and start_date.month == 12 and start_date.day == 21 and
        end_date.year == 2025 and end_date.month == 1 and end_date.day == 21):
        # Adjust start date to January 1, 2025
        print(f"Special case: Adjusting leave period from {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')} to 01/01/2025 - {end_date.strftime('%d/%m/%Y')}")
        start_date = datetime(2025, 1, 1)
        
        # Recalculate working days with new start date
        working_days = count_working_days(start_date, end_date)
        print(f"Adjusted working days: {working_days} (excluding Sundays)")
        
        # Update leave application with new start date
        leave_application_details.update(
            leave_from=start_date,
            no_of_days=str(working_days)
        )
        leave_application_details.reload()
    else:
        # Recalculate leave days excluding Sundays
        working_days = count_working_days(start_date, end_date)
    
    # If we have edited dates, update the no_of_days to reflect working days
    if has_edited:
        leave_application_details.update(no_of_days=str(working_days))
        leave_application_details.reload()
        print(f"Updated leave days to {working_days} (excluding Sundays)")
    
    # Special handling for cross-year leave requests
    is_cross_year = end_date.year > start_date.year
    if is_cross_year:
        print(f"Processing cross-year leave from {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
    
    # Check leave balance
    current_leave_balance = leave_application_details.employee_leave_policy.balance
    asking_leave_days = working_days  # Use the calculated working days
    
    # Get the leave policy details
    leave_policy_details = EmployeeLeavePolicies.objects(_id=leave_application_details.employee_leave_policy._id).first()
    
    # Determine if employee has sufficient balance
    if current_leave_balance >= asking_leave_days:
        # Sufficient balance - standard approval
        return approve_with_sufficient_balance(
            leave_request_details, leave_application_details, leave_policy_details,
            comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days
        )
    else:
        # Insufficient balance - special handling needed
        return approve_with_insufficient_balance(
            leave_request_details, leave_application_details, leave_policy_details,
            comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days
        )

def count_working_days(start_date, end_date):
    """Count the number of working days (excluding Sundays) between two dates"""
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Skip Sundays (weekday 6)
        if current_date.weekday() != 6:
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days


def check_cross_year_leave(leave_application_details):
    """Check if the leave request spans across different years"""
    asked_leave_from = leave_application_details.asked_leave_from
    asked_leave_till = leave_application_details.asked_leave_till
    
    if asked_leave_till.year > asked_leave_from.year:
        print("The 'asked_leave_till' date is in the next year.")
        print(f"Leave spans from {asked_leave_from.strftime('%d/%m/%Y')} to {asked_leave_till.strftime('%d/%m/%Y')}")
        
        # Calculate working days (excluding Sundays)
        total_working_days = count_working_days(asked_leave_from, asked_leave_till)
        days_current_year = count_working_days(asked_leave_from, datetime(asked_leave_from.year, 12, 31))
        days_next_year = count_working_days(datetime(asked_leave_till.year, 1, 1), asked_leave_till)
        
        print(f"Total working days (excluding Sundays): {total_working_days}")
        print(f"Working days in current year: {days_current_year}")
        print(f"Working days in next year: {days_next_year}")
    else:
        print("The 'asked_leave_till' date is not in the next year.")


def approve_with_sufficient_balance(leave_request_details, leave_application_details, leave_policy_details, 
                                    comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days):
    """Process approval when employee has sufficient leave balance"""
    # Update request status
    leave_request_details.update(
        request_status="approved", 
        approved_on=datetime.now(), 
        comment=comment
    )
    
    # Calculate new balance
    new_balance = current_leave_balance - asking_leave_days
    
    # Update leave policy balance
    if leave_policy_details:
        leave_policy_details.update(balance=new_balance)
    
    # Update leave application status
    leave_application_details.update(
        current_approval_level="", 
        leave_status="approved", 
        balance_before_approval=current_leave_balance, 
        balance_after_approval=new_balance, 
        approved_on=datetime.now()
    )
    
    # Create leave adjustment record
    adj_days = str(asking_leave_days if not has_edited else float(leave_application_details.no_of_days))
    after_adj = str(current_leave_balance - float(adj_days))
    
    new_data = create_leave_adjustment(
        leave_policy_details.company_id,
        leave_policy_details.employee_details_id,
        leave_application_details.employee_leave_policy._id,
        'decrement',
        adj_days,
        str(comment),
        str(current_leave_balance),
        after_adj
    )
    
    leave_application_details.update(leave_adjustment=new_data._id)
    leave_application_details.save()
    
    # Process schedule and attendance updates
    process_schedule_and_attendance(leave_application_details, start_date, end_date, has_edited, comment)
    
    return json.dumps({"status": "success"})


def approve_with_insufficient_balance(leave_request_details, leave_application_details, leave_policy_details, 
                                     comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days):
    """Process approval when employee has insufficient leave balance"""
    try:
        # Calculate difference between requested leave days and current balance
        difference = asking_leave_days - current_leave_balance
        
        # Approve the leave request
        leave_request_details.update(
            request_status="approved",
            approved_on=datetime.now(),
            comment=comment
        )
        
        # Set balance to 0 after deduction
        if leave_policy_details:
            leave_policy_details.update(balance=0)
        
        # Extract IDs safely
        employee_id = leave_application_details.employee_details_id._id
        company_id = leave_application_details.company_id.id
        
        # Ensure ObjectId type for IDs
        company_id = ObjectId(company_id) if not isinstance(company_id, ObjectId) else company_id
        employee_id = ObjectId(employee_id) if not isinstance(employee_id, ObjectId) else employee_id
        
        # Find unpaid leave policy
        unpaid_policy_id, policy_balance = find_unpaid_leave_policy(company_id, employee_id)
        
        # Update leave application details
        leave_application_details.update(
            current_approval_level="",
            leave_status="approved",
            balance_before_approval=current_leave_balance,
            balance_after_approval=0,
            approved_on=datetime.now()
        )
        
        # Process leave adjustments
        process_leave_adjustments(
            leave_application_details, leave_policy_details, company_id,
            current_leave_balance, difference, unpaid_policy_id, policy_balance,
            comment
        )
        
        # Process schedule and attendance updates
        process_schedule_and_attendance(leave_application_details, start_date, end_date, has_edited, comment)
        
        return json.dumps({"status": "success"})
        
    except Exception as e:
        print(f"Error in approve_with_insufficient_balance: {e}")
        return json.dumps({"status": "error", "message": str(e)})


def find_unpaid_leave_policy(company_id, employee_id):
    """Find the unpaid leave policy for the employee"""
    # Query for leave policies
    leave_policies = EmployeeLeavePolicies.objects(
        company_id=company_id,
        employee_details_id=employee_id
    )
    
    # Find the policy ID for "Unpaid Leaves"
    emp_leave_policy_id = None
    policy_balance = 0
    
    if leave_policies:
        for policy in leave_policies:
            # Store policy details for debugging
            policy_info = {
                "policy_id": str(policy._id),
                "policy_name": policy.leave_policy_id.leave_policy_name,
                "balance": policy.balance,
                "leave_policy_id": policy.leave_policy_id, 
                "allowance_day": getattr(policy, "allowance_day", 24),
            }
            
            # Check if this is the "Unpaid Leaves" policy
            if policy.leave_policy_id.leave_policy_name == "Unpaid Leaves":
                emp_leave_policy_id = str(policy._id)
                policy_balance = policy.balance
    
    return emp_leave_policy_id, policy_balance


def process_leave_adjustments(leave_application_details, leave_policy_details, company_id,
                             current_leave_balance, difference, unpaid_policy_id, policy_balance, comment):
    """Process leave adjustments for the approved leave"""
    asked_leave_from = leave_application_details.asked_leave_from
    asked_leave_till = leave_application_details.asked_leave_till
    
    # Handle cross-year leave requests
    if asked_leave_till.year > asked_leave_from.year:
        process_cross_year_adjustments(
            leave_application_details, leave_policy_details, company_id,
            current_leave_balance, asked_leave_from, asked_leave_till, comment
        )
    else:
        # Standard leave adjustments
        process_standard_adjustments(
            leave_application_details, leave_policy_details, company_id,
            current_leave_balance, difference, unpaid_policy_id, policy_balance, comment
        )


def process_cross_year_adjustments(leave_application_details, leave_policy_details, company_id,
                                  current_leave_balance, asked_leave_from, asked_leave_till, comment):
    """Process adjustments for leave requests that span across years"""
    # Special handling for Dec 21, 2024 to Jan 21, 2025 period
    if (asked_leave_from.year == 2024 and asked_leave_from.month == 12 and asked_leave_from.day == 21 and
        asked_leave_till.year == 2025 and asked_leave_till.month == 1 and asked_leave_till.day == 21):
        # For this specific period, only process days in 2025
        first_day_next_year = datetime(2025, 1, 1)
        
        # Count working days in 2025 only (excluding Sundays)
        days_in_next_year = count_working_days(first_day_next_year, asked_leave_till)
        
        print(f"Special case: Only considering days from 01/01/2025 to 21/01/2025")
        print(f"Working days to be deducted: {days_in_next_year}")
        
        # Get leave allowance for next year
        leave_allow = get_leave_allowance(leave_application_details)
        
        # Calculate new balance after deduction for next year
        leave_allow_balance = leave_allow - days_in_next_year
        
        # Create adjustment for 2025 only
        created_at = first_day_next_year.strftime("%d %B %Y %H:%M:%S")
        
        new_data = create_leave_adjustment(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            "decrement",
            str(days_in_next_year),
            f"Leave from {first_day_next_year.strftime('%d/%m/%Y')} to {asked_leave_till.strftime('%d/%m/%Y')} (excluding Sundays)",
            str(leave_allow),
            str(leave_allow_balance),
            created_at
        )
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(leave_application_details.employee_leave_policy._id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=leave_allow_balance
        )
        
        return
    
    # Regular processing for other cross-year leaves
    # Calculate days in current year and next year (excluding Sundays)
    first_day_next_year = datetime(asked_leave_till.year, 1, 1)
    
    # Count working days in current year (excluding Sundays)
    days_in_current_year = count_working_days(asked_leave_from, datetime(asked_leave_from.year, 12, 31))
    
    # Count working days in next year (excluding Sundays)
    days_in_next_year = count_working_days(first_day_next_year, asked_leave_till)
    
    print(f"Working days in current year: {days_in_current_year}")
    print(f"Working days in next year: {days_in_next_year}")
    
    if current_leave_balance != 0:
        # Determine how many days to deduct from current year's balance
        days_to_deduct_current_year = min(days_in_current_year, current_leave_balance)
        
        # First adjustment (deduct from current year balance)
        new_data = create_leave_adjustment(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            'decrement',
            str(days_to_deduct_current_year),
            f"Leave from {asked_leave_from.strftime('%d/%m/%Y')} to {datetime(asked_leave_from.year, 12, 31).strftime('%d/%m/%Y')} (excluding Sundays)",
            str(current_leave_balance),
            str(current_leave_balance - days_to_deduct_current_year)
        )
        
        remaining_balance = current_leave_balance - days_to_deduct_current_year
        
        leave_application_details.update(leave_adjustment=new_data._id)
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(leave_application_details.employee_leave_policy._id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=remaining_balance
        )
        
        # Get leave allowance for next year
        leave_allow = get_leave_allowance(leave_application_details)
        
        # Calculate new balance after deduction for next year
        leave_allow_balance = leave_allow - days_in_next_year
        
        # Create adjustment for next year
        created_at = first_day_next_year.strftime("%d %B %Y %H:%M:%S")
        
        new_data = create_leave_adjustment(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            "decrement",
            str(days_in_next_year),
            f"Leave from {first_day_next_year.strftime('%d/%m/%Y')} to {asked_leave_till.strftime('%d/%m/%Y')} (excluding Sundays)",
            str(leave_allow),
            str(leave_allow_balance),
            created_at
        )
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(leave_application_details.employee_leave_policy._id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=leave_allow_balance
        )


def process_standard_adjustments(leave_application_details, leave_policy_details, company_id,
                               current_leave_balance, difference, unpaid_policy_id, policy_balance, comment):
    """Process adjustments for standard leave requests"""
    if current_leave_balance != 0:
        # First adjustment (deduct full current balance)
        new_data = create_leave_adjustment(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            'decrement',
            str(current_leave_balance),
            str(comment),
            str(current_leave_balance),
            "0"
        )
        
        leave_application_details.update(leave_adjustment=new_data._id)
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(leave_application_details.employee_leave_policy._id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=0
        )
    
    # If unpaid leave policy exists, update it
    if unpaid_policy_id:
        new_policy_balance = policy_balance - difference
        
        new_data = create_leave_adjustment(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            ObjectId(unpaid_policy_id),
            'decrement',
            str(difference),
            str(comment),
            str(policy_balance),
            str(-new_policy_balance)
        )
        
        leave_application_details.update(leave_adjustment=new_data._id)
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(unpaid_policy_id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=float(new_policy_balance)
        )


def get_leave_allowance(leave_application_details):
    """Get the leave allowance for a policy"""
    # Default allowance
    leave_allow = 24
    
    # Query for leave policies
    leave_policies = EmployeeLeavePolicies.objects(
        company_id=leave_application_details.company_id.id,
        employee_details_id=leave_application_details.employee_details_id._id
    )
    
    # Find the current policy allowance
    if leave_policies:
        for policy in leave_policies:
            if str(policy._id) == str(leave_application_details.employee_leave_policy._id):
                leave_allow = getattr(policy, "allowance_day", 24)
                break
    
    return leave_allow


def create_leave_adjustment(company_id, employee_details_id, employee_leave_pol_id, 
                           adjustment_type, adjustment_days, adjustment_comment,
                           before_adjustment, after_adjustment, created_at=None):
    """Create a leave adjustment record"""
    new_data = EmployeeLeaveAdjustment(
        company_id=company_id,
        employee_details_id=employee_details_id,
        employee_leave_pol_id=employee_leave_pol_id,
        adjustment_type=adjustment_type,
        adjustment_days=adjustment_days,
        adjustment_comment=adjustment_comment,
        before_adjustment=before_adjustment,
        after_adjustment=after_adjustment
    )
    
    if created_at:
        new_data.created_at = created_at
    
    new_data.save()
    return new_data


def process_schedule_and_attendance(leave_application_details, start_date, end_date, has_edited, comment):
    """Process schedule and attendance updates for approved leave"""
    # Special handling for Dec 21, 2024 to Jan 21, 2025 period
    original_start_date = start_date
    if (start_date.year == 2024 and start_date.month == 12 and start_date.day == 21 and
        end_date.year == 2025 and end_date.month == 1 and end_date.day == 21):
        print(f"Special case for schedule processing: Using only Jan 1, 2025 to Jan 21, 2025")
        start_date = datetime(2025, 1, 1)
    
    # Ensure we have day off work timings
    work_timings = get_or_create_day_off_work_timings(leave_application_details.company_id.id)
    
    # Send approval email
    send_leave_approval_email(leave_application_details, original_start_date, end_date, has_edited, comment)
    
    # Count working days for reporting
    working_days = count_working_days(start_date, end_date)
    print(f"Processing {working_days} working days of leave (excluding Sundays)")
    
    # Process each day in the leave period
    current_date = start_date
    while current_date <= end_date:
        # Skip Sundays
        if current_date.weekday() == 6:  # Sunday
            print(f"Skipping Sunday: {current_date.strftime('%d/%m/%Y')}")
            current_date = current_date + timedelta(days=1)
            continue
            
        # Create schedule entry
        create_schedule_entry(leave_application_details, work_timings, current_date)
        
        # Create attendance entry
        create_attendance_entry(leave_application_details, current_date)
        
        # Handle unpaid leave adjustments
        if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
            create_unpaid_leave_adjustment(leave_application_details, current_date)
        
        current_date = current_date + timedelta(days=1)

def get_or_create_day_off_work_timings(company_id):
    """Get or create day off work timings"""
    work_timings = WorkTimings.objects(is_day_off=True, company_id=company_id).first()
    
    if not work_timings:
        work_timings = WorkTimings(
            name="Day Off",
            schedule_color='#808080',
            is_day_off=True,
            office_start_at='',
            office_end_at='',
            late_arrival__later_than='',
            early_departure_earliar_than='',
            consider_absent_after='',
            week_offs='',
            company_id=company_id
        )
        work_timings.save()
        
        CompanyDetails.objects(user_id=company_id).update(push__worktimings=work_timings._id)
    
    return work_timings


def send_leave_approval_email(leave_application_details, start_date, end_date, has_edited, comment):
    """Send leave approval email to employee"""
    try:
        # Get policy details
        leave_policy_details = EmployeeLeavePolicies.objects(
            _id=leave_application_details.employee_leave_policy._id
        ).first()
        
        if not leave_policy_details:
            return
        
        # Get approver name
        approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name
        
        # Calculate working days (excluding Sundays)
        working_days = count_working_days(start_date, end_date)
        
        # Add note about cross-year leave if applicable
        cross_year_note = ""
        if end_date.year > start_date.year:
            days_in_current_year = count_working_days(start_date, datetime(start_date.year, 12, 31))
            days_in_next_year = count_working_days(datetime(end_date.year, 1, 1), end_date)
            cross_year_note = f"\n\nNote: This leave spans across different years.\n- Days in {start_date.year}: {days_in_current_year}\n- Days in {end_date.year}: {days_in_next_year}"
        
        # Prepare email data
        email_template = 'email/leave_approved.html'
        data = {
            'employee_details_id': leave_policy_details.employee_details_id,
            'type': leave_application_details.employee_leave_policy.leave_policy_id.leave_type,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'no_of_days': str(working_days),  # Use calculated working days
            'is_modified': 'Yes' if has_edited else 'No',
            'aprover_remarks': comment + cross_year_note,  # Add cross-year note to remarks
            'approver_name': approver,
            'status': 'accepted',
            'receiver_email': leave_application_details.employee_details_id.personal_email,
            'excluding_sundays': 'Yes'  # Add flag to indicate Sundays are excluded
        }
        
        # Send email
        send_email(email_template, data)
        print(f"Sent leave approval email with {working_days} working days (excluding Sundays)")
    except Exception as e:
        print(f"Error sending approval email: {e}")


def create_schedule_entry(leave_application_details, work_timings, current_date):
    """Create schedule entry for leave day"""
    # Check if already scheduled
    is_already_scheduled = CompanyEmployeeSchedule.objects(
        work_timings=work_timings._id,
        employee_id=leave_application_details.employee_details_id._id,
        schedule_from=current_date,
        schedule_till=current_date
    ).first()
    
    if not is_already_scheduled:
        # Create new schedule entry
        employee_schedule = CompanyEmployeeSchedule(
            company_id=leave_application_details.company_id.id,
            work_timings=work_timings._id,
            employee_id=leave_application_details.employee_details_id._id,
            schedule_from=current_date,
            schedule_till=current_date,
            allow_outside_checkin=False,
            is_leave=True,
            leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
        )
        employee_schedule.save()
        
        # Update company details
        CompanyDetails.objects(
            user_id=leave_application_details.company_id.id
        ).update(
            push__employee_schedules=employee_schedule._id
        )


def create_attendance_entry(leave_application_details, current_date):
    """Create attendance entry for leave day"""
    # Create new attendance entry
    employee_attendance = EmployeeAttendance(
        employee_id=leave_application_details.employee_details_id.employee_company_details.employee_id,
        employee_details_id=leave_application_details.employee_details_id._id,
        attendance_date=current_date,
        company_id=leave_application_details.company_id.id,
        leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name,
        attendance_status="absent"
    )
    employee_attendance.save()


def create_unpaid_leave_adjustment(leave_application_details, current_date):
    """Create payroll adjustment for unpaid leave"""
    try:
        # Get first day of month
        start_of_month = current_date.replace(day=1)
        
        # Calculate end of month
        nxt_mnth = current_date.replace(day=28) + timedelta(days=4)
        end_of_the_month = nxt_mnth - timedelta(days=nxt_mnth.day)
        
        # Get or create adjustment reason
        adjustment_reason = get_or_create_unpaid_leaves_adjustment_reason(
            leave_application_details.company_id.id
        )
        
        # Calculate daily wage
        total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary
        current_month = current_date.strftime('%B')
        
        # Get working days for the month
        no_of_working_days = get_working_days_in_month(
            leave_application_details.company_id.id,
            current_month,
            end_of_the_month.day
        )
        
        # Calculate adjustment amount
        adjustment_amount = round(int(total_salary) / no_of_working_days, 0)
        
        # Check if adjustment already exists
        adjustment_exists = CompanyPayrollAdjustment.objects(
            company_id=leave_application_details.company_id.id,
            employee_details_id=leave_application_details.employee_details_id._id,
            adjustment_reason_id=adjustment_reason._id,
            attendance_date=current_date
        ).first()
        
        if adjustment_exists:
            adjustment_exists.delete()
        
        # Create new adjustment
        new_data = CompanyPayrollAdjustment(
            company_id=leave_application_details.company_id.id,
            employee_details_id=leave_application_details.employee_details_id._id,
            adjustment_reason_id=adjustment_reason._id,
            adjustment_type=adjustment_reason.adjustment_type,
            adjustment_amount=str(adjustment_amount),
            adjustment_on=start_of_month,
            adjustment_month_on_payroll=start_of_month.strftime('%B'),
            adjustment_year_on_payroll=start_of_month.year,
            attendance_date=current_date
        )
        new_data.save()
    except Exception as e:
        print(f"Error creating unpaid leave adjustment: {e}")


def get_or_create_unpaid_leaves_adjustment_reason(company_id):
    """Get or create unpaid leaves adjustment reason"""
    adjustment_reason = CompanyAdjustmentReasons.objects(
        company_id=company_id,
        adjustment_reason="Unpaid Leaves"
    ).first()
    
    if not adjustment_reason:
        adjustment_reason = create_adjustment_reason(company_id, "Unpaid Leaves", "deduction")
    
    return adjustment_reason


def get_working_days_in_month(company_id, current_month, default_days):
    """Get configured working days for a month"""
    calendar_working_days = CompanyDetails.objects(
        user_id=company_id
    ).only('working_days').first()
    
    working_days = list(filter(
        lambda x: x['month'] == current_month.lower(),
        calendar_working_days.working_days
    ))
    
    return int(working_days[0]['days']) if working_days else default_days


def forward_to_next_approver(leave_request_details, leave_application_details, current_approval_level):
    """Forward leave request to next approver"""
    # Create new leave request for next approver
    request_approver = EmployeeLeaveRequest()
    request_approver.employee_leave_app_id = leave_application_details._id
    request_approver.company_id = leave_application_details.company_id.id
    
    # Calculate next approval level
    next_approval_level = int(current_approval_level) + 1
    
    # Find next approver
    department = leave_application_details.company_approver.department_name
    approver = EmployeeLeaveApprover.objects(
        employee_approval_level=str(next_approval_level),
        department_name=department,
        company_id=leave_application_details.company_id.id
    ).first()
    
    if approver:
        request_approver.approver_id = approver._id
    
    request_approver.save()
    
    # Update current request
    leave_request_details.update(
        request_status="approved",
        approved_on=datetime.now()
    )
    
    # Update leave application
    leave_application_details.update(
        current_approval_level=str(next_approval_level),
        current_aprrover=request_approver._id,
        add_to_set__approver_list=request_approver._id
    )
    
    return json.dumps({"status": "success"})




@employee.route('/superapproveleaverequest', methods=['POST'])
def super_approve_leave_request():
    """
    Simplified super approval function for leave requests without approval levels.
    This function directly approves the leave request without considering approval levels.
    """
    leave_request_id = request.form.get('leave_request_id')
    comment = request.form.get('approver_comment')
    
    if not leave_request_id:
        return json.dumps({"status": "failed", "message": "No leave request ID provided"})
    
    # Get leave request details
    leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
    if not leave_request_details:
        return json.dumps({"status": "failed", "message": "Leave request not found"})
    
    # Get leave application details
    leave_application_details = EmployeeLeaveApplication.objects(_id=leave_request_details.employee_leave_app_id._id).first()
    if not leave_application_details:
        return json.dumps({"status": "failed", "message": "Leave application not found"})
    
    # Add comment if provided
    if comment:
        leave_request_details.update(comment=comment)
        leave_application_details.update(push__approver_comments=leave_request_details._id)
    
    # Handle date edits if applicable
    has_edited = request.form.get('edit_leave_date')
    start_date = leave_application_details.leave_from
    end_date = leave_application_details.leave_till
    no_of_days = leave_application_details.no_of_days
    
    if has_edited:
        try:
            new_leave_range = request.form.get('daterange').split(' - ')
            start_date = datetime.strptime(new_leave_range[0], '%d/%m/%Y')
            end_date = datetime.strptime(new_leave_range[1], '%d/%m/%Y')
            
            # Calculate working days excluding Sundays
            working_days = count_working_days(start_date, end_date)
            no_of_days = str(working_days)
            
            print(f"Edited leave period: {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
            print(f"Working days (excluding Sundays): {working_days}")
            
            # Update leave application with new dates
            leave_application_details.update(
                leave_from=start_date,
                leave_till=end_date,
                no_of_days=no_of_days,
                asked_leave_from=start_date,  # Also update the asked dates
                asked_leave_till=end_date
            )
            
            leave_application_details.reload()
        except Exception as e:
            print(f"Error updating leave dates: {e}")
            return json.dumps({"status": "failed", "message": f"Error updating leave dates: {str(e)}"})
    
    # Get the current user as the super approver
    try:
        super_employee = EmployeeDetails.objects(user_id=current_user.id).first()
        super_approver_details = SuperLeaveApprovers.objects(employee_details_id=super_employee._id).first()
        
        # Mark as super approved
        leave_application_details.update(
            is_super_approved=True, 
            super_approver_comment=comment,
            super_approver=super_approver_details._id if super_approver_details else None
        )
    except Exception as e:
        print(f"Error setting super approver: {e}")
        # Continue with approval even if super approver setting fails
    
    # Check for cross-year leave requests
    is_cross_year = end_date.year > start_date.year
    if is_cross_year:
        print(f"Processing cross-year leave from {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
        # Calculate days in each year
        days_in_current_year = count_working_days(start_date, datetime(start_date.year, 12, 31))
        days_in_next_year = count_working_days(datetime(end_date.year, 1, 1), end_date)
        
        print(f"Working days in {start_date.year}: {days_in_current_year}")
        print(f"Working days in {end_date.year}: {days_in_next_year}")
        print(f"Total working days: {working_days if has_edited else count_working_days(start_date, end_date)}")
    
    # Check leave balance
    current_leave_balance = leave_application_details.employee_leave_policy.balance
    asking_leave_days = int(float(no_of_days)) if no_of_days else 0
    
    # Get the leave policy details
    leave_policy_details = EmployeeLeavePolicies.objects(_id=leave_application_details.employee_leave_policy._id).first()
    
    # Check if employee has sufficient balance
    if current_leave_balance >= asking_leave_days:
        return handle_sufficient_balance_sup(
            leave_request_details, leave_application_details, leave_policy_details,
            comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days
        )
    else:
        return handle_insufficient_balance_sup(
            leave_request_details, leave_application_details, leave_policy_details,
            comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days
        )


def handle_sufficient_balance_sup(leave_request_details, leave_application_details, leave_policy_details, 
                             comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days):
    """Handle approval when employee has sufficient leave balance"""
    try:
        # Update request status
        leave_request_details.update(
            request_status="approved", 
            approved_on=datetime.now(),
            comment=comment
        )
        
        # Calculate new balance
        new_balance = current_leave_balance - asking_leave_days
        
        # Update leave policy balance
        if leave_policy_details:
            leave_policy_details.update(balance=new_balance)
        
        # Update leave application status
        leave_application_details.update(
            leave_status="approved", 
            balance_before_approval=current_leave_balance, 
            balance_after_approval=new_balance, 
            approved_on=datetime.now()
        )
        
        # Create leave adjustment record
        adj_days = str(asking_leave_days if not has_edited else float(leave_application_details.no_of_days))
        after_adj = str(current_leave_balance - float(adj_days))
        
        new_data = create_leave_adjustment(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            'decrement',
            adj_days,
            comment,
            str(current_leave_balance),
            after_adj
        )
        
        leave_application_details.update(leave_adjustment=new_data._id)
        
        # Process schedule and attendance
        process_schedule_and_attendance_sup(leave_application_details, start_date, end_date, comment)
        
        # Send email notification
        send_approval_email_sup(leave_application_details, start_date, end_date, has_edited, comment)
        
        return json.dumps({"status": "success"})
    except Exception as e:
        print(f"Error in handle_sufficient_balance: {e}")
        return json.dumps({"status": "error", "message": str(e)})


def handle_insufficient_balance_sup(leave_request_details, leave_application_details, leave_policy_details, 
                              comment, has_edited, start_date, end_date, current_leave_balance, asking_leave_days):
    """Handle approval when employee has insufficient leave balance"""
    try:
        # Calculate difference between requested leave days and current balance
        difference = asking_leave_days - current_leave_balance
        
        # Approve the leave request
        leave_request_details.update(
            request_status="approved",
            approved_on=datetime.now(),
            comment=comment
        )
        
        # Set balance to 0 after deduction
        if leave_policy_details:
            leave_policy_details.update(balance=0)
        
        # Extract IDs safely
        employee_id = leave_application_details.employee_details_id._id
        company_id = leave_application_details.company_id.id
        
        # Ensure ObjectId type for IDs
        company_id = ObjectId(company_id) if not isinstance(company_id, ObjectId) else company_id
        employee_id = ObjectId(employee_id) if not isinstance(employee_id, ObjectId) else employee_id
        
        # Find unpaid leave policy
        unpaid_policy_id, policy_balance = find_unpaid_leave_policy_sup(company_id, employee_id)
        
        # Update leave application details
        leave_application_details.update(
            leave_status="approved",
            balance_before_approval=current_leave_balance,
            balance_after_approval=0,
            approved_on=datetime.now()
        )
        
        # Handle cross-year leave requests
        if end_date.year > start_date.year:
            process_cross_year_adjustments_sup(
                leave_application_details, leave_policy_details, company_id,
                current_leave_balance, start_date, end_date, comment
            )
        else:
            # Process standard leave adjustments
            process_standard_adjustments_sup(
                leave_application_details, leave_policy_details, company_id,
                current_leave_balance, difference, unpaid_policy_id, policy_balance, comment
            )
        
        # Process schedule and attendance
        process_schedule_and_attendance_sup(leave_application_details, start_date, end_date, comment)
        
        # Send email notification
        send_approval_email_sup(leave_application_details, start_date, end_date, has_edited, comment)
        
        return json.dumps({"status": "success"})
    except Exception as e:
        print(f"Error in handle_insufficient_balance: {e}")
        return json.dumps({"status": "error", "message": str(e)})


def process_schedule_and_attendance_sup(leave_application_details, start_date, end_date, comment):
    """Process schedule and attendance updates for the approved leave"""
    # Get or create day off work timings
    work_timings = WorkTimings.objects(
        is_day_off=True, 
        company_id=leave_application_details.company_id.id
    ).first()
    
    if not work_timings:
        work_timings = WorkTimings(
            name="Day Off",
            schedule_color='#808080',
            is_day_off=True,
            office_start_at='',
            office_end_at='',
            late_arrival__later_than='',
            early_departure_earliar_than='',
            consider_absent_after='',
            week_offs='',
            company_id=leave_application_details.company_id.id
        )
        work_timings.save()
        
        CompanyDetails.objects(
            user_id=leave_application_details.company_id.id
        ).update(
            push__worktimings=work_timings._id
        )
    
    # Process each day in the leave period
    current_date = start_date
    while current_date <= end_date:
        # Skip Sundays (weekday 6)
        if current_date.weekday() == 6:
            current_date += timedelta(days=1)
            continue
        
        # Check if already scheduled
        is_already_scheduled = CompanyEmployeeSchedule.objects(
            work_timings=work_timings._id,
            employee_id=leave_application_details.employee_details_id._id,
            schedule_from=current_date,
            schedule_till=current_date
        ).first()
        
        if not is_already_scheduled:
            # Create schedule entry
            employee_schedule = CompanyEmployeeSchedule(
                company_id=leave_application_details.company_id.id,
                work_timings=work_timings._id,
                employee_id=leave_application_details.employee_details_id._id,
                schedule_from=current_date,
                schedule_till=current_date,
                allow_outside_checkin=False,
                is_leave=True,
                leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
            )
            employee_schedule.save()
            
            CompanyDetails.objects(
                user_id=leave_application_details.company_id.id
            ).update(
                push__employee_schedules=employee_schedule._id
            )
            
            # Create attendance entry
            employee_attendance = EmployeeAttendance(
                employee_id=leave_application_details.employee_details_id.employee_company_details.employee_id,
                employee_details_id=leave_application_details.employee_details_id._id,
                attendance_date=current_date,
                company_id=leave_application_details.company_id.id,
                leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name,
                attendance_status="absent"
            )
            employee_attendance.save()
            
            # Handle unpaid leave adjustments
            if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
                create_unpaid_leave_adjustment_sup(leave_application_details, current_date)
        
        current_date += timedelta(days=1)


def count_working_days_sup(start_date, end_date):
    """Count the number of working days (excluding Sundays) between two dates"""
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Skip Sundays (weekday 6)
        if current_date.weekday() != 6:
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days


def find_unpaid_leave_policy_sup(company_id, employee_id):
    """Find the unpaid leave policy for the employee"""
    # Query for leave policies
    leave_policies = EmployeeLeavePolicies.objects(
        company_id=company_id,
        employee_details_id=employee_id
    )
    
    # Find the policy ID for "Unpaid Leaves"
    emp_leave_policy_id = None
    policy_balance = 0
    
    if leave_policies:
        for policy in leave_policies:
            # Check if this is the "Unpaid Leaves" policy
            if policy.leave_policy_id.leave_policy_name == "Unpaid Leaves":
                emp_leave_policy_id = str(policy._id)
                policy_balance = policy.balance
    
    return emp_leave_policy_id, policy_balance


def create_leave_adjustment_sup(company_id, employee_details_id, employee_leave_pol_id, 
                           adjustment_type, adjustment_days, adjustment_comment,
                           before_adjustment, after_adjustment, created_at=None):
    """Create a leave adjustment record"""
    new_data = EmployeeLeaveAdjustment(
        company_id=company_id,
        employee_details_id=employee_details_id,
        employee_leave_pol_id=employee_leave_pol_id,
        adjustment_type=adjustment_type,
        adjustment_days=adjustment_days,
        adjustment_comment=adjustment_comment,
        before_adjustment=before_adjustment,
        after_adjustment=after_adjustment
    )
    
    if created_at:
        new_data.created_at = created_at
    
    new_data.save()
    return new_data


def process_cross_year_adjustments_sup(leave_application_details, leave_policy_details, company_id,
                                  current_leave_balance, start_date, end_date, comment):
    """Process adjustments for leave requests that span across years"""
    # Calculate days in current year and next year (excluding Sundays)
    first_day_next_year = datetime(end_date.year, 1, 1)
    
    # Count working days in current year (excluding Sundays)
    days_in_current_year = count_working_days_sup(start_date, datetime(start_date.year, 12, 31))
    
    # Count working days in next year (excluding Sundays)
    days_in_next_year = count_working_days_sup(first_day_next_year, end_date)
    
    print(f"Working days in current year: {days_in_current_year}")
    print(f"Working days in next year: {days_in_next_year}")
    
    if current_leave_balance != 0:
        # Determine how many days to deduct from current year's balance
        days_to_deduct_current_year = min(days_in_current_year, current_leave_balance)
        
        # First adjustment (deduct from current year balance)
        new_data = create_leave_adjustment_sup(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            'decrement',
            str(days_to_deduct_current_year),
            f"Leave from {start_date.strftime('%d/%m/%Y')} to {datetime(start_date.year, 12, 31).strftime('%d/%m/%Y')} (excluding Sundays)",
            str(current_leave_balance),
            str(current_leave_balance - days_to_deduct_current_year)
        )
        
        remaining_balance = current_leave_balance - days_to_deduct_current_year
        
        leave_application_details.update(leave_adjustment=new_data._id)
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(leave_application_details.employee_leave_policy._id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=remaining_balance
        )
        
        # Get leave allowance for next year
        leave_allow = get_leave_allowance_sup(leave_application_details)
        
        # Calculate new balance after deduction for next year
        leave_allow_balance = leave_allow - days_in_next_year
        
        # Create adjustment for next year
        created_at = first_day_next_year.strftime("%d %B %Y %H:%M:%S")
        
        new_data = create_leave_adjustment_sup(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            "decrement",
            str(days_in_next_year),
            f"Leave from {first_day_next_year.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')} (excluding Sundays)",
            str(leave_allow),
            str(leave_allow_balance),
            created_at
        )
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(leave_application_details.employee_leave_policy._id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=leave_allow_balance
        )


def process_standard_adjustments_sup(leave_application_details, leave_policy_details, company_id,
                                current_leave_balance, difference, unpaid_policy_id, policy_balance, comment):
    """Process adjustments for standard leave requests"""
    if current_leave_balance != 0:
        # First adjustment (deduct full current balance)
        new_data = create_leave_adjustment(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            leave_application_details.employee_leave_policy._id,
            'decrement',
            str(current_leave_balance),
            str(comment),
            str(current_leave_balance),
            "0"
        )
        
        leave_application_details.update(leave_adjustment=new_data._id)
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(leave_application_details.employee_leave_policy._id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=0
        )
    
    # If unpaid leave policy exists, update it
    if unpaid_policy_id:
        new_policy_balance = policy_balance - difference
        
        new_data = create_leave_adjustment_sup(
            leave_policy_details.company_id,
            leave_policy_details.employee_details_id,
            ObjectId(unpaid_policy_id),
            'decrement',
            str(difference),
            str(comment),
            str(policy_balance),
            str(-new_policy_balance)
        )
        
        leave_application_details.update(leave_adjustment=new_data._id)
        
        EmployeeLeavePolicies.objects(
            company_id=company_id,
            _id=ObjectId(unpaid_policy_id)
        ).update(
            push__employee_leave_adjustments=new_data._id, 
            balance=float(new_policy_balance)
        )


def get_leave_allowance_sup(leave_application_details):
    """Get the leave allowance for a policy"""
    # Default allowance
    leave_allow = 24
    
    # Query for leave policies
    leave_policies = EmployeeLeavePolicies.objects(
        company_id=leave_application_details.company_id.id,
        employee_details_id=leave_application_details.employee_details_id._id
    )
    
    # Find the current policy allowance
    if leave_policies:
        for policy in leave_policies:
            if str(policy._id) == str(leave_application_details.employee_leave_policy._id):
                leave_allow = getattr(policy, "allowance_day", 24)
                break
    
    return leave_allow


def create_adjustment_reason_sup(company_id, reason_name, adjustment_type):
    """Create an adjustment reason"""
    adjustment_reason = CompanyAdjustmentReasons(
        company_id=company_id,
        adjustment_reason=reason_name,
        adjustment_type=adjustment_type
    )
    adjustment_reason.save()
    return adjustment_reason


def send_approval_email_sup(leave_application_details, start_date, end_date, has_edited, comment):
    """Send approval email to employee"""
    try:
        # Get policy details
        leave_policy_details = EmployeeLeavePolicies.objects(
            _id=leave_application_details.employee_leave_policy._id
        ).first()
        
        if not leave_policy_details:
            return
        
        # Get approver information
        try:
            approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name
        except:
            approver = "Super Approver"  # Default if approver info not found
        
        # Calculate working days (excluding Sundays)
        working_days = count_working_days_sup(start_date, end_date)
        
        # Add note about cross-year leave if applicable
        cross_year_note = ""
        if end_date.year > start_date.year:
            days_in_current_year = count_working_days_sup(start_date, datetime(start_date.year, 12, 31))
            days_in_next_year = count_working_days_sup(datetime(end_date.year, 1, 1), end_date)
            cross_year_note = f"\n\nNote: This leave spans across different years.\n- Days in {start_date.year}: {days_in_current_year}\n- Days in {end_date.year}: {days_in_next_year}"
        
        # Prepare email data
        email_template = 'email/leave_approved.html'
        data = {
            'employee_details_id': leave_policy_details.employee_details_id,
            'type': leave_application_details.employee_leave_policy.leave_policy_id.leave_type,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'no_of_days': str(working_days),  # Use calculated working days
            'is_modified': 'Yes' if has_edited else 'No',
            'aprover_remarks': comment + cross_year_note,  # Add cross-year note to remarks
            'approver_name': approver,
            'status': 'accepted',
            'receiver_email': leave_application_details.employee_details_id.personal_email,
            'excluding_sundays': 'Yes'  # Add flag to indicate Sundays are excluded
        }
        
        # Send email
        send_email(email_template, data)
        print(f"Sent leave approval email with {working_days} working days (excluding Sundays)")
    except Exception as e:
        print(f"Error sending approval email: {e}")


def create_unpaid_leave_adjustment_sup(leave_application_details, current_date):
    """Create payroll adjustment for unpaid leave"""
    try:
        # Get first day of month
        start_of_month = current_date.replace(day=1)
        
        # Calculate end of month
        nxt_mnth = current_date.replace(day=28) + timedelta(days=4)
        end_of_the_month = nxt_mnth - timedelta(days=nxt_mnth.day)
        
        # Get or create adjustment reason
        adjustment_reason = CompanyAdjustmentReasons.objects(
            company_id=leave_application_details.company_id.id,
            adjustment_reason="Unpaid Leaves"
        ).first()
        
        if not adjustment_reason:
            adjustment_reason = create_adjustment_reason_sup(
                leave_application_details.company_id.id,
                "Unpaid Leaves",
                "deduction"
            )
        
        # Calculate daily wage
        total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary
        current_month = current_date.strftime('%B')
        
        # Get working days for the month
        calendar_working_days = CompanyDetails.objects(
            user_id=leave_application_details.company_id.id
        ).only('working_days').first()
        
        working_days = list(filter(
            lambda x: x['month'] == current_month.lower(),
            calendar_working_days.working_days
        ))
        
        no_of_working_days = int(working_days[0]['days']) if working_days else end_of_the_month.day
        
        # Calculate adjustment amount
        adjustment_amount = round(int(total_salary) / no_of_working_days, 0)
        
        # Check if adjustment already exists
        adjustment_exists = CompanyPayrollAdjustment.objects(
            company_id=leave_application_details.company_id.id,
            employee_details_id=leave_application_details.employee_details_id._id,
            adjustment_reason_id=adjustment_reason._id,
            attendance_date=current_date
        ).first()
        
        if adjustment_exists:
            adjustment_exists.delete()
        
        # Create new adjustment
        new_data = CompanyPayrollAdjustment(
            company_id=leave_application_details.company_id.id,
            employee_details_id=leave_application_details.employee_details_id._id,
            adjustment_reason_id=adjustment_reason._id,
            adjustment_type=adjustment_reason.adjustment_type,
            adjustment_amount=str(adjustment_amount),
            adjustment_on=start_of_month,
            adjustment_month_on_payroll=start_of_month.strftime('%B'),
            adjustment_year_on_payroll=start_of_month.year,
            attendance_date=current_date
        )
        new_data.save()
    except Exception as e:
        print(f"Error creating unpaid leave adjustment: {e}")

# @employee.route('/approveleaverequest', methods=['POST'])
# def approve_leave_request():
#     leave_request_id = request.form.get('leave_request_id')
#     comment = request.form.get('approver_comment')
    
#     has_edited = request.form.get('edit_leave_date')
#     if has_edited:
#         new_leave_range = request.form.get('daterange').split(' - ')
#         new_leave_from = datetime. strptime(new_leave_range[0], '%d/%m/%Y')
#         new_leave_till = datetime. strptime(new_leave_range[1], '%d/%m/%Y')
#         new_no_of_days = request.form.get('no_of_days')
        
#         delta = new_leave_till - new_leave_from
#         new_no_of_days = delta.days + 1 

#     if leave_request_id:
#         leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
#         # check if the data exist or not 
#         if leave_request_details:
#             leave_application_details = EmployeeLeaveApplication.objects(_id=leave_request_details.employee_leave_app_id._id).first()
#             if comment:
#                 leave_request_details.update(comment=comment)
#                 leave_application_details.update(push__approver_comments=leave_request_details._id)
#             # if edited the leave dates update those


#             if has_edited:
#                 leave_application_details.update(leave_from=new_leave_from, leave_till=new_leave_till, no_of_days=new_no_of_days)
            
#             current_approval_level = leave_application_details.current_approval_level
#             company_approval_level = leave_application_details.company_approval_level
            
#             # if the current approval level is equals to company approval level assume this is the last approver in the level else pass onto the next approver
#             if current_approval_level == company_approval_level:
#                 # Final approver
#                 # Todo: Check if the user has the balance to be able to get approved
#                 current_leave_balance = leave_application_details.employee_leave_policy.balance
#                 asking_leave_days = int(leave_application_details.no_of_days)
#                 # if  (current_leave_balance >= asking_leave_days): #Todo: This condition need to be checked 
#                 if leave_application_details:
#                     asked_leave_from = leave_application_details.asked_leave_from
#                     asked_leave_till = leave_application_details.asked_leave_till

#                     print(f"Asked leave from: {asked_leave_from}")
#                     print(f"Asked leave till: {asked_leave_till}")

#                     # Check if asked_leave_till is in the next year compared to asked_leave_from
#                     if asked_leave_till.year > asked_leave_from.year:
#                         print("The 'asked_leave_till' date is in the next year.")
#                     else:
#                         print("The 'asked_leave_till' date is not in the next year.")
#                 else:
#                     print("No leave application details found.")
#                 if (current_leave_balance >= asking_leave_days):
#                     # Todo: Change the leave status of both the application and request
#                         # leave_request_details.request_status = "approved"
#                         # leave_request_details.approved_on = datetime.now()
#                     leave_request_details.update(request_status="approved",approved_on=datetime.now(),comment=comment)
#                     # Todo: Deduct the leave balance
#                     new_balance =current_leave_balance - asking_leave_days
#                     leave_policy_details = EmployeeLeavePolicies.objects(_id=leave_application_details.employee_leave_policy._id).first()
#                     if leave_policy_details:
#                         leave_policy_details.update(balance=new_balance)
#                     # if any Comment By the Approver
                        
#                     leave_application_details.update(current_approval_level="",leave_status="approved",balance_before_approval=current_leave_balance,balance_after_approval=new_balance,approved_on=datetime.now())

#                     # -------create leave adjuestment data so this leave appears in the leave adjustment-------

#                     # ---gathering data for leave adjustment---
#                     # employee_details = EmployeeCompanyDetails.objects(user_id=current_user.id).first()
#                     # company_id = employee_details.company_id

#                     # leave_application_details = EmployeeLeaveApplication.objects(_id=leave_request_details.employee_leave_app_id._id).first()
#                     # employee_leave_pol_id = leave_application_details.employee_leave_policy

#                     # ---end of gathering data for leave adjustment----

#                     adj_days = str(asking_leave_days if not has_edited else new_no_of_days)
#                     after_adj = str(current_leave_balance - float(adj_days))

#                     new_data = EmployeeLeaveAdjustment(
#                                    company_id = leave_policy_details.company_id,
#                                    employee_details_id = leave_policy_details.employee_details_id,
#                                    employee_leave_pol_id = leave_application_details.employee_leave_policy._id,
#                                    adjustment_type = 'decrement',
#                                    adjustment_days = adj_days,
#                                    adjustment_comment = str(comment),
#                                    before_adjustment = str(current_leave_balance),
#                                    after_adjustment = after_adj         
#                         )
#                     status = new_data.save()

#                     leave_application_details.update(leave_adjustment=new_data._id)
#                     leave_application_details.save()

#                     # --------------------------end of creating leave adjustment---------------------------------


#                     # Todo: Add the record in the Shift Scheduler
#                     # Firstly get the day off worktimings details, if not exist create one??
#                     work_timings = WorkTimings.objects(is_day_off=True,company_id=leave_application_details.company_id.id).first()
#                     if not work_timings:
#                         # Create a new work timings of day off data
#                         work_timings =  WorkTimings(name="Day Off",
#                                     schedule_color='#808080',
#                                     is_day_off=True,
#                                     office_start_at='',
#                                     office_end_at='',
#                                     late_arrival__later_than='',
#                                     early_departure_earliar_than='',
#                                     consider_absent_after='',
#                                     week_offs = '',
#                                     company_id = leave_application_details.company_id.id
#                                     )
#                         work_timings.save()
#                         update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__worktimings=work_timings._id)

#                     start_date = leave_application_details.leave_from if not has_edited else new_leave_from
#                     end_date = leave_application_details.leave_till if not has_edited else new_leave_till


#                     # .................send an email to the leave applicant about approval ...........
#                     approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name

#                     # email_template = 'email/leave_approved.html'
#                     # data = {}

#                     # data['employee_details_id'] = leave_policy_details.employee_details_id
#                     # data['type'] = leave_application_details.employee_leave_policy.leave_policy_id.leave_type
#                     # data['start_date'] = start_date.strftime('%Y-%m-%d')
#                     # data['end_date'] = end_date.strftime('%Y-%m-%d')
#                     # data['no_of_days'] = adj_days
#                     # data['is_modified'] = 'Yes' if has_edited else 'No'
#                     # data['aprover_remarks'] = comment
#                     # data['approver_name'] = approver
#                     # data['status'] = 'accepted'
#                     # data['receiver_email'] = leave_application_details.employee_details_id.personal_email

#                     # send_email(email_template, data)

#                     #.................end of sending email.............................................
                    
#                     while start_date <= end_date:
#                         is_already_scheduled = CompanyEmployeeSchedule.objects(work_timings=work_timings._id,employee_id=leave_application_details.employee_details_id._id,schedule_from=start_date,schedule_till=start_date).first()
#                         if not is_already_scheduled:
#                             employee_schedule = CompanyEmployeeSchedule(company_id=leave_application_details.company_id.id,
#                                                             work_timings=work_timings._id,
#                                                             employee_id=leave_application_details.employee_details_id._id,
#                                                             schedule_from=start_date,
#                                                             schedule_till=start_date,
#                                                             allow_outside_checkin = False,
#                                                             is_leave = True,
#                                                             leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                                 )
#                             employee_schedule.save()                        
#                             update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__employee_schedules=employee_schedule._id)
#                             # Add attendance Data as well
#                             employee_attendance = EmployeeAttendance()    
#                             employee_attendance.employee_id = leave_application_details.employee_details_id.employee_company_details.employee_id
#                             employee_attendance.employee_details_id = leave_application_details.employee_details_id._id
#                             employee_attendance.attendance_date = start_date
#                             employee_attendance.company_id = leave_application_details.company_id.id
#                             employee_attendance.leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                             employee_attendance.attendance_status = "absent"
#                             employee_attendance.save()
#                         # start_date = start_date + timedelta(days=1)
#                         # todo: Create an adjustment record if the leave policy type is unpaid
#                         if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
#                             start_of_month = start_date.replace(day=1)
#                             nxt_mnth = start_date.replace(day=28) + timedelta(days=4)
#                             # subtracting the days from next month date to
#                             # get last date of current Month
#                             end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
#                              # Todo: Create a adjustment record by deducting the off day amount
#                             # Check if the adjustment reason is defined if not create a adjustment reason for Unpaid Leaves
#                             adjustment_reason = CompanyAdjustmentReasons.objects(company_id=leave_application_details.company_id.id,adjustment_reason="Unpaid Leaves").first()
#                             if not adjustment_reason:
#                                 adjustment_reason = create_adjustment_reason(leave_application_details.company_id.id,"Unpaid Leaves","deduction")
                            
#                             # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
#                             total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary
                            
#                             current_month = start_date.strftime('%B')

#                             calendar_working_days = CompanyDetails.objects(user_id=leave_application_details.company_id.id).only('working_days').first()
#                             # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
#                             working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))

#                             no_of_working_days = int(working_days[0]['days']) if working_days else end_of_the_month.days() # By Default Set to 30 Days
                                                
#                             adjustment_amount = round(int(total_salary)/no_of_working_days,0)
                            
#                             adjustment_exists = CompanyPayrollAdjustment.objects(company_id=leave_application_details.company_id.id,
#                                                                     employee_details_id=leave_application_details.employee_details_id._id,
#                                                                     adjustment_reason_id=adjustment_reason._id,
#                                                                     attendance_date=start_date).first()
#                             if adjustment_exists:
#                                 adjustment_exists.delete()
                                
#                             new_data = CompanyPayrollAdjustment(
#                                     company_id = leave_application_details.company_id.id,
#                                     employee_details_id = leave_application_details.employee_details_id._id,
#                                     adjustment_reason_id = adjustment_reason._id,
#                                     adjustment_type = adjustment_reason.adjustment_type,
#                                     adjustment_amount = str(adjustment_amount),
#                                     adjustment_on = start_of_month,
#                                     adjustment_month_on_payroll = start_of_month.strftime('%B'),
#                                     adjustment_year_on_payroll =  start_of_month.year,
#                                     attendance_date =  start_date,                   
#                             )   
#                             new_data.save()
#                         start_date = start_date + timedelta(days=1)
#                 else:
#                     try:
                       
#                         # Calculate difference between requested leave days and current balance
#                         difference = asking_leave_days - current_leave_balance

#                         # Approve the leave request
#                         leave_request_details.update(
#                             request_status="approved",
#                             approved_on=datetime.now(),
#                             comment=comment
#                         )

#                         # Deduct leave balance and update leave policy details
#                         leave_policy_details = EmployeeLeavePolicies.objects(
#                             _id=leave_application_details.employee_leave_policy._id
#                         ).first()

#                         if leave_policy_details:
#                             leave_policy_details.update(balance=0)  # Set balance to 0 after deduction

#                         # Safely extract employee_id and company_id
#                         employee_id = leave_application_details.employee_details_id._id
#                         company_id = leave_application_details.company_id.id

#                         # Ensure ObjectId type for IDs
#                         company_id = ObjectId(company_id) if not isinstance(company_id, ObjectId) else company_id
#                         employee_id = ObjectId(employee_id) if not isinstance(employee_id, ObjectId) else employee_id

#                         # Query for leave policies
#                         leave_policies = EmployeeLeavePolicies.objects(
#                             company_id=company_id,
#                             employee_details_id=employee_id
#                         )

#                         # Find the policy ID for "Unpaid Leaves"
#                         emp_leave_policy_id = None
#                         policies_array = []  # Initialize an empty list to store all policy details

#                         policy_balance = 0
#                         emp_leave_policy_id = None  # Initialize emp_leave_policy_id

#                         # if leave_policies:
#                         #     for policy in leave_policies:
#                         #         # Store policy details in the array
#                         #         policies_array.append({
#                         #             "policy_id": str(policy._id),
#                         #             "policy_name": policy.leave_policy_id.leave_policy_name,
#                         #             "balance": policy.balance
#                         #         })

#                         #         # Check if this is the "Unpaid Leaves" policy
#                         #         if policy.leave_policy_id.leave_policy_name == "Unpaid Leaves":
#                         #             emp_leave_policy_id = str(policy._id)
#                         #             policy_balance = policy.balance

#                         #     if not emp_leave_policy_id:
#                         #         print("No policy found with the name 'Unpaid Leaves'.")
#                         # else:
#                         #     print("No leave policies found for this employee.")

#                         # # Example output of policies_array
#                         # print(policies_array

#                         if leave_policies:
#                             for policy in leave_policies:
                                
#                                 policies_array.append({
#                                     "policy_id": str(policy._id),
#                                     "policy_name": policy.leave_policy_id.leave_policy_name,
#                                     "balance": policy.balance,
#                                     "leave_policy_id": policy.leave_policy_id, 
#                                     "allowance_day": getattr(policy, "allowance_day", 30),                                
#                                 })

#                                 # Check if this is the "Unpaid Leaves" policy
#                                 if policy.leave_policy_id.leave_policy_name == "Unpaid Leaves":
#                                     emp_leave_policy_id = str(policy._id)
#                                     policy_balance = policy.balance

#                             if not emp_leave_policy_id:
#                                 print("No policy found with the name 'Unpaid Leaves'.")
#                         else:
#                             print("No leave policies found for this employee.")

#                         # Example output of policies_array
#                         print(policies_array)



#                         # Update leave application details
#                         leave_application_details.update(
#                             current_approval_level="",
#                             leave_status="approved",
#                             balance_before_approval=current_leave_balance,
#                             balance_after_approval=0,
#                             approved_on=datetime.now()
#                         )

#                         # Calculate adjustment days
#                         adj_days = asking_leave_days if not has_edited else new_no_of_days
#                         after_adj = current_leave_balance - float(adj_days)


                        

#                         if asked_leave_till.year > asked_leave_from.year:
#                             # Calculate how many days are in the next year
#                             first_day_next_year = datetime(asked_leave_till.year, 1, 1)
#                             days_in_next_year = (asked_leave_till - first_day_next_year).days + 1  # Include `asked_leave_till` itself

#                             print(f"Days in next year: {days_in_next_year}")

#                             if current_leave_balance != 0:
#                                 # First adjustment (deduct full current balance)
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
#                                     adjustment_type='decrement',
#                                     adjustment_days=str(current_leave_balance),
#                                     adjustment_comment=str(comment),
#                                     before_adjustment=str(current_leave_balance),
#                                     after_adjustment="0"  # Balance after full deduction
#                                 )
#                                 status = new_data.save()
#                                 leave_application_details.update(leave_adjustment=new_data._id)
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(leave_application_details.employee_leave_policy._id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=0)

#                                 # Second adjustment for new leave balance with `created_at` as the first day of next year
#                                 created_at = first_day_next_year.strftime("%d %B %Y %H:%M:%S")  # Format: 01 January 2023 00:00:00

#                                 leave_allow = 30  # Default allowance
#                                 for policy in policies_array:
#                                     if policy["policy_id"] == str(leave_application_details.employee_leave_policy._id):
#                                         leave_allow = policy["allowance_day"]
#                                         break

#                                 # Example of applying the adjustment logic using the leave allowance
#                                 print(f"Leave allowance for policy {leave_application_details.employee_leave_policy._id}: {leave_allow}")

#                                 leave_allow_balance=leave_allow-days_in_next_year
#                                 # Save second adjustment (if applicable)
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
#                                     adjustment_type="decrement",
#                                     adjustment_days=str(days_in_next_year),
#                                     adjustment_comment="Adjustment for new year",
#                                     before_adjustment=str(leave_allow),  # Assuming fully deducted
#                                     after_adjustment=str(leave_allow_balance),  # New allowance for the year
#                                     created_at=created_at
#                                 )
#                                 status = new_data.save()
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(leave_application_details.employee_leave_policy._id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=leave_allow_balance)

#                                 print(f"Adjustment saved with created_at: {created_at}")

#                         else:
#                                # Create leave adjustments
#                             if current_leave_balance != 0:
#                                 # First adjustment (deduct full current balance)
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
#                                     adjustment_type='decrement',
#                                     adjustment_days=str(current_leave_balance),
#                                     adjustment_comment=str(comment),
#                                     before_adjustment=str(current_leave_balance),
#                                     after_adjustment="0"  # Balance after full deduction
#                                 )
#                                 status = new_data.save()
#                                 leave_application_details.update(leave_adjustment=new_data._id)
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(leave_application_details.employee_leave_policy._id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=0)
                            
                           
#                             if emp_leave_policy_id:
#                                 new_policy_balance = policy_balance + difference
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=ObjectId(emp_leave_policy_id),
#                                     adjustment_type='decrement',
#                                     adjustment_days=str(difference),  # Always store positive adjustment days
#                                     adjustment_comment=str(comment),
#                                     before_adjustment=str(policy_balance),
#                                     after_adjustment=str(-new_policy_balance)
#                                 )
#                                 status = new_data.save()
#                                 leave_application_details.update(leave_adjustment=new_data._id)
                                
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(emp_leave_policy_id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=float(-new_policy_balance))

                     
#                             print("Leave adjustment saved successfully.", status)

#                     except Exception as e:
#                         print(f"Error saving leave adjustment: {e}")

                   
#                     work_timings = WorkTimings.objects(is_day_off=True,company_id=leave_application_details.company_id.id).first()
#                     if not work_timings:
                      
#                         work_timings =  WorkTimings(name="Day Off",
#                                     schedule_color='#808080',
#                                     is_day_off=True,
#                                     office_start_at='',
#                                     office_end_at='',
#                                     late_arrival__later_than='',
#                                     early_departure_earliar_than='',
#                                     consider_absent_after='',
#                                     week_offs = '',
#                                     company_id = leave_application_details.company_id.id
#                                     )
#                         work_timings.save()
#                         update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__worktimings=work_timings._id)

#                     start_date = leave_application_details.leave_from if not has_edited else new_leave_from
#                     end_date = leave_application_details.leave_till if not has_edited else new_leave_till


#                     # .................send an email to the leave applicant about approval ...........
#                     approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name

#                     # email_template = 'email/leave_approved.html'
#                     # data = {}

#                     # data['employee_details_id'] = leave_policy_details.employee_details_id
#                     # data['type'] = leave_application_details.employee_leave_policy.leave_policy_id.leave_type
#                     # data['start_date'] = start_date.strftime('%Y-%m-%d')
#                     # data['end_date'] = end_date.strftime('%Y-%m-%d')
#                     # data['no_of_days'] = adj_days
#                     # data['is_modified'] = 'Yes' if has_edited else 'No'
#                     # data['aprover_remarks'] = comment
#                     # data['approver_name'] = approver
#                     # data['status'] = 'accepted'
#                     # data['receiver_email'] = leave_application_details.employee_details_id.personal_email

#                     # send_email(email_template, data)

#                     #.................end of sending email.............................................
                    
#                     while start_date <= end_date:
#                         is_already_scheduled = CompanyEmployeeSchedule.objects(work_timings=work_timings._id,employee_id=leave_application_details.employee_details_id._id,schedule_from=start_date,schedule_till=start_date).first()
#                         if not is_already_scheduled:
#                             employee_schedule = CompanyEmployeeSchedule(company_id=leave_application_details.company_id.id,
#                                                             work_timings=work_timings._id,
#                                                             employee_id=leave_application_details.employee_details_id._id,
#                                                             schedule_from=start_date,
#                                                             schedule_till=start_date,
#                                                             allow_outside_checkin = False,
#                                                             is_leave = True,
#                                                             leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                                 )
#                             employee_schedule.save()                        
#                             update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__employee_schedules=employee_schedule._id)
#                             # Add attendance Data as well
#                             employee_attendance = EmployeeAttendance()    
#                             employee_attendance.employee_id = leave_application_details.employee_details_id.employee_company_details.employee_id
#                             employee_attendance.employee_details_id = leave_application_details.employee_details_id._id
#                             employee_attendance.attendance_date = start_date
#                             employee_attendance.company_id = leave_application_details.company_id.id
#                             employee_attendance.leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                             employee_attendance.attendance_status = "absent"
#                             employee_attendance.save()
#                         # start_date = start_date + timedelta(days=1)
#                         # todo: Create an adjustment record if the leave policy type is unpaid
#                         if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
#                             start_of_month = start_date.replace(day=1)
#                             nxt_mnth = start_date.replace(day=28) + timedelta(days=4)
#                             # subtracting the days from next month date to
#                             # get last date of current Month
#                             end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
#                              # Todo: Create a adjustment record by deducting the off day amount
#                             # Check if the adjustment reason is defined if not create a adjustment reason for Unpaid Leaves
#                             adjustment_reason = CompanyAdjustmentReasons.objects(company_id=leave_application_details.company_id.id,adjustment_reason="Unpaid Leaves").first()
#                             if not adjustment_reason:
#                                 adjustment_reason = create_adjustment_reason(leave_application_details.company_id.id,"Unpaid Leaves","deduction")
                            
#                             # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
#                             total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary
                            
#                             current_month = start_date.strftime('%B')

#                             calendar_working_days = CompanyDetails.objects(user_id=leave_application_details.company_id.id).only('working_days').first()
                          
#                             working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))

#                             no_of_working_days = int(working_days[0]['days']) if working_days else end_of_the_month.days() # By Default Set to 30 Days
                                                
#                             adjustment_amount = round(int(total_salary)/no_of_working_days,0)
                            
#                             adjustment_exists = CompanyPayrollAdjustment.objects(company_id=leave_application_details.company_id.id,
#                                                                     employee_details_id=leave_application_details.employee_details_id._id,
#                                                                     adjustment_reason_id=adjustment_reason._id,
#                                                                     attendance_date=start_date).first()
#                             if adjustment_exists:
#                                 adjustment_exists.delete()
                                
#                             new_data = CompanyPayrollAdjustment(
#                                     company_id = leave_application_details.company_id.id,
#                                     employee_details_id = leave_application_details.employee_details_id._id,
#                                     adjustment_reason_id = adjustment_reason._id,
#                                     adjustment_type = adjustment_reason.adjustment_type,
#                                     adjustment_amount = str(adjustment_amount),
#                                     adjustment_on = start_of_month,
#                                     adjustment_month_on_payroll = start_of_month.strftime('%B'),
#                                     adjustment_year_on_payroll =  start_of_month.year,
#                                     attendance_date =  start_date,                   
#                             )   
#                             new_data.save()
#                         start_date = start_date + timedelta(days=1)
                  
                
#                     # msg = json.dumps({
#                     #     "status": "failed",
#                     #     "message": "Insufficient leave balance",
#                     #     "current_balance": current_leave_balance,
#                     #     "asking_leave_days": asking_leave_days,
#                     #     "difference": difference
#                     # })
#                     # msghtml = json.loads(msg)
#                     # return msghtml
#                     msg =  json.dumps({'status':'success'})
#                     msghtml = json.loads(msg)
#                     return msghtml


#             # Pass the approval proocess to next approver
#             else:
             
#                 request_approver = EmployeeLeaveRequest()
#                 request_approver.employee_leave_app_id = leave_application_details._id
#                 request_approver.company_id = leave_application_details.company_id.id
#                 next_approval_level = int(current_approval_level)+1
               
#                 department = leave_application_details.company_approver.department_name
#                 approver = EmployeeLeaveApprover.objects(employee_approval_level=str(next_approval_level),department_name=department,company_id=leave_application_details.company_id.id).first()
               
#                 if approver:
#                     request_approver.approver_id = approver._id

#                 request_approver.save() 
                
#                 leave_request_details.update(request_status="approved",approved_on=datetime.now())
               
#                 leave_application_details.update(current_approval_level=str(next_approval_level),current_aprrover=request_approver._id,add_to_set__approver_list=request_approver._id)

#             msg =  json.dumps({'status':'success'})
#             msghtml = json.loads(msg)
#             return msghtml
        
#         msg =  json.dumps({'status':'success'})
#         msghtml = json.loads(msg)
#         return msghtml
#     else:
#         msg =  json.dumps({"status":"success"})
#         msghtml = json.loads(msg)
#         return msghtml    



def process_single_employee(company_id, employee_id, leave_policies=None):
    # Fetch the specific company details
    company_detail = CompanyDetails.objects(user_id=company_id).first()
    if not company_detail:
        print("Company not found!")
        return None  # Return None if company is not found

    # Fetch the specific employee details
    employee = EmployeeDetails.objects(_id=employee_id).first()
    if not employee:
        print("Employee not found!")
        return None  # Return None if employee is not found

    # Use the provided leave policies or fetch them from the company
    if leave_policies is None:
        leave_policies = [
            leave_policy for leave_policy in company_detail.leave_policies
            if leave_policy.allowance_type == 'annual'
        ]

    updated_balances = []

    # Fetch the employee's leave policies from the database
    employee_leave_policies = EmployeeLeavePolicies.objects(
        company_id=company_id,
        employee_details_id=employee_id
    )
    emp_leave_policy_id = None
    policy_balance = 0
    for policy in employee_leave_policies:
        if policy._id == objects(leave_policies):
            emp_leave_policy_id = str(policy._id)
            policy_balance = policy.balance
            break

    # Process leave policies for the employee
    for leave_policy in leave_policies:
        new_leave_balance = 30
        before_adjustment = 0

        # Convert leave_policy to ObjectId if necessary (only if it's not already an ObjectId)
        if isinstance(leave_policy, str):
            leave_policy = ObjectId(leave_policy)

        # Find matching policy in employee's leave policies
        emp_leave_policy_id = None
        policy_balance = 0
        for policy in employee_leave_policies:
            if policy.leave_policy_id._id == leave_policies:
                emp_leave_policy_id = str(policy._id)
                policy_balance = policy.balance
                break

        # If policy is found, process it
        if emp_leave_policy_id:
            before_adjustment = policy_balance
            new_leave_balance = float(new_leave_balance)
            print(f"Leave Policy: {leave_policy.leave_policy_name}")
            print("New leave balance:", new_leave_balance)

            # Calculate the adjustment comment for yearly reset
            previous_year = (datetime.now() - timedelta(days=30)).strftime("%Y")
            adjustment_comment = f'Yearly Reset of the Leave for Year {previous_year}'

            # Create a new leave adjustment record
            new_data = EmployeeLeaveAdjustment(
                company_id=company_id,
                employee_details_id=employee._id,
                employee_leave_pol_id=emp_leave_policy_id,
                adjustment_type='increment',
                adjustment_days=str(new_leave_balance),
                adjustment_comment=adjustment_comment,
                before_adjustment=str(before_adjustment),
                after_adjustment=str(new_leave_balance)
            )
            status = new_data.save()

            # Update the employee leave policy
            employee_leave_policy = EmployeeLeavePolicies.objects(id=emp_leave_policy_id).first()
            if employee_leave_policy:
                employee_leave_policy.update(
                    push__employee_leave_adjustments=new_data._id,
                    balance=new_leave_balance
                )

                # Store the updated leave balance for this policy
                updated_balances.append({
                    "leave_policy_id": leave_policy._id,
                    "leave_policy_name": leave_policy.leave_policy_name,
                    "new_balance": new_leave_balance
                })

        else:
            print(f"No matching leave policy found for {leave_policy.leave_policy_name}.")

    # Return all updated balances for the employee
    return updated_balances

@employee.route('/rejectleaverequest', methods=['POST'])
def reject_leave_request():
    leave_request_id = request.form.get('leave_request_id')
    leave_reject_reason = request.form.get('leave_reject_reason')
    if leave_request_id:
        leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
        # check if the data exist or not 
        if leave_request_details:
            leave_application_details = EmployeeLeaveApplication.objects(_id=leave_request_details.employee_leave_app_id._id).first()
            # Change the status of LeaveRequest by the previous/Current approver
            leave_request_details.update(request_status="rejected",rejected_on=datetime.now())
            # Change the current_approval_level of LeaveApplication and Current approver
            leave_application_details.update(current_approval_level="",leave_status="rejected",rejected_by=leave_request_details.approver_id.employee_details_id.first_name,leave_reject_reason=leave_reject_reason,rejected_on=datetime.now())

            # .................send an email to the leave applicant about approval ...........
            approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name

            email_template = 'email/leave_approved.html'
            data = {}

            data['employee_details_id'] = leave_application_details.employee_details_id
            data['type'] = leave_application_details.employee_leave_policy.leave_policy_id.leave_type
            data['start_date'] = leave_application_details.leave_from.strftime('%Y-%m-%d')
            data['end_date'] = leave_application_details.leave_till.strftime('%Y-%m-%d')
            data['no_of_days'] = leave_application_details.no_of_days
            data['is_modified'] = 'No'
            data['aprover_remarks'] = leave_reject_reason
            data['approver_name'] = approver
            data['status'] = 'rejected'
            data['receiver_email'] = leave_application_details.employee_details_id.personal_email


            send_email(email_template, data)

            #.................end of sending email.............................................
                
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml    
  
@employee.route('/deleteleaveapplication', methods=['POST'])
def delete_leave_application():
    leave_application_id = request.form.get('leave_application_id')
    if leave_application_id:
        leave_request_details = EmployeeLeaveRequest.objects(employee_leave_app_id=ObjectId(leave_application_id)).delete()
        
        leave_application_details = EmployeeLeaveApplication.objects(_id=ObjectId(leave_application_id)).delete()
        # Change the status of LeaveRequest by the previous/Current approver
        # Change the current_approval_level of LeaveApplication and Current approver
        if leave_application_details and leave_request_details:
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml   

def calculate_late_details(employee_check_in_time,employee_details,attendance_date):
    
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
    if "AM" in work_timings.office_end_at:
        # Checkout without Grace
        existing_schedule_end_time_str = work_timings.office_end_at #'9:00 AM'
        existing_schedule_end_time = datetime.strptime(existing_schedule_end_time_str, '%I:%M %p')
        # Get the current date and time
        current_check_out_date = datetime.combine(attendance_date.date()+timedelta(days=1),existing_schedule_end_time.time())

        # Add 4 hours to the existing schedule end time
        new_end_time = existing_schedule_end_time + timedelta(hours=4)

        # Combine the new end time with the current date to get the final datetime
        final_datetime = datetime(current_check_out_date.year,current_check_out_date.month,current_check_out_date.day,new_end_time.hour,new_end_time.minute,new_end_time.second,new_end_time.microsecond)
    else:
        final_datetime = ""
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
        
    return (int(late_by_minutes),final_datetime)



def calculate_early_departure_details(employee_check_out_time,employee_details,attendance_date):
    
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

def calculate_overtime_details(employee_check_out_time,employee_check_in_time,employee_details,attendance_date):
    
    # Todo: Check the Existing Scheduled Work Timings or get the default Work Timings
    has_overtime,ot_by_minutes,ot_policy_multiplier,ot_type,ot_policy_on = False,0,'','',''
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
    
    is_holiday = CompanyHolidays.objects(company_id=employee_details.company_id,occasion_date=attendance_date,is_working_day=False).first()
    is_non_working_day = True if (is_holiday or work_timings.is_day_off) else False
    overtime_type='extended'
    if is_non_working_day:
        overtime_type = 'holiday' if is_holiday else 'dayoff'
    
    office_start_at = work_timings.office_start_at 
    office_end_at = work_timings.office_end_at   
    default_checkout_time =  datetime.strptime(office_end_at, '%I:%M %p')
    default_checkin_time = datetime.strptime(office_start_at, '%I:%M %p')   
    

    # This Condition will check if the checkout time is next day of the checkin time 
    if "AM" in office_end_at:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date()+timedelta(days=1),default_checkout_time.time())
        # Checkin without Grace
        current_check_in_date = datetime.combine(attendance_date.date(),default_checkin_time.time())
    else:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date(),default_checkout_time.time())
        # Checkin without Grace
        current_check_in_date = datetime.combine(attendance_date.date(),default_checkin_time.time())
    
    total_hrs_worked = employee_check_out_time-employee_check_in_time
    total_working_hour = current_check_out_date - current_check_in_date
    
    overtime_hours = total_hrs_worked-total_working_hour
    overtime_minutes = overtime_hours.total_seconds()/60 if overtime_hours else 0
    minimum_ot = int(work_timings.minimum_ot) if work_timings.minimum_ot else 0      
     
    if overtime_minutes >= minimum_ot:
        overtime_policy = CompanyOvertimePolicies.objects(company_id=employee_details.company_id,ot_policy_name=overtime_type).first()
        if overtime_policy:
            has_overtime = True
            ot_by_minutes = overtime_minutes
            ot_policy_multiplier = overtime_policy.ot_policy_multiplier
            ot_type = overtime_policy.ot_policy_name
            ot_policy_on = overtime_policy.ot_policy_on
            
    return has_overtime,int(ot_by_minutes),ot_policy_multiplier,ot_type,ot_policy_on

def create_time_request(company_id,attendance_id,department,request_type):
    # Todo: Check for the time approver if exist create record else return false; 
    company_time_approver = CompanyTimeApprovers.objects(company_id=company_id,department_name=department).first()
    if not company_time_approver:
        company_time_approver = CompanyTimeApprovers.objects(company_id=company_id,department_name='all').first()
    if company_time_approver:
        employee_time_request = EmployeeTimeRequest()
        employee_time_request.company_id = company_id
        employee_time_request.attendance_id = attendance_id
        employee_time_request.approver_id = company_time_approver._id
        employee_time_request.request_type = request_type
        
        employee_time_request.save()
        
    return True

@employee.route('/timeapprovals')
@login_required
@roles_accepted('employee')
def time_approvals():
    # employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    # Get all the aprrovers id 
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    approvers = CompanyTimeApprovers.objects(approver=employee_details._id).only('_id')
    
    if approvers:
    # Look for application request based on approver ids with pending status
        data = []
        for item in approvers:
            data.append(item._id)
        time_requests = EmployeeTimeRequest.objects(approver_id__in=data)
            
        return render_template('employee/time_approval.html',time_requests=time_requests)
    
@employee.route('/approvetimerequest', methods=['POST'])
def approve_time_request():
    time_request_id = request.form.get('time_request_id')
    has_edited = request.form.get('has_edited')
    edit_approval_time = request.form.get('edit_approve_time')
    approval_type = request.form.get('approval_type')
    
    if time_request_id:
        time_request_details = EmployeeTimeRequest.objects(_id=ObjectId(time_request_id)).first()
        # check if the data exist or not 
        if time_request_details:
            attendance_details = EmployeeAttendance.objects(_id=time_request_details.attendance_id._id).first()
            # Change the status of TimeRequest by the approver
            time_request_details.update(request_status="approved",approved_on=datetime.now())
            # Change the approval_status of timeApplication         
            if time_request_details.request_type == 'early':
                approved_minutes = edit_approval_time if has_edited else attendance_details.early_by_minutes
                status = attendance_details.update(early_approval_status=True,approved_early_minutes=approved_minutes)
                
            elif time_request_details.request_type == 'late':
                approved_minutes = edit_approval_time if has_edited else attendance_details.late_by_minutes
                status = attendance_details.update(late_approval_status=True,approved_late_minutes=approved_minutes)
                
            elif time_request_details.request_type == 'overtime':
                approved_minutes = edit_approval_time if has_edited else attendance_details.ot_by_minutes
                status = attendance_details.update(ot_approval_status=True,approved_ot_minutes=approved_minutes)
            
            # Todo: Calculate and generate an adjustment based on request Type; Check if the employee is Full-time if yes create an adjustment
            if status and time_request_details.attendance_id.employee_details_id.employee_company_details.type == '0':
               if approval_type == 'timeoff':
                   generate_timeoff_on_approval(time_request_details._id) 
               else:
                   generate_adjustment_on_approval(time_request_details._id) 
             
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml  
        
@employee.route('/rejecttimerequest', methods=['POST'])
def reject_time_request():
    time_request_id = request.form.get('time_request_id')
    time_reject_reason = request.form.get('time_reject_reason')

    if time_request_id:
        time_request_details = EmployeeTimeRequest.objects(_id=ObjectId(time_request_id)).first()
        # check if the data exist or not 
        if time_request_details:
            time_request_details.update(request_status="rejected",rejected_on=datetime.now(),time_reject_reason=time_reject_reason)
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml   
    
def generate_adjustment_on_approval(time_request_details_id):
    # Todo: Check if the Adjustment reasons are already added else add; for late and early create Deducution Adjustment Reason; for OT Create Addition Adjustment Reason; 
    # Todo: Calculate the hourly rate of the employee
    # Wages Details
    time_request_details = EmployeeTimeRequest.objects(_id=ObjectId(time_request_details_id)).first()
    employee_data = EmployeeDetails.objects(_id=time_request_details.attendance_id.employee_details_id._id).first()
    monthly_salary = employee_data.employee_company_details.total_salary if employee_data.employee_company_details.total_salary else 0
    basic_monthly_salary = employee_data.employee_company_details.basic_salary if employee_data.employee_company_details.basic_salary else 0
    # employee_attendance.basic_monthly_salary = basic_monthly_salary
    current_month = datetime(time_request_details.attendance_id.attendance_date.year, time_request_details.attendance_id.attendance_date.month, 1).strftime('%B')
    calendar_working_days = CompanyDetails.objects(user_id=time_request_details.company_id.id).only('working_days','daily_working_hour').first()
    # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
    working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))

    no_of_working_days = int(working_days[0]['days']) if working_days else 30 # By Default Set to 30 Days
    daily_salary = int(monthly_salary)/no_of_working_days # Get the no of working days in current monthly calendar
    daily_basic_salary = int(basic_monthly_salary)/no_of_working_days # Get the no of working days in current monthly calendar
    # Todo: Check for the schedule in order to get total working hours of employee or else get default working hour from WTs
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=time_request_details.attendance_id.employee_details_id._id,schedule_from=time_request_details.attendance_id.attendance_date).first()
    if existing_schedule:
        total_working_hours = existing_schedule.work_timings.total_working_hour
    else:
          # Default Work Timings
        if not employee_data.employee_company_details.work_timing:
            default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,is_default=True).first() 
        else:
            default_work_timings = employee_data.employee_company_details.work_timing
            
        # default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,is_default=True).first() 
        total_working_hours = default_work_timings.total_working_hour
    
    total_working_hour = datetime.strptime(total_working_hours, '%I:%M:%S')
    working_hour= (total_working_hour.hour*60+total_working_hour.minute)/60
        
    daily_working_hour = working_hour if working_hour else calendar_working_days.daily_working_hour # Default Set to daily_working_hour
    hourly_rate = float(daily_salary)/float(daily_working_hour)
    basic_hourly_rate = float(daily_basic_salary)/float(daily_working_hour)
    # Wages Details End
    
    adjustment_amount = 0
    start_of_month = time_request_details.attendance_id.attendance_date.replace(day=1,minute=0, hour=0, second=0,microsecond=0)

    if time_request_details.request_type == 'early' or time_request_details.request_type == 'late':
        if time_request_details.request_type == 'early':
            # Todo: Check if the Deduction Reason Exist or else Create a new;
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,adjustment_reason="Early Departure").first()
            if not adjustment_reason:
               adjustment_reason = create_adjustment_reason(time_request_details.company_id.id,"Early Departure","deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            adjustment_amount = (hourly_rate/60)*float(time_request_details.attendance_id.approved_early_minutes)
            # adjustment_amount = round((hourly_rate/60)*float(time_request_details.attendance_id.approved_early_minutes),2)
            
        elif time_request_details.request_type == 'late':
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,adjustment_reason="Late Arrival").first()
            if not adjustment_reason:
               adjustment_reason = create_adjustment_reason(time_request_details.company_id.id,"Late Arrival","deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            adjustment_amount =  (hourly_rate/60)*float(time_request_details.attendance_id.approved_late_minutes)
            # adjustment_amount =  round((hourly_rate/60)*float(time_request_details.attendance_id.approved_late_minutes),2)
            
        
    elif time_request_details.request_type == 'overtime':
        adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,adjustment_reason="Extra Hours").first()
        if not adjustment_reason:
           adjustment_reason = create_adjustment_reason(time_request_details.company_id.id,"Extra Hours","addition")
       
        if(time_request_details.attendance_id.ot_policy_on == 'basic_salary'):
            adjustment_amount = ((basic_hourly_rate*float(time_request_details.attendance_id.ot_policy_multiplier))/60)*int(time_request_details.attendance_id.approved_ot_minutes)
        else:
            adjustment_amount = ((hourly_rate*float(time_request_details.attendance_id.ot_policy_multiplier))/60)*int(time_request_details.attendance_id.approved_ot_minutes)
        
     # Todo: Create a CPA Record   
    if adjustment_amount>0:
        new_data = CompanyPayrollAdjustment(
                                company_id=time_request_details.company_id.id,
                                employee_details_id=time_request_details.attendance_id.employee_details_id._id,
                                adjustment_reason_id=adjustment_reason._id,
                                adjustment_type=adjustment_reason.adjustment_type,
                                adjustment_amount=str(adjustment_amount),
                                adjustment_on=start_of_month,
                                adjustment_month_on_payroll=start_of_month.strftime('%B'),
                                adjustment_year_on_payroll= start_of_month.year)
        status = new_data.save()  
          
    return True

def generate_timeoff_on_approval(time_request_details_id):
    # Todo: Check if the Adjustment reasons are already added else add; for late and early create Deducution Adjustment Reason; for OT Create Addition Adjustment Reason; 
    # Todo: Calculate the hourly rate of the employee
    # Wages Details
    time_request_details = EmployeeTimeRequest.objects(_id=ObjectId(time_request_details_id)).first()
    employee_data = EmployeeDetails.objects(_id=time_request_details.attendance_id.employee_details_id._id).first()
    # employee_attendance.basic_monthly_salary = basic_monthly_salary
    calendar_working_days = CompanyDetails.objects(user_id=time_request_details.company_id.id).only('working_days','daily_working_hour').first()
    # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
    # Todo: Check for the schedule in order to get total working hours of employee or else get default working hour from WTs
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=time_request_details.attendance_id.employee_details_id._id,schedule_from=time_request_details.attendance_id.attendance_date).first()
    if existing_schedule:
        total_working_hours = existing_schedule.work_timings.total_working_hour
    else:
          # Default Work Timings
        if not employee_data.employee_company_details.work_timing:
            default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,is_default=True).first() 
        else:
            default_work_timings = employee_data.employee_company_details.work_timing
            
        # default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,is_default=True).first() 
        
        total_working_hours = default_work_timings.total_working_hour
    
    total_working_hour = datetime.strptime(total_working_hours, '%I:%M:%S')
    
    calender_working_hour = float(calendar_working_days.daily_working_hour)*60
    # Convert In minutes
    working_hour= (total_working_hour.hour*60+total_working_hour.minute) 
    # Daily Working Hour in Minutes 
    
    daily_working_hour = working_hour if working_hour else calender_working_hour # Default Set to daily_working_hour
    
    time_off_balance = 0.0
    start_of_month = time_request_details.attendance_id.attendance_date.replace(day=1,minute=0, hour=0, second=0,microsecond=0)

    if time_request_details.request_type == 'early' or time_request_details.request_type == 'late':
        if time_request_details.request_type == 'early':
            # Todo: Check if the Deduction Reason Exist or else Create a new;
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,adjustment_reason="Early Departure").first()
            if not adjustment_reason:
               adjustment_reason = create_adjustment_reason(time_request_details.company_id.id,"Early Departure","deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            # adjustment_amount = (hourly_rate/60)*float(time_request_details.attendance_id.approved_early_minutes)
            extra_time = int(time_request_details.attendance_id.approved_early_minutes)
            time_off_balance =  extra_time/daily_working_hour
            
            # adjustment_amount = round((hourly_rate/60)*float(time_request_details.attendance_id.approved_early_minutes),2)
            
        elif time_request_details.request_type == 'late':
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,adjustment_reason="Late Arrival").first()
            if not adjustment_reason:
               adjustment_reason = create_adjustment_reason(time_request_details.company_id.id,"Late Arrival","deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            # adjustment_amount =  (hourly_rate/60)*float(time_request_details.attendance_id.approved_late_minutes)
            extra_time = int(time_request_details.attendance_id.approved_late_minutes)
            time_off_balance =  extra_time/daily_working_hour

            # adjustment_amount =  round((hourly_rate/60)*float(time_request_details.attendance_id.approved_late_minutes),2)
        
    elif time_request_details.request_type == 'overtime':
        adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,adjustment_reason="Extra Hours").first()
        if not adjustment_reason:
           adjustment_reason = create_adjustment_reason(time_request_details.company_id.id,"Extra Hours","addition")
           
        extra_time = int(time_request_details.attendance_id.approved_ot_minutes)
        time_off_balance =  extra_time/daily_working_hour
     
     # Todo: Create a CPA Record   
    if time_off_balance>0:
        new_data = CompanyTimeOffAdjustment(
                                company_id=time_request_details.company_id.id,
                                employee_details_id=time_request_details.attendance_id.employee_details_id._id,
                                adjustment_reason_id=adjustment_reason._id,
                                adjustment_type='increment' if adjustment_reason.adjustment_type =="addition" else 'decrement' ,
                                time_request_details_id = time_request_details_id,
                                time_off_balance=float(time_off_balance),
                                approved_minutes=extra_time,
                                daily_working_hour=daily_working_hour
                                )
        status = new_data.save()  
          
    return True

def create_adjustment_reason(company_id,adjustement_reason,adjustment_type):
    # Todo: Check for the time approver if exist create record else return false; 
    new_adjustment_reason = CompanyAdjustmentReasons()
    new_adjustment_reason.company_id = company_id
    new_adjustment_reason.adjustment_reason = adjustement_reason
    new_adjustment_reason.adjustment_type = adjustment_type
    new_adjustment_reason.save()
    update_details = CompanyDetails.objects(user_id=company_id).update(push__adjustment_reasons=new_adjustment_reason.id)
        
    return new_adjustment_reason

@employee.route('/request/extratime/', methods=['POST'])
def request_extratime():
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        employee_details_id = request.form.get('employee_details_id')
        attendance_id = request.form.get('employee_attendance_id')
        if employee_details_id:
            employee_details = EmployeeDetails.objects(_id=ObjectId(employee_details_id)).only('employee_company_details').first()
            time_request = create_time_request(ObjectId(company_id),ObjectId(attendance_id),employee_details.employee_company_details.department,'overtime')
        if time_request:
            msg =  json.dumps({"status":"success"})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg =  json.dumps({"status":"failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))
    
@employee.route('/attendancehistory',methods=["GET","POST"])
@login_required
@roles_accepted('employee')
def attendance_history():
    if request.method=="POST":
        attendance_from = request.form.get('attendance_date_from')
        attendance_to = request.form.get('attendance_date_to')

        start_of_month = datetime. strptime(attendance_from, '%d/%m/%Y')
        end_of_the_month = datetime. strptime(attendance_to, '%d/%m/%Y')

        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        monthly_att_data =EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).order_by('-attendance_date')
    
    else:    
        start_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
        end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        monthly_att_data =EmployeeAttendance.objects(company_id=ObjectId( employee_details.company_id),employee_details_id=ObjectId(employee_details._id),attendance_date__gte=start_of_month,attendance_date__lte=end_of_the_month).order_by('-attendance_date')
    
    return render_template('employee/attendance_history.html',employee_details=employee_details,attendance_history=monthly_att_data,start=start_of_month,end=end_of_the_month)

@employee.route('/reimbursement')
@login_required
@roles_accepted('employee')
def reimbursement():
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    reimbursement_data = EmployeeReimbursement.objects(employee_details_id=employee_details._id)
    return render_template('employee/reimbursement.html',employee_details=employee_details,reimbursement_data=reimbursement_data)

@employee.route('/create/reimbursement', methods=['GET','POST'])
@roles_accepted('admin','company','expensemanager')
@login_required
def create_reimbursement():
    company_details = CompanyDetails.objects(user_id=current_user.id).only('employees','adjustment_reasons','company_name').first()
    company_id = current_user.id
    if not company_details: 
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        company_details = CompanyDetails.objects(user_id=employee_details.company_id).only('adjustment_reasons','company_name').first()  
        company_id = employee_details.company_id
        
    if request.method == 'POST':
        flag = False
        # employee_details_id = current_user.id
        # start_of_month = datetime. strptime(request.form.get('selected_month'), '%Y-%m-%d')  if request.form.get('selected_month') else datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        total_adjustments = len(request.form.getlist("adjustment_reason[]"))
        if total_adjustments > 0:
            adjustment_reason_list = request.form.getlist('adjustment_reason[]')
            adjustment_on_list = request.form.getlist('reimburesement_of[]')
            adjustment_amount_list = request.form.getlist('adjustment_amount[]')
            adjustment_document_list = request.files.getlist('adjustment_document[]')

            for item in range(0,total_adjustments):
                adjustment_reason = adjustment_reason_list[item]
                adjustment_on = datetime. strptime(adjustment_on_list[item], '%d/%m/%Y')
                adjustment_amount = adjustment_amount_list[item]
                adjustment_document = adjustment_document_list[item]
                
                if adjustment_reason:
                    flag = True
                    adjustment_reason_details = CompanyAdjustmentReasons.objects(_id=ObjectId(adjustment_reason)).first()
                    if adjustment_reason_details:
                        # Create a new record for payroll adjustment
                        # todo: Check if the payment is recurring; if recurring then create all the records of the terms with their respective amounts
                        adjustment_document_name = ""
                        if adjustment_document:
                            adjustment_document_name = upload_adjustment_document(adjustment_document,company_details.company_name)    
                            
                        new_data = EmployeeReimbursement(
                                company_id = company_id,
                                employee_details_id = employee_details._id,
                                adjustment_reason_id = adjustment_reason_details._id,
                                adjustment_type = adjustment_reason_details.adjustment_type,
                                reimbursement_amount = adjustment_amount,
                                reimbursement_document = adjustment_document_name,
                                reimbursement_on = adjustment_on
                        )
                        status = new_data.save()
            if flag:
                flash('Reimbursement Created Successfully!', 'success')
                return redirect(url_for('employee.reimbursement'))
            else:
                flash('Something went Wrong. Please try again!', 'danger')
                return redirect(url_for('employee.reimbursement'))
        
    else:
        # company_details = CompanyDetails.objects(user_id=current_user.id).only('employees','adjustment_reasons').first()  
        start_of_month = datetime.today().replace(day=1,minute=0, hour=0, second=0,microsecond=0)
        return render_template('employee/create_reimbursement.html',company_details=company_details,start_of_month=start_of_month)
    
def upload_adjustment_document(file,company_name):
    fname=''
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = str.lower(os.path.splitext(filename)[1])
        fname = fn+str(uuid.uuid4())+file_ext
        if file_ext not in current_app.config['UPLOAD_REIMBURSEMENT_DOCUMENT_EXTENSIONS']: 
            flash('Please insert document with desired format!')
            return redirect(url_for('employee.reimbursement'))
        file_path = current_app.config['UPLOAD_DOCUMENT_FOLDER'] + company_name.strip()+'/adjustments/'
        # if not os.path.exists(app.config['UPLOAD_DOCUMENT_FOLDER']):
        #     os.makedirs(app.config['UPLOAD_DOCUMENT_FOLDER'])
        # file.save(os.path.join(app.config['UPLOAD_DOCUMENT_FOLDER'], fname))
        if not os.path.exists(file_path):
                os.makedirs(file_path)
        file.save(os.path.join(file_path, fname))
    return fname;

# @celery.task(track_started = True,result_extended=True,name='Leave-Approval-Email')
# def send_leave_approval_email():
#     app = create_app()  # create the Flask app
#     mail = Mail(current_app)  # initialize Flask-Mail with default email server details

#     # Get Leave application details
#     leave_application_details = EmployeeLeaveApplication.objects(_id=ObjectId(leave_application_id)).first()
#     if leave_application_details:
    
#         company_details = CompanyDetails.objects(user_id=leave_application_details.company_id).only('email_config').first()
#         if company_details.email_config:
#             mail_server = company_details.email_config.company_email_host
#             mail_port = company_details.email_config.company_email_port
#             mail_use_tls = company_details.email_config.company_email_tls
#             mail_username = company_details.email_config.company_email_user
#             mail_password = company_details.email_config.company_email_password
        
#             current_app.config.update(
#             MAIL_SERVER=mail_server,
#             MAIL_PORT=mail_port,
#             MAIL_USE_TLS=mail_use_tls,
#             MAIL_USERNAME=mail_username,
#             MAIL_PASSWORD=mail_password
#             )
#             mail.init_app(current_app)
#         else:
#             mail_server = app.config['MAIL_SERVER']
#             mail_port = app.config['MAIL_PORT']
#             mail_use_tls = app.config['MAIL_USE_TLS']
#             mail_username = app.config['MAIL_USERNAME']
#             mail_password = app.config['MAIL_PASSWORD']
#             mail.init_app(app)

#         with current_app.app_context():
#             receiver_email = leave_application_details.current_aprrover.approver_id.employee_details_id.user_id.email
#             html = render_template('email/leave_approval.html', leave_application_details=leave_application_details)
#             msg = Message('Leave Application Approval Required! | Cubes HRMS', sender = ("Cubes HRMS",app.config['MAIL_USERNAME']), recipients = [receiver_email])
#             msg.html = html
#             mail.send(msg)
#             return True

# @employee.route('/superapproveleaverequest', methods=['POST'])
# def super_approve_leave_request():
#     leave_request_id = request.form.get('leave_request_id')
#     comment = request.form.get('approver_comment')
#     new_leave_till = None
#     new_leave_from = None

#     has_edited = request.form.get('edit_leave_date')
#     if has_edited:
#         new_leave_range = request.form.get('daterange').split(' - ')
#         new_leave_from = datetime.strptime(new_leave_range[0], '%d/%m/%Y')
#         new_leave_till = datetime.strptime(new_leave_range[1], '%d/%m/%Y')

#         new_no_of_days = request.form.get('no_of_days')
#         delta = new_leave_till - new_leave_from
#         no_of_days = delta.days

#     if leave_request_id:
#         leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
#         # check if the data exist or not 
#         if leave_request_details:
#             leave_application_details = EmployeeLeaveApplication.objects(
#                 _id=leave_request_details.employee_leave_app_id._id).first()
#             if comment:
#                 super_employee = EmployeeDetails.objects(user_id=current_user.id).first()
#                 super_approver_details = SuperLeaveApprovers.objects(employee_details_id=super_employee._id).first()
#                 leave_application_details.update(is_super_approved=True, super_approver_comment=comment,
#                                                  super_approver=super_approver_details._id)
#             if has_edited:
#                 leave_application_details.update(leave_from=new_leave_from, leave_till=new_leave_till,
#                                                  no_of_days=new_no_of_days)
#             current_leave_balance = leave_application_details.employee_leave_policy.balance
#             asking_leave_days = int(leave_application_details.no_of_days)
#             current_year = datetime.now().year
#             created_at=datetime.now()
#             if leave_application_details:
#                 asked_leave_from = leave_application_details.asked_leave_from
#                 asked_leave_till = leave_application_details.asked_leave_till
#                 if asked_leave_till.year == current_year:
#                     created_at= datetime.now()
#                 else:
#                     cutoff_date = datetime(2025, 1, 1)

#                     # Emplyolee_leave_data = EmployeeLeaveAdjustment.objects(
#                     #     employee_details_id=leave_application_details.employee_details_id,
#                     #     employee_leave_pol_id=leave_application_details.employee_leave_pol_id,
#                     #     created_at__lt=cutoff_date 
#                     # ).order_by('-created_at').first()
#                     # current_leave_balance = Emplyolee_leave_data.employee_leave_policy.balance
#                     # asking_leave_days = int(leave_application_details.no_of_days)
#                     # created_at= leave_application_details.asked_leave_till

#             if (current_leave_balance >= asking_leave_days):  #Todo: This condition need to be checked
#                 leave_request_details.update(request_status="approved", approved_on=datetime.now(), comment=comment)
#                 leave_policy_details = EmployeeLeavePolicies.objects(
#                     _id=leave_application_details.employee_leave_policy._id).first()
#                 adj_days = str(asking_leave_days if not has_edited else new_no_of_days)
#                 after_adj = str(current_leave_balance - float(adj_days))

#                 new_data = EmployeeLeaveAdjustment(
#                     company_id=leave_policy_details.company_id,
#                     employee_details_id=leave_policy_details.employee_details_id,
#                     employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
#                     adjustment_type='decrement',
#                     adjustment_days=adj_days,
#                     adjustment_comment=str(comment),
#                     before_adjustment=str(current_leave_balance),
#                     after_adjustment=after_adj,
#                     created_at=created_at
#                 )
#                 status = new_data.save()

#                 leave_application_details.update(leave_adjustment=new_data._id)
#                 leave_application_details.save()

#                 new_balance = current_leave_balance - asking_leave_days
#                 if leave_policy_details:
#                     leave_policy_details.update(balance=new_balance)
#                 leave_application_details.update(current_approval_level="", leave_status="approved",
#                                                  balance_before_approval=current_leave_balance,
#                                                  balance_after_approval=new_balance, approved_on=datetime.now())
#                 work_timings = WorkTimings.objects(is_day_off=True,
#                                                    company_id=leave_application_details.company_id.id).first()
#                 if not work_timings:
           
#                     work_timings = WorkTimings(name="Day Off",
#                                                schedule_color='#808080',
#                                                is_day_off=True,
#                                                office_start_at='',
#                                                office_end_at='',
#                                                late_arrival__later_than='',
#                                                early_departure_earliar_than='',
#                                                consider_absent_after='',
#                                                week_offs='',
#                                                company_id=leave_application_details.company_id.id
#                                                )
#                     work_timings.save()
#                     update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(
#                         push__worktimings=work_timings._id)
#                 approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name
 
#                 start_date = leave_application_details.leave_from
#                 end_date = leave_application_details.leave_till
#                 while start_date <= end_date:
#                     is_already_scheduled = CompanyEmployeeSchedule.objects(work_timings=work_timings._id,
#                                                                            employee_id=leave_application_details.employee_details_id._id,
#                                                                            schedule_from=start_date,
#                                                                            schedule_till=start_date).first()
#                     if not is_already_scheduled:
#                         employee_schedule = CompanyEmployeeSchedule(company_id=leave_application_details.company_id.id,
#                                                                     work_timings=work_timings._id,
#                                                                     employee_id=leave_application_details.employee_details_id._id,
#                                                                     schedule_from=start_date,
#                                                                     schedule_till=start_date,
#                                                                     allow_outside_checkin=False,
#                                                                     is_leave=True,
#                                                                     leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                                                                     )
#                         employee_schedule.save()
#                         update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(
#                             push__employee_schedules=employee_schedule._id)
#                         # Add attendance Data as well
#                         employee_attendance = EmployeeAttendance()
#                         employee_attendance.employee_id = leave_application_details.employee_details_id.employee_company_details.employee_id
#                         employee_attendance.employee_details_id = leave_application_details.employee_details_id._id
#                         employee_attendance.attendance_date = start_date
#                         employee_attendance.company_id = leave_application_details.company_id.id
#                         employee_attendance.leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                         employee_attendance.attendance_status = "absent"
#                         employee_attendance.save()
#                     # start_date = start_date + timedelta(days=1)
#                     # todo: Create an adjustment record if the leave policy type is unpaid
#                     if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
#                         start_of_month = start_date.replace(day=1)
#                         nxt_mnth = start_date.replace(day=28) + timedelta(days=4)
#                         # subtracting the days from next month date to
#                         # get last date of current Month
#                         end_of_the_month = nxt_mnth - timedelta(days=nxt_mnth.day)
#                         # Todo: Create a adjustment record by deducting the off day amount
#                         # Check if the adjustment reason is defined if not create a adjustment reason for Unpaid Leaves
#                         adjustment_reason = CompanyAdjustmentReasons.objects(
#                             company_id=leave_application_details.company_id.id,
#                             adjustment_reason="Unpaid Leaves").first()
#                         if not adjustment_reason:
#                             adjustment_reason = create_adjustment_reason(leave_application_details.company_id.id,
#                                                                          "Unpaid Leaves", "deduction")

#                         # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
#                         total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary

#                         current_month = start_date.strftime('%B')

#                         calendar_working_days = CompanyDetails.objects(
#                             user_id=leave_application_details.company_id.id).only('working_days').first()
#                         # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
#                         working_days = list(
#                             filter(lambda x: x['month'] == current_month.lower(), calendar_working_days.working_days))

#                         no_of_working_days = int(working_days[0][
#                                                      'days']) if working_days else end_of_the_month.days()  # By Default Set to 30 Days

#                         adjustment_amount = round(int(total_salary) / no_of_working_days, 0)

#                         adjustment_exists = CompanyPayrollAdjustment.objects(
#                             company_id=leave_application_details.company_id.id,
#                             employee_details_id=leave_application_details.employee_details_id._id,
#                             adjustment_reason_id=adjustment_reason._id,
#                             attendance_date=start_date).first()
#                         if adjustment_exists:
#                             adjustment_exists.delete()

#                         new_data = CompanyPayrollAdjustment(
#                             company_id=leave_application_details.company_id.id,
#                             employee_details_id=leave_application_details.employee_details_id._id,
#                             adjustment_reason_id=adjustment_reason._id,
#                             adjustment_type=adjustment_reason.adjustment_type,
#                             adjustment_amount=str(adjustment_amount),
#                             adjustment_on=start_of_month,
#                             adjustment_month_on_payroll=start_of_month.strftime('%B'),
#                             adjustment_year_on_payroll=start_of_month.year,
#                             attendance_date=start_date,
#                         )
#                         new_data.save()
#                     start_date = start_date + timedelta(days=1)
#             else:
#                 try:
                       
#                         # Calculate difference between requested leave days and current balance
#                         difference = asking_leave_days - current_leave_balance

#                         # Approve the leave request
#                         leave_request_details.update(
#                             request_status="approved",
#                             approved_on=datetime.now(),
#                             comment=comment
#                         )

#                         # Deduct leave balance and update leave policy details
#                         leave_policy_details = EmployeeLeavePolicies.objects(
#                             _id=leave_application_details.employee_leave_policy._id
#                         ).first()

#                         if leave_policy_details:
#                             leave_policy_details.update(balance=0)  # Set balance to 0 after deduction

#                         # Safely extract employee_id and company_id
#                         employee_id = leave_application_details.employee_details_id._id
#                         company_id = leave_application_details.company_id.id

#                         # Ensure ObjectId type for IDs
#                         company_id = ObjectId(company_id) if not isinstance(company_id, ObjectId) else company_id
#                         employee_id = ObjectId(employee_id) if not isinstance(employee_id, ObjectId) else employee_id

#                         # Query for leave policies
#                         leave_policies = EmployeeLeavePolicies.objects(
#                             company_id=company_id,
#                             employee_details_id=employee_id
#                         )

#                         # Find the policy ID for "Unpaid Leaves"
#                         emp_leave_policy_id = None
#                         policies_array = []  # Initialize an empty list to store all policy details

#                         policy_balance = 0
#                         emp_leave_policy_id = None  # Initialize emp_leave_policy_id

#                         # if leave_policies:
#                         #     for policy in leave_policies:
#                         #         # Store policy details in the array
#                         #         policies_array.append({
#                         #             "policy_id": str(policy._id),
#                         #             "policy_name": policy.leave_policy_id.leave_policy_name,
#                         #             "balance": policy.balance
#                         #         })

#                         #         # Check if this is the "Unpaid Leaves" policy
#                         #         if policy.leave_policy_id.leave_policy_name == "Unpaid Leaves":
#                         #             emp_leave_policy_id = str(policy._id)
#                         #             policy_balance = policy.balance

#                         #     if not emp_leave_policy_id:
#                         #         print("No policy found with the name 'Unpaid Leaves'.")
#                         # else:
#                         #     print("No leave policies found for this employee.")

#                         # # Example output of policies_array
#                         # print(policies_array

#                         if leave_policies:
#                             for policy in leave_policies:
                                
#                                 policies_array.append({
#                                     "policy_id": str(policy._id),
#                                     "policy_name": policy.leave_policy_id.leave_policy_name,
#                                     "balance": policy.balance,
#                                     "leave_policy_id": policy.leave_policy_id, 
#                                     "allowance_day": getattr(policy, "allowance_day", 30),                                
#                                 })

#                                 # Check if this is the "Unpaid Leaves" policy
#                                 if policy.leave_policy_id.leave_policy_name == "Unpaid Leaves":
#                                     emp_leave_policy_id = str(policy._id)
#                                     policy_balance = policy.balance

#                             if not emp_leave_policy_id:
#                                 print("No policy found with the name 'Unpaid Leaves'.")
#                         else:
#                             print("No leave policies found for this employee.")

#                         # Example output of policies_array
#                         print(policies_array)



#                         # Update leave application details
#                         leave_application_details.update(
#                             current_approval_level="",
#                             leave_status="approved",
#                             balance_before_approval=current_leave_balance,
#                             balance_after_approval=0,
#                             approved_on=datetime.now()
#                         )

#                         # Calculate adjustment days
#                         adj_days = asking_leave_days if not has_edited else new_no_of_days
#                         after_adj = current_leave_balance - float(adj_days)


                        

#                         if asked_leave_till.year > asked_leave_from.year:
#                             # Calculate how many days are in the next year
#                             first_day_next_year = datetime(asked_leave_till.year, 1, 1)
#                             days_in_next_year = (asked_leave_till - first_day_next_year).days + 1  # Include `asked_leave_till` itself

#                             print(f"Days in next year: {days_in_next_year}")

#                             if current_leave_balance != 0:
#                                 # First adjustment (deduct full current balance)
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
#                                     adjustment_type='decrement',
#                                     adjustment_days=str(current_leave_balance),
#                                     adjustment_comment=str(comment),
#                                     before_adjustment=str(current_leave_balance),
#                                     after_adjustment="0",  # Balance after full deduction
#                                     created_at=created_at
#                                 )
#                                 status = new_data.save()
#                                 leave_application_details.update(leave_adjustment=new_data._id)
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(leave_application_details.employee_leave_policy._id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=0)

#                                 # Second adjustment for new leave balance with `created_at` as the first day of next year
#                                 created_at = first_day_next_year.strftime("%d %B %Y %H:%M:%S")  # Format: 01 January 2023 00:00:00

#                                 leave_allow = 30  # Default allowance
#                                 for policy in policies_array:
#                                     if policy["policy_id"] == str(leave_application_details.employee_leave_policy._id):
#                                         leave_allow = policy["allowance_day"]
#                                         break

#                                 # Example of applying the adjustment logic using the leave allowance
#                                 print(f"Leave allowance for policy {leave_application_details.employee_leave_policy._id}: {leave_allow}")

#                                 leave_allow_balance=leave_allow-days_in_next_year
#                                 # Save second adjustment (if applicable)
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
#                                     adjustment_type="decrement",
#                                     adjustment_days=str(days_in_next_year),
#                                     adjustment_comment="Adjustment for new year",
#                                     before_adjustment=str(leave_allow),  # Assuming fully deducted
#                                     after_adjustment=str(leave_allow_balance),  # New allowance for the year
#                                     created_at=created_at,
                            
#                                 )
#                                 status = new_data.save()
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(leave_application_details.employee_leave_policy._id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=leave_allow_balance)

#                                 print(f"Adjustment saved with created_at: {created_at}")

#                         else:
#                                # Create leave adjustments
#                             if current_leave_balance != 0:
#                                 # First adjustment (deduct full current balance)
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
#                                     adjustment_type='decrement',
#                                     adjustment_days=str(current_leave_balance),
#                                     adjustment_comment=str(comment),
#                                     before_adjustment=str(current_leave_balance),
#                                     after_adjustment="0" ,
#                                     created_at=created_at # Balance after full deduction
#                                 )
#                                 status = new_data.save()
#                                 leave_application_details.update(leave_adjustment=new_data._id)
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(leave_application_details.employee_leave_policy._id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=0)
                            
                           
#                             if emp_leave_policy_id:
#                                 new_policy_balance = policy_balance + difference
#                                 new_data = EmployeeLeaveAdjustment(
#                                     company_id=leave_policy_details.company_id,
#                                     employee_details_id=leave_policy_details.employee_details_id,
#                                     employee_leave_pol_id=ObjectId(emp_leave_policy_id),
#                                     adjustment_type='decrement',
#                                     adjustment_days=str(difference),  # Always store positive adjustment days
#                                     adjustment_comment=str(comment),
#                                     before_adjustment=str(policy_balance),
#                                     after_adjustment=str(-new_policy_balance),
#                                     created_at=created_at
#                                 )
#                                 status = new_data.save()
#                                 leave_application_details.update(leave_adjustment=new_data._id)
                                
#                                 EmployeeLeavePolicies.objects(
#                                     company_id=company_id,
#                                     _id=ObjectId(emp_leave_policy_id)
#                                 ).update(push__employee_leave_adjustments=new_data._id, balance=float(-new_policy_balance))

                     
#                             print("Leave adjustment saved successfully.", status)

#                 except Exception as e:
#                     print(f"Error saving leave adjustment: {e}")

                
#                 work_timings = WorkTimings.objects(is_day_off=True,company_id=leave_application_details.company_id.id).first()
#                 if not work_timings:
                    
#                     work_timings =  WorkTimings(name="Day Off",
#                                 schedule_color='#808080',
#                                 is_day_off=True,
#                                 office_start_at='',
#                                 office_end_at='',
#                                 late_arrival__later_than='',
#                                 early_departure_earliar_than='',
#                                 consider_absent_after='',
#                                 week_offs = '',
#                                 company_id = leave_application_details.company_id.id
#                                 )
#                     work_timings.save()
#                     update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__worktimings=work_timings._id)

#                 start_date = leave_application_details.leave_from if not has_edited else new_leave_from
#                 end_date = leave_application_details.leave_till if not has_edited else new_leave_till


#                 # .................send an email to the leave applicant about approval ...........
#                 approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name

#                 email_template = 'email/leave_approved.html'
#                 data = {}

#                 data['employee_details_id'] = leave_policy_details.employee_details_id
#                 data['type'] = leave_application_details.employee_leave_policy.leave_policy_id.leave_type
#                 data['start_date'] = start_date.strftime('%Y-%m-%d')
#                 data['end_date'] = end_date.strftime('%Y-%m-%d')
#                 data['no_of_days'] = adj_days
#                 data['is_modified'] = 'Yes' if has_edited else 'No'
#                 data['aprover_remarks'] = comment
#                 data['approver_name'] = approver
#                 data['status'] = 'accepted'
#                 data['receiver_email'] = leave_application_details.employee_details_id.personal_email

#                 send_email(email_template, data)

#                 #.................end of sending email.............................................
                
#                 while start_date <= end_date:
#                     is_already_scheduled = CompanyEmployeeSchedule.objects(work_timings=work_timings._id,employee_id=leave_application_details.employee_details_id._id,schedule_from=start_date,schedule_till=start_date).first()
#                     if not is_already_scheduled:
#                         employee_schedule = CompanyEmployeeSchedule(company_id=leave_application_details.company_id.id,
#                                                         work_timings=work_timings._id,
#                                                         employee_id=leave_application_details.employee_details_id._id,
#                                                         schedule_from=start_date,
#                                                         schedule_till=start_date,
#                                                         allow_outside_checkin = False,
#                                                         is_leave = True,
#                                                         leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                             )
#                         employee_schedule.save()                        
#                         update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__employee_schedules=employee_schedule._id)
#                         # Add attendance Data as well
#                         employee_attendance = EmployeeAttendance()    
#                         employee_attendance.employee_id = leave_application_details.employee_details_id.employee_company_details.employee_id
#                         employee_attendance.employee_details_id = leave_application_details.employee_details_id._id
#                         employee_attendance.attendance_date = start_date
#                         employee_attendance.company_id = leave_application_details.company_id.id
#                         employee_attendance.leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
#                         employee_attendance.attendance_status = "absent"
#                         employee_attendance.save()
#                     # start_date = start_date + timedelta(days=1)
#                     # todo: Create an adjustment record if the leave policy type is unpaid
#                     if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
#                         start_of_month = start_date.replace(day=1)
#                         nxt_mnth = start_date.replace(day=28) + timedelta(days=4)
#                         # subtracting the days from next month date to
#                         # get last date of current Month
#                         end_of_the_month  = nxt_mnth - timedelta(days=nxt_mnth.day)
#                             # Todo: Create a adjustment record by deducting the off day amount
#                         # Check if the adjustment reason is defined if not create a adjustment reason for Unpaid Leaves
#                         adjustment_reason = CompanyAdjustmentReasons.objects(company_id=leave_application_details.company_id.id,adjustment_reason="Unpaid Leaves").first()
#                         if not adjustment_reason:
#                             adjustment_reason = create_adjustment_reason(leave_application_details.company_id.id,"Unpaid Leaves","deduction")
                        
#                         # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
#                         total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary
                        
#                         current_month = start_date.strftime('%B')

#                         calendar_working_days = CompanyDetails.objects(user_id=leave_application_details.company_id.id).only('working_days').first()
                        
#                         working_days = list(filter(lambda x:x['month']==current_month.lower(),calendar_working_days.working_days))

#                         no_of_working_days = int(working_days[0]['days']) if working_days else end_of_the_month.days() # By Default Set to 30 Days
                                            
#                         adjustment_amount = round(int(total_salary)/no_of_working_days,0)
                        
#                         adjustment_exists = CompanyPayrollAdjustment.objects(company_id=leave_application_details.company_id.id,
#                                                                 employee_details_id=leave_application_details.employee_details_id._id,
#                                                                 adjustment_reason_id=adjustment_reason._id,
#                                                                 attendance_date=start_date).first()
#                         if adjustment_exists:
#                             adjustment_exists.delete()
                            
#                         new_data = CompanyPayrollAdjustment(
#                                 company_id = leave_application_details.company_id.id,
#                                 employee_details_id = leave_application_details.employee_details_id._id,
#                                 adjustment_reason_id = adjustment_reason._id,
#                                 adjustment_type = adjustment_reason.adjustment_type,
#                                 adjustment_amount = str(adjustment_amount),
#                                 adjustment_on = start_of_month,
#                                 adjustment_month_on_payroll = start_of_month.strftime('%B'),
#                                 adjustment_year_on_payroll =  start_of_month.year,
#                                 attendance_date =  start_date,                   
#                         )   
#                         new_data.save()
#                     start_date = start_date + timedelta(days=1)
                  
                
#                     # msg = json.dumps({
#                     #     "status": "failed",
#                     #     "message": "Insufficient leave balance",
#                     #     "current_balance": current_leave_balance,
#                     #     "asking_leave_days": asking_leave_days,
#                     #     "difference": difference
#                     # })
#                     # msghtml = json.loads(msg)
#                     # return msghtml
#                     msg =  json.dumps({'status':'success'})
#                     msghtml = json.loads(msg)
#                     return msghtml


#         msg =  json.dumps({'status':'success'})
#         msghtml = json.loads(msg)
#         return msghtml   
#     else:
#         msg = json.dumps({"status": "failed"})
#         msghtml = json.loads(msg)
#         return msghtml




@employee.route('/superrejectleaverequest', methods=['POST'])
def super_reject_leave_request():
    leave_request_id = request.form.get('leave_request_id')
    leave_reject_reason = request.form.get('leave_reject_reason')
    if leave_request_id:
        leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
        # check if the data exist or not 
        if leave_request_details:
            leave_application_details = EmployeeLeaveApplication.objects(_id=leave_request_details.employee_leave_app_id._id).first()
            # Change the status of LeaveRequest by the previous/Current approver
            leave_request_details.update(request_status="rejected",rejected_on=datetime.now())
            
            super_employee = EmployeeDetails.objects(user_id=current_user.id).first() 
            super_approver_details = SuperLeaveApprovers.objects(employee_details_id=super_employee._id).first()
            # leave_request_details.update(is_super_approved=True,super_approver_comment=comment,super_approver=super_approver_details._id)
            # Change the current_approval_level of LeaveApplication and Current approver
            leave_application_details.update(current_approval_level="",
                                             leave_status="rejected",
                                             rejected_by=super_employee.first_name,
                                             leave_reject_reason=leave_reject_reason,
                                             rejected_on=datetime.now(),
                                             is_super_approved=True,
                                             super_approver_comment=leave_reject_reason,
                                             super_approver=super_approver_details._id)
                
            msg =  json.dumps({'status':'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml    
    
    
@employee.route('/leaveapplicationhistory', methods=['GET'])
def leave_application_history():
    application_id = request.args.get('application_id')
    application_details = EmployeeLeaveApplication.objects(_id=ObjectId(application_id)).first()
    if application_details:
        details = {}
        data = []
        for item in application_details.approver_list:
            if item._id != application_details.current_aprrover._id: 
                details = {
                    'approved_on' : item.approved_on.strftime('%b %d') if hasattr(item,'approved_on') else '',
                    'comment' : item.comment,
                    'approver_name' : item.approver_id.employee_details_id.first_name+' '+item.approver_id.employee_details_id.last_name,
                    'status' :  item.request_status,
                }
                data.append(details)
                
        # attendance_data = loads(attendance_details.to_json())
        msg =  json.dumps({'status':'success','details':data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg =  json.dumps({"status":"failed"})
        msghtml = json.loads(msg)
        return msghtml
    

@celery.task(track_started=True, result_extended=True, name='Leave-Application-Creation')
def send_leave_notification_email(leave_application_id):
    # Defer import to avoid circular import
    from ..company.model import EmployeeLeaveApplication
    from ..models import CompanyDetails
    from .. import mail

    # Get Leave application details
    leave_application_details = EmployeeLeaveApplication.objects(_id=ObjectId(leave_application_id)).first()
    if leave_application_details:
        company_details = CompanyDetails.objects(user_id=leave_application_details.company_id).only('email_config').first()
        mail_server = current_app.config['MAIL_SERVER']
        mail_port = current_app.config['MAIL_PORT']
        mail_use_tls = current_app.config['MAIL_USE_TLS']
        mail_username = current_app.config['MAIL_USERNAME']
        mail_password = current_app.config['MAIL_PASSWORD']

        current_app.config.update(
            MAIL_SERVER=mail_server,
            MAIL_PORT=mail_port,
            MAIL_USE_TLS=mail_use_tls,
            MAIL_USERNAME=mail_username,
            MAIL_PASSWORD=mail_password
        )
        mail.init_app(current_app)

        with current_app.app_context():
            receiver_email = leave_application_details.current_aprrover.approver_id.employee_details_id.user_id.email
            approver_name = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name
            html = render_template('email/leave_notification.html', leave_application_details=leave_application_details, approver_name=approver_name)
            msg = Message('Leave Application Approval Required! | Cubes HRMS', sender=("Cubes HRMS", current_app.config['MAIL_USERNAME']), recipients=[receiver_email])
            msg.html = html
            mail.send(msg)
            return True

@celery.task(track_started=True, result_extended=True, name='Leave-Application-Status-Update')
def send_email(template, data):
    from .. import mail
    
    mail_server = current_app.config['MAIL_SERVER']
    mail_port = current_app.config['MAIL_PORT']
    mail_use_tls = current_app.config['MAIL_USE_TLS']
    mail_username = current_app.config['MAIL_USERNAME']
    mail_password = current_app.config['MAIL_PASSWORD']

    current_app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USERNAME=mail_username,
        MAIL_PASSWORD=mail_password
    )
    mail.init_app(current_app)

    with current_app.app_context():
        receiver_email = data['receiver_email']
        html = render_template(template_name_or_list=template, data=data)
        msg = Message('Leave Application Approval Required! | Cubes HRMS', sender=("Cubes HRMS", current_app.config['MAIL_USERNAME']), recipients=[receiver_email])
        msg.html = html
        mail.send(msg)
        return True