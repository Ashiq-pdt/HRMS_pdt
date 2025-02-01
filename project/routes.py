import calendar
import os
import uuid
from datetime import datetime, timedelta
from flask_mail import Message
from bson import ObjectId
from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for, json, session
from flask import current_app
from flask_login import login_required
from flask_security import roles_accepted, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from .. import create_app,create_celery_app, mail
from .utils.employe_attendance_related import process_leave_request, send_approval_email
from project.employee.model import EmployeeBreakHistory
from .utils.process_pending_leave_requests import process_pending_leave_requests
from ..company.model import EmployeeDetails, EmployeeAttendance, EmployeeLeaveApplication, EmployeeLeaveApprover, \
    EmployeeLeavePolicies, EmployeeLeaveRequest, EmployeeTimeRequest, EmployeeLeaveAdjustment, EmployeeReimbursement
from ..models import (User, CompanyLeaveApprovers, WorkTimings, CompanyDetails, CompanyEmployeeSchedule,
                      CompanyHolidays, CompanyOvertimePolicies, CompanyTimeApprovers, CompanyAdjustmentReasons,
                      CompanyPayrollAdjustment, CompanyTimeOffAdjustment, SuperLeaveApprovers)

employee = Blueprint('employee', __name__)


celery = create_celery_app()

def chop_microseconds(delta):
    return delta - timedelta(microseconds=0, milliseconds=0)


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
    return render_template('employee/profile.html', employee_details=employee_details, departments=departments)


@employee.route('/edit/profile')
@login_required
@roles_accepted('employee')
def edit_profile():
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    return render_template('employee/edit_profile.html', employee_details=employee_details)


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
                employee_details.update(profile_pic=profile_pic)
            flash('Profile Details Updated Successfully!', 'success')
            return redirect(url_for('employee.edit_profile'))
    else:
        return redirect(url_for('employee.profile'))


def populate_employee_details(request):
    employee_details = {
        'first_name': request.form.get('first_name'),
        'last_name': request.form.get('last_name'),
        'father_name': request.form.get('father_name'),
        'contact_no': request.form.get('contact_no'),
        'emergency_contact_no_1': request.form.get('emergency_contact_no_1'),
        'emergency_contact_no_2': request.form.get('emergency_contact_no_2'),
        'dob': request.form.get('dob'),
        'gender': request.form.get('gender'),
        'marital_status': request.form.get('marital_status'),
        'blood_group': request.form.get('blood_group'),
        'present_address': request.form.get('present_address'),
        'permanent_address': request.form.get('permanent_address'),
        'personal_email': request.form.get('personal_email'),
        'facebook_link': request.form.get('facebook_link'),
        'linkedin_link': request.form.get('linkedin_link'),
        'twitter_link': request.form.get('twitter_link'),
        'about_me': request.form.get('about_me'),
    }
    return employee_details


def upload_profile_pic(file):
    fname = ''
    file = request.files['profile_pic']
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = os.path.splitext(filename)[1]
        fname = fn + str(uuid.uuid4()) + file_ext
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
            flash('Wrong Current Password, Please try again.', 'danger')
            return redirect(url_for('auth.edit_profile'))
        else:
            #Create Employee Login Details
            update_status = user.update(password=generate_password_hash(new_password, method='sha256'))
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
        attendance_date = datetime.today().replace(minute=0, hour=0, second=0, microsecond=0)
        current_latitude = request.form.get('current_latitude')
        current_longitude = request.form.get('current_longitude')
        working_from = request.form.get('working_from')
        working_office = request.form.get('working_office')
        note = request.form.get('notes')

        data_available = EmployeeAttendance.objects(company_id=ObjectId(company_id), attendance_date=attendance_date,
                                                    employee_details_id=ObjectId(employee_details_id)).first()
        if data_available:
            data_available.delete()
        employee_details = EmployeeDetails.objects(_id=ObjectId(employee_details_id)).first()
        employee_attendance = EmployeeAttendance()
        employee_attendance.employee_id = employee_details.employee_company_details.employee_id
        employee_attendance.employee_details_id = ObjectId(employee_details_id)
        employee_attendance.attendance_date = attendance_date
        employee_attendance.company_id = ObjectId(company_id)
        employee_attendance.employee_check_in_at = employee_check_in_at
        employee_attendance.attendance_status = "present"
        employee_attendance.clock_in_coords = [{"lat": current_latitude, "lng": current_longitude}]
        employee_attendance.working_from = ObjectId(working_from)
        employee_attendance.clock_in_note = note
        employee_attendance.working_office = ObjectId(working_office)
        employee_attendance.has_next_day_clockout = True if session["has_next_day_clockout"] else False

        # Calculate the late minutes if late by the employee;
        late_minutes, final_datetime = calculate_late_details(employee_check_in_at, employee_details, attendance_date)
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
                time_request = create_time_request(ObjectId(company_id), employee_attendance._id,
                                                   employee_details.employee_company_details.department, 'late')

        if status:
            msg = json.dumps(
                {"status": "success", "checked_in_time": employee_check_in_at.strftime('%d %B %Y , %H:%M:%S %p')})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg = json.dumps({"status": "failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))


@employee.route('/employee/clockout/', methods=['POST'])
def clock_out():
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        employee_details_id = request.form.get('employee_details_id')
        employee_check_out_at = datetime.now()
        attendance_date = datetime.today().replace(minute=0, hour=0, second=0, microsecond=0) if not session[
            "has_next_day_clockout"] else (datetime.today() - timedelta(days=1)).replace(minute=0, hour=0, second=0,
                                                                                         microsecond=0)
        current_latitude = request.form.get('current_latitude')
        current_longitude = request.form.get('current_longitude')
        note = request.form.get('notes')

        has_overtime, ot_by_minutes, ot_policy_multiplier, ot_type, ot_policy_on = False, 0, '', '', ''
        attendance_data = EmployeeAttendance.objects(company_id=ObjectId(company_id), attendance_date=attendance_date,
                                                     employee_details_id=ObjectId(employee_details_id)).first()
        if attendance_data:
            total_hrs_worked = chop_microseconds(employee_check_out_at - attendance_data.employee_check_in_at)
            attendance_data.total_hrs_worked = str(total_hrs_worked)
            attendance_data.employee_check_out_at = employee_check_out_at
            attendance_data.clock_out_note = note
            attendance_data.clock_out_coords = [{"lat": current_latitude, "lng": current_longitude}]

            # Check if the user clocked out Early or Has Any Overtime
            # Todo: Check if the user left early
            # Start
            # Calculate the Early minutes if late by the employee;
            early_by_minutes = calculate_early_departure_details(employee_check_out_at,
                                                                 attendance_data.employee_details_id,
                                                                 attendance_data.attendance_date)

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
                has_overtime, ot_by_minutes, ot_policy_multiplier, ot_type, ot_policy_on = calculate_overtime_details(
                    employee_check_out_at, attendance_data.employee_check_in_at, attendance_data.employee_details_id,
                    attendance_date)
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
                time_request = create_time_request(ObjectId(company_id), attendance_data._id,
                                                   attendance_data.employee_details_id.employee_company_details.department,
                                                   'early')

        if status:
            msg = json.dumps(
                {"status": "success", "checked_out_time": employee_check_out_at.strftime('%d %B %Y , %H:%M:%S %p'),
                 "checked_in_time": attendance_data.employee_check_in_at.strftime('%d %B %Y , %H:%M:%S %p'),
                 "has_overtime": has_overtime, "ot_by_minutes": ot_by_minutes,
                 "attendance_id": str(attendance_data._id)})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg = json.dumps({"status": "failed"})
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
        attendance_date = datetime.today().replace(minute=0, hour=0, second=0, microsecond=0)
        break_id = request.form.get('break_id')

        break_type = request.form.get('break_type')
        break_history = EmployeeBreakHistory.objects(already_ended=False, attendance_date=attendance_date,
                                                     employee_details_id=ObjectId(employee_details_id),
                                                     company_id=ObjectId(company_id)).first()
        if break_type == 'start' and not break_history:
            break_history = EmployeeBreakHistory()
            break_history.start_at = datetime.now()
            break_history.company_id = ObjectId(company_id)
            break_history.employee_details_id = ObjectId(employee_details_id)
            break_history.attendance_date = attendance_date
            status = break_history.save()
            update_details = EmployeeAttendance.objects(company_id=ObjectId(company_id),
                                                        attendance_date=attendance_date,
                                                        employee_details_id=ObjectId(employee_details_id)).update(
                push__break_history=break_history.id, on_break=True)

        if break_type == 'end' and break_id:  #break_type: end
            break_history = EmployeeBreakHistory.objects(_id=ObjectId(break_id)).first()
            if break_history:
                already_ended = True
                end_at = datetime.now()
                diff = end_at - break_history.start_at  #in minutes
                break_difference = diff.total_seconds() / 60
                status = break_history.update(already_ended=already_ended, end_at=end_at,
                                              break_difference=break_difference)
                update_details = EmployeeAttendance.objects(company_id=ObjectId(company_id),
                                                            attendance_date=attendance_date,
                                                            employee_details_id=ObjectId(employee_details_id)).update(
                    on_break=False)

        if status:
            msg = json.dumps(
                {"status": "success", "break_id": str(break_history._id), "break_minutes": break_difference})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg = json.dumps({"status": "failed"})
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
        attendance_details.break_history = sorted(attendance_details.break_history, key=lambda k: k.start_at,
                                                  reverse=True)
        for item in attendance_details.break_history:
            details = {
                'attendance_date': item.attendance_date.strftime('%b %d'),
                'start_at': item.start_at.strftime('%H:%M:%S %p'),
                'end_at': item.end_at.strftime('%H:%M:%S %p') if item.end_at else '',
                'break_difference': item.break_difference if item.break_difference else '',
            }
            data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg = json.dumps({'status': 'success', 'details': data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg = json.dumps({"status": "failed"})
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
                'lat': item['lat'],
                'lng': item['lng']
            }
            data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg = json.dumps({'status': 'success', 'details': data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg = json.dumps({"status": "failed"})
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
                'lat': item['lat'],
                'lng': item['lng']
            }
            data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg = json.dumps({'status': 'success', 'details': data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg = json.dumps({"status": "failed"})
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
            'attendance_id': str(attendance_details._id),
            'employee_check_in_at': attendance_details.employee_check_in_at.strftime('%I:%M %p'),
            'employee_check_out_at': attendance_details.employee_check_out_at.strftime('%I:%M %p') if hasattr(
                attendance_details, 'employee_check_out_at') else '',
            'clock_in_note': attendance_details.clock_in_note if hasattr(attendance_details, 'clock_in_note') else '',
            'clock_out_note': attendance_details.clock_out_note if hasattr(attendance_details,
                                                                           'clock_out_note') else '',
        }
        data.append(details)
        # attendance_data = loads(attendance_details.to_json())
        msg = json.dumps({'status': 'success', 'details': data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg = json.dumps({"status": "failed"})
        msghtml = json.loads(msg)
        return msghtml


@employee.route('/leaves', methods=['GET', 'POST'])
@login_required
@roles_accepted('employee')
def leaves():
    if request.method == 'POST':
        attendance_range = request.form.get('daterange').split(' - ')
        start_date = datetime.strptime(attendance_range[0], '%d/%m/%Y')
        end_date = datetime.strptime(attendance_range[1], '%d/%m/%Y')

        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        can_apply_leave = CompanyDetails.objects(user_id=employee_details.company_id).only(
            'disable_leave_application').first()
        leave_applications = EmployeeLeaveApplication.objects(employee_details_id=employee_details._id)
        adjustment_details = EmployeeLeaveAdjustment.objects(employee_details_id=employee_details.id,
                                                             created_at__gte=start_date,
                                                             created_at__lte=end_date)

        return render_template('employee/leaves.html', employee_details=employee_details,
                               adjustment_details=adjustment_details, start=start_date, end=end_date,
                               leave_applications=leave_applications, can_apply_leave=can_apply_leave,
                               isLeaveAdjustmentActive=True)

    now = datetime.today()
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Get the last day of the current month
    last_day = calendar.monthrange(now.year, now.month)[1]

    # Get the end date of the current month
    end_date = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    can_apply_leave = CompanyDetails.objects(user_id=employee_details.company_id).only(
        'disable_leave_application').first()
    leave_applications = EmployeeLeaveApplication.objects(employee_details_id=employee_details._id)
    adjustment_details = EmployeeLeaveAdjustment.objects(employee_details_id=employee_details.id)

    return render_template('employee/leaves.html', employee_details=employee_details,
                           adjustment_details=adjustment_details, start=start_date, end=end_date,
                           leave_applications=leave_applications, can_apply_leave=can_apply_leave)


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
        leave_from = datetime.strptime(leave_range[0], '%d/%m/%Y')
        leave_till = datetime.strptime(leave_range[1], '%d/%m/%Y')
        employee_leave_policy = request.form.get('leave_type')
        reason = request.form.get('reason')
        emergency_contact = request.form.get('emergency_contact')
        contact_address = request.form.get('contact_address')

        leave_application = EmployeeLeaveApplication()
        leave_application.employee_details_id = employee_details._id
        leave_application.no_of_days = no_of_days
        leave_application.leave_from = leave_from
        leave_application.leave_till = leave_till
        leave_application.employee_leave_policy = ObjectId(employee_leave_policy)
        leave_application.reason = reason
        leave_application.company_id = employee_details.company_id
        leave_application.current_approval_level = "1"

        leave_application.asked_leave_from = leave_from
        leave_application.asked_leave_till = leave_till
        leave_application.asked_no_of_days = no_of_days

        leave_application.emergency_contact = emergency_contact
        leave_application.contact_address = contact_address

        # Get the company approver level and store the ref id to employee leave application
        company_leave_approver = CompanyLeaveApprovers.objects(
            department_name=employee_details.employee_company_details.department,
            company_id=employee_details.company_id).first()
        if company_leave_approver:
            leave_application.company_approver = company_leave_approver._id
            leave_application.company_approval_level = company_leave_approver.department_approval_level

        # This department follows the deafult/all department approval level
        else:
            company_leave_approver = CompanyLeaveApprovers.objects(department_name="all",
                                                                   company_id=employee_details.company_id).first()
            if company_leave_approver:
                leave_application.company_approver = company_leave_approver._id
                leave_application.company_approval_level = company_leave_approver.department_approval_level

        status = leave_application.save()

        # Request the approver for the approval Create a record for EmployeeLeaveRequest
        request_approver = EmployeeLeaveRequest()
        request_approver.employee_leave_app_id = leave_application._id
        request_approver.company_id = employee_details.company_id

        # Get Approver Details Based on Level(Current Level=1,department=current department,company ID)
        approver = EmployeeLeaveApprover.objects(employee_approval_level="1",
                                                 department_name=employee_details.employee_company_details.department,
                                                 company_id=employee_details.company_id).first()
        if approver:
            request_approver.approver_id = approver._id
        # else Get the all department approver level
        else:
            approver = EmployeeLeaveApprover.objects(employee_approval_level="1", department_name="all",
                                                     company_id=employee_details.company_id).first()
            if approver:
                request_approver.approver_id = approver._id

        request_approver.save()
        leave_application.update(current_aprrover=request_approver._id, add_to_set__approver_list=request_approver._id)
        # Send email to Level 1 application approver
        # send_leave_approval_email.delay(str(leave_application._id))
        # send_leave_approval_email(str(leave_application._id))

        try:
            send_leave_notification_email(str(leave_application._id))
        except Exception as e:
            print(e)

        if status:
            msg = json.dumps({"status": "success"})
            print('sucessfully sent')
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg = json.dumps({"status": "failed"})
            msghtml = json.loads(msg)
            return msghtml


@employee.route('/leavesapprovals')
@login_required
@roles_accepted('employee')
def leaves_approvals():
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
                    {'id': str(subitem._id),
                     'title': subitem.employee_details_id.first_name + ' ' + subitem.employee_details_id.last_name,
                     'start': subitem.asked_leave_from.strftime("%Y-%m-%d"),
                     'end': (subitem.asked_leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                     #  'display': 'block',
                     'color': '#e3b113',
                     'userId': subitem.employee_details_id.employee_company_details.department
                     })

                super_department_list.append(
                    subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list

            elif subitem.leave_status == "approved":
                super_leave_list.append(
                    {'id': str(subitem._id),
                     'title': subitem.employee_details_id.first_name + ' ' + subitem.employee_details_id.last_name,
                     'start': subitem.leave_from.strftime("%Y-%m-%d"),
                     'color': 'rgb(13, 205, 148)',
                     'userId': subitem.employee_details_id.employee_company_details.department
                     })
                super_department_list.append(
                    subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list

    approvers = EmployeeLeaveApprover.objects(employee_details_id=employee_details._id).only('_id')
    if approvers:
        # Look for application request based on approver ids with pending status
        data = []
        for item in approvers:
            data.append(item._id)
        leave_requests = EmployeeLeaveRequest.objects(approver_id__in=data)

        for subitem in leave_requests:
            if subitem.request_status == "pending":
                leave_list.append(
                    {'id': str(subitem._id),
                     'title': subitem.employee_leave_app_id.employee_details_id.first_name + ' ' + subitem.employee_leave_app_id.employee_details_id.last_name,
                     'start': subitem.employee_leave_app_id.asked_leave_from.strftime("%Y-%m-%d"),
                     'end': (subitem.employee_leave_app_id.asked_leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                     #  'display': 'block',
                     'color': '#e3b113',
                     'userId': subitem.employee_leave_app_id.employee_details_id.employee_company_details.department
                     })

                department_list.append(
                    subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list

            elif subitem.request_status == "approved":
                leave_list.append(
                    {'id': str(subitem._id),
                     'title': subitem.employee_leave_app_id.employee_details_id.first_name + ' ' + subitem.employee_leave_app_id.employee_details_id.last_name,
                     'start': subitem.employee_leave_app_id.leave_from.strftime("%Y-%m-%d"),
                     'end': (subitem.employee_leave_app_id.leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                     # 'display': 'block',
                     # 'color':'rgba(255, 173, 0, 1)'
                     # 'eventColor': 'rgb(13, 205, 148)',
                     'color': 'rgb(13, 205, 148)',
                     'userId': subitem.employee_leave_app_id.employee_details_id.employee_company_details.department
                     })
                department_list.append(
                    subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list
    if employee_details.is_super_leave_approver or employee_details.is_approver:
        return render_template('employee/leaves_approval.html', leave_requests=leave_requests,
                               leave_list=leave_list, department_list=department_list, all_leave_list=all_leave_list,
                               super_leave_list=super_leave_list, super_department_list=super_department_list)
    else:
        flash("Sorry, You do not have permission to view/(perform action on) this resource.", 'danger')
        # return render_template('employee/leaves_approval.html',leave_requests=leave_requests,leave_list=leave_list,department_list=department_list,all_leave_list=all_leave_list,super_leave_list=super_leave_list,super_department_list=super_department_list)


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
                    {'id': str(subitem._id),
                     'title': subitem.employee_details_id.first_name + ' ' + subitem.employee_details_id.last_name,
                     'start': subitem.asked_leave_from.strftime("%Y-%m-%d"),
                     'end': (subitem.asked_leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                     #  'display': 'block',
                     'color': '#e3b113',
                     'userId': subitem.employee_details_id.employee_company_details.department
                     })

                super_department_list.append(
                    subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list

            elif subitem.leave_status == "approved":
                super_leave_list.append(
                    {'id': str(subitem._id),
                     'title': subitem.employee_details_id.first_name + ' ' + subitem.employee_details_id.last_name,
                     'start': subitem.leave_from.strftime("%Y-%m-%d"),
                     'color': 'rgb(13, 205, 148)',
                     'userId': subitem.employee_details_id.employee_company_details.department
                     })
                super_department_list.append(
                    subitem.employee_details_id.employee_company_details.department) if subitem.employee_details_id.employee_company_details.department not in super_department_list else super_department_list

    approvers = EmployeeLeaveApprover.objects(employee_details_id=employee_details._id).only('_id')
    # Look for application request based on approver ids with pending status
    data = []
    for item in approvers:
        data.append(item._id)
    leave_requests = EmployeeLeaveRequest.objects(company_id=employee_details.company_id)

    for subitem in leave_requests:
        if subitem.request_status == "pending":
            leave_list.append(
                {'id': str(subitem._id),
                 'title': subitem.employee_leave_app_id.employee_details_id.first_name + ' ' + subitem.employee_leave_app_id.employee_details_id.last_name,
                 'start': subitem.employee_leave_app_id.asked_leave_from.strftime("%Y-%m-%d"),
                 'end': (subitem.employee_leave_app_id.asked_leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                 #  'display': 'block',
                 'color': '#e3b113',
                 'userId': subitem.employee_leave_app_id.employee_details_id.employee_company_details.department
                 })

            department_list.append(
                subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list

        elif subitem.request_status == "approved":
            leave_list.append(
                {'id': str(subitem._id),
                 'title': subitem.employee_leave_app_id.employee_details_id.first_name + ' ' + subitem.employee_leave_app_id.employee_details_id.last_name,
                 'start': subitem.employee_leave_app_id.leave_from.strftime("%Y-%m-%d"),
                 'end': (subitem.employee_leave_app_id.leave_till + timedelta(days=1)).strftime("%Y-%m-%d"),
                 # 'display': 'block',
                 # 'color':'rgba(255, 173, 0, 1)'
                 # 'eventColor': 'rgb(13, 205, 148)',
                 'color': 'rgb(13, 205, 148)',
                 'userId': subitem.employee_leave_app_id.employee_details_id.employee_company_details.department
                 })
            department_list.append(
                subitem.employee_leave_app_id.employee_details_id.employee_company_details.department) if subitem.employee_leave_app_id.employee_details_id.employee_company_details.department not in department_list else department_list
    if employee_details.is_super_leave_approver or employee_details.is_approver:
        return render_template('company/employee/leave_calendar.html', leave_requests=leave_requests,
                               leave_list=leave_list, department_list=department_list, all_leave_list=all_leave_list,
                               super_leave_list=super_leave_list, super_department_list=super_department_list)


@employee.route('/approveleaverequest', methods=['POST'])
def approve_leave_request():
    leave_request_id = request.form.get('leave_request_id')
    comment = request.form.get('approver_comment')

    if leave_request_id:
        leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
        if leave_request_details:
            process_leave_request(leave_request_details, comment, request, current_app)
            return json.dumps({'status': 'success'})
    return json.dumps({'status': 'failed'})


@employee.route('/rejectleaverequest', methods=['POST'])
def reject_leave_request():
    leave_request_id = request.form.get('leave_request_id')
    leave_reject_reason = request.form.get('leave_reject_reason')
    if leave_request_id:
        leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
        # check if the data exist or not 
        if leave_request_details:
            leave_application_details = EmployeeLeaveApplication.objects(
                _id=leave_request_details.employee_leave_app_id._id).first()
            # Change the status of LeaveRequest by the previous/Current approver
            leave_request_details.update(request_status="rejected", rejected_on=datetime.now())
            # Change the current_approval_level of LeaveApplication and Current approver
            leave_application_details.update(current_approval_level="", leave_status="rejected",
                                             rejected_by=leave_request_details.approver_id.employee_details_id.first_name,
                                             leave_reject_reason=leave_reject_reason, rejected_on=datetime.now())

            # .................send an email to the leave applicant about approval ...........
            approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name

            # email_template = 'email/leave_approved.html'
            # data = {}

            # data['employee_details_id'] = leave_application_details.employee_details_id
            # data['type'] = leave_application_details.employee_leave_policy.leave_policy_id.leave_type
            # data['start_date'] = leave_application_details.leave_from.strftime('%Y-%m-%d')
            # data['end_date'] = leave_application_details.leave_till.strftime('%Y-%m-%d')
            # data['no_of_days'] = leave_application_details.no_of_days
            # data['is_modified'] = 'No'
            # data['aprover_remarks'] = leave_reject_reason
            # data['approver_name'] = approver
            # data['status'] = 'rejected'
            # data['receiver_email'] = leave_application_details.employee_details_id.personal_email

            # from .utils.email import send_email

            # send_email(email_template, data, current_app)

            #.................end of sending email.............................................

            msg = json.dumps({'status': 'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg = json.dumps({"status": "failed"})
        msghtml = json.loads(msg)
        return msghtml


@employee.route('/deleteleaveapplication', methods=['POST'])
def delete_leave_application():
    leave_application_id = request.form.get('leave_application_id')
    if leave_application_id:
        leave_request_details = EmployeeLeaveRequest.objects(
            employee_leave_app_id=ObjectId(leave_application_id)).delete()

        leave_application_details = EmployeeLeaveApplication.objects(_id=ObjectId(leave_application_id)).delete()
        # Change the status of LeaveRequest by the previous/Current approver
        # Change the current_approval_level of LeaveApplication and Current approver
        if leave_application_details and leave_request_details:
            msg = json.dumps({'status': 'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg = json.dumps({"status": "failed"})
        msghtml = json.loads(msg)
        return msghtml


def calculate_late_details(employee_check_in_time, employee_details, attendance_date):
    # Todo: Check the Existing Scheduled Work Timings or get the default Work Timings
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,
                                                        schedule_from=attendance_date).first()
    late_by_minutes = 0
    if existing_schedule:
        work_timings = WorkTimings.objects(_id=existing_schedule.work_timings._id).first()
    else:
        # Default Work Timings
        if not employee_details.employee_company_details.work_timing:
            work_timings = WorkTimings.objects(company_id=employee_details.company_id, is_default=True).first()
        else:
            work_timings = employee_details.employee_company_details.work_timing
    if "AM" in work_timings.office_end_at:
        # Checkout without Grace
        existing_schedule_end_time_str = work_timings.office_end_at  #'9:00 AM'
        existing_schedule_end_time = datetime.strptime(existing_schedule_end_time_str, '%I:%M %p')
        # Get the current date and time
        current_check_out_date = datetime.combine(attendance_date.date() + timedelta(days=1),
                                                  existing_schedule_end_time.time())

        # Add 4 hours to the existing schedule end time
        new_end_time = existing_schedule_end_time + timedelta(hours=4)

        # Combine the new end time with the current date to get the final datetime
        final_datetime = datetime(current_check_out_date.year, current_check_out_date.month, current_check_out_date.day,
                                  new_end_time.hour, new_end_time.minute, new_end_time.second, new_end_time.microsecond)
    else:
        final_datetime = ""
    office_start_at = work_timings.office_start_at
    late_arrival_later_than = work_timings.late_arrival_later_than
    default_checkin_time = datetime.strptime(office_start_at, '%I:%M %p')
    current_check_in_date = datetime.combine(attendance_date.date(), default_checkin_time.time())
    current_working_day_check_in = current_check_in_date + timedelta(minutes=int(late_arrival_later_than))

    # check if the employee checked_in early if he/she is early set checkin time at current day work_start time
    employee_check_in_time = current_check_in_date if employee_check_in_time <= current_check_in_date else employee_check_in_time

    if employee_check_in_time > current_working_day_check_in:
        late_by_time = employee_check_in_time - current_check_in_date
        late_by_minutes = late_by_time.total_seconds() / 60

    return (int(late_by_minutes), final_datetime)


def calculate_early_departure_details(employee_check_out_time, employee_details, attendance_date):
    # Todo: Check the Existing Scheduled Work Timings or get the default Work Timings
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,
                                                        schedule_from=attendance_date).first()
    early_by_minutes = 0
    if existing_schedule:
        work_timings = WorkTimings.objects(_id=existing_schedule.work_timings._id).first()
    else:
        # Default Work Timings
        if not employee_details.employee_company_details.work_timing:
            work_timings = WorkTimings.objects(company_id=employee_details.company_id, is_default=True).first()
        else:
            work_timings = employee_details.employee_company_details.work_timing

        # Default Work Timings
        # work_timings = WorkTimings.objects(company_id=employee_details.company_id,is_default=True).first()

    office_end_at = work_timings.office_end_at
    early_departure_earliar_than = work_timings.early_departure_earliar_than
    default_checkout_time = datetime.strptime(office_end_at, '%I:%M %p')

    # This Condition will check if the checkout time is next day of the checkin time 
    if "AM" in office_end_at:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date() + timedelta(days=1),
                                                  default_checkout_time.time())
        # Checkout with Grace
        current_working_day_check_out = current_check_out_date + timedelta(minutes=-int(early_departure_earliar_than))
    else:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date(), default_checkout_time.time())
        # Checkout with Grace
        current_working_day_check_out = current_check_out_date + timedelta(minutes=-int(early_departure_earliar_than))

    if employee_check_out_time < current_working_day_check_out:
        early_by_time = current_check_out_date - employee_check_out_time
        early_by_minutes = early_by_time.total_seconds() / 60

    return int(early_by_minutes)


def calculate_overtime_details(employee_check_out_time, employee_check_in_time, employee_details, attendance_date):
    # Todo: Check the Existing Scheduled Work Timings or get the default Work Timings
    has_overtime, ot_by_minutes, ot_policy_multiplier, ot_type, ot_policy_on = False, 0, '', '', ''
    existing_schedule = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,
                                                        schedule_from=attendance_date).first()
    early_by_minutes = 0
    if existing_schedule:
        work_timings = WorkTimings.objects(_id=existing_schedule.work_timings._id).first()
    else:
        # Default Work Timings
        if not employee_details.employee_company_details.work_timing:
            work_timings = WorkTimings.objects(company_id=employee_details.company_id, is_default=True).first()
        else:
            work_timings = employee_details.employee_company_details.work_timing

        # Default Work Timings
        # work_timings = WorkTimings.objects(company_id=employee_details.company_id,is_default=True).first()

    is_holiday = CompanyHolidays.objects(company_id=employee_details.company_id, occasion_date=attendance_date,
                                         is_working_day=False).first()
    is_non_working_day = True if (is_holiday or work_timings.is_day_off) else False
    overtime_type = 'extended'
    if is_non_working_day:
        overtime_type = 'holiday' if is_holiday else 'dayoff'

    office_start_at = work_timings.office_start_at
    office_end_at = work_timings.office_end_at
    default_checkout_time = datetime.strptime(office_end_at, '%I:%M %p')
    default_checkin_time = datetime.strptime(office_start_at, '%I:%M %p')

    # This Condition will check if the checkout time is next day of the checkin time 
    if "AM" in office_end_at:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date() + timedelta(days=1),
                                                  default_checkout_time.time())
        # Checkin without Grace
        current_check_in_date = datetime.combine(attendance_date.date(), default_checkin_time.time())
    else:
        # Checkout without Grace
        current_check_out_date = datetime.combine(attendance_date.date(), default_checkout_time.time())
        # Checkin without Grace
        current_check_in_date = datetime.combine(attendance_date.date(), default_checkin_time.time())

    total_hrs_worked = employee_check_out_time - employee_check_in_time
    total_working_hour = current_check_out_date - current_check_in_date

    overtime_hours = total_hrs_worked - total_working_hour
    overtime_minutes = overtime_hours.total_seconds() / 60 if overtime_hours else 0
    minimum_ot = int(work_timings.minimum_ot) if work_timings.minimum_ot else 0

    if overtime_minutes >= minimum_ot:
        overtime_policy = CompanyOvertimePolicies.objects(company_id=employee_details.company_id,
                                                          ot_policy_name=overtime_type).first()
        if overtime_policy:
            has_overtime = True
            ot_by_minutes = overtime_minutes
            ot_policy_multiplier = overtime_policy.ot_policy_multiplier
            ot_type = overtime_policy.ot_policy_name
            ot_policy_on = overtime_policy.ot_policy_on

    return has_overtime, int(ot_by_minutes), ot_policy_multiplier, ot_type, ot_policy_on


def create_time_request(company_id, attendance_id, department, request_type):
    # Todo: Check for the time approver if exist create record else return false; 
    company_time_approver = CompanyTimeApprovers.objects(company_id=company_id, department_name=department).first()
    if not company_time_approver:
        company_time_approver = CompanyTimeApprovers.objects(company_id=company_id, department_name='all').first()
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

        return render_template('employee/time_approval.html', time_requests=time_requests)


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
            time_request_details.update(request_status="approved", approved_on=datetime.now())
            # Change the approval_status of timeApplication         
            if time_request_details.request_type == 'early':
                approved_minutes = edit_approval_time if has_edited else attendance_details.early_by_minutes
                status = attendance_details.update(early_approval_status=True, approved_early_minutes=approved_minutes)

            elif time_request_details.request_type == 'late':
                approved_minutes = edit_approval_time if has_edited else attendance_details.late_by_minutes
                status = attendance_details.update(late_approval_status=True, approved_late_minutes=approved_minutes)

            elif time_request_details.request_type == 'overtime':
                approved_minutes = edit_approval_time if has_edited else attendance_details.ot_by_minutes
                status = attendance_details.update(ot_approval_status=True, approved_ot_minutes=approved_minutes)

            # Todo: Calculate and generate an adjustment based on request Type; Check if the employee is Full-time if yes create an adjustment
            if status and time_request_details.attendance_id.employee_details_id.employee_company_details.type == '0':
                if approval_type == 'timeoff':
                    generate_timeoff_on_approval(time_request_details._id)
                else:
                    generate_adjustment_on_approval(time_request_details._id)

            msg = json.dumps({'status': 'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg = json.dumps({"status": "failed"})
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
            time_request_details.update(request_status="rejected", rejected_on=datetime.now(),
                                        time_reject_reason=time_reject_reason)
            msg = json.dumps({'status': 'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg = json.dumps({"status": "failed"})
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
    current_month = datetime(time_request_details.attendance_id.attendance_date.year,
                             time_request_details.attendance_id.attendance_date.month, 1).strftime('%B')
    calendar_working_days = CompanyDetails.objects(user_id=time_request_details.company_id.id).only('working_days',
                                                                                                    'daily_working_hour').first()
    # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
    working_days = list(filter(lambda x: x['month'] == current_month.lower(), calendar_working_days.working_days))

    no_of_working_days = int(working_days[0]['days']) if working_days else 30  # By Default Set to 30 Days
    daily_salary = int(monthly_salary) / no_of_working_days  # Get the no of working days in current monthly calendar
    daily_basic_salary = int(
        basic_monthly_salary) / no_of_working_days  # Get the no of working days in current monthly calendar
    # Todo: Check for the schedule in order to get total working hours of employee or else get default working hour from WTs
    existing_schedule = CompanyEmployeeSchedule.objects(
        employee_id=time_request_details.attendance_id.employee_details_id._id,
        schedule_from=time_request_details.attendance_id.attendance_date).first()
    if existing_schedule:
        total_working_hours = existing_schedule.work_timings.total_working_hour
    else:
        # Default Work Timings
        if not employee_data.employee_company_details.work_timing:
            default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,
                                                       is_default=True).first()
        else:
            default_work_timings = employee_data.employee_company_details.work_timing

        # default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,is_default=True).first() 
        total_working_hours = default_work_timings.total_working_hour

    total_working_hour = datetime.strptime(total_working_hours, '%I:%M:%S')
    working_hour = (total_working_hour.hour * 60 + total_working_hour.minute) / 60

    daily_working_hour = working_hour if working_hour else calendar_working_days.daily_working_hour  # Default Set to daily_working_hour
    hourly_rate = float(daily_salary) / float(daily_working_hour)
    basic_hourly_rate = float(daily_basic_salary) / float(daily_working_hour)
    # Wages Details End

    adjustment_amount = 0
    start_of_month = time_request_details.attendance_id.attendance_date.replace(day=1, minute=0, hour=0, second=0,
                                                                                microsecond=0)

    if time_request_details.request_type == 'early' or time_request_details.request_type == 'late':
        if time_request_details.request_type == 'early':
            # Todo: Check if the Deduction Reason Exist or else Create a new;
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,
                                                                 adjustment_reason="Early Departure").first()
            if not adjustment_reason:
                adjustment_reason = create_adjustment_reason(time_request_details.company_id.id, "Early Departure",
                                                             "deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            adjustment_amount = (hourly_rate / 60) * float(time_request_details.attendance_id.approved_early_minutes)
            # adjustment_amount = round((hourly_rate/60)*float(time_request_details.attendance_id.approved_early_minutes),2)

        elif time_request_details.request_type == 'late':
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,
                                                                 adjustment_reason="Late Arrival").first()
            if not adjustment_reason:
                adjustment_reason = create_adjustment_reason(time_request_details.company_id.id, "Late Arrival",
                                                             "deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            adjustment_amount = (hourly_rate / 60) * float(time_request_details.attendance_id.approved_late_minutes)
            # adjustment_amount =  round((hourly_rate/60)*float(time_request_details.attendance_id.approved_late_minutes),2)


    elif time_request_details.request_type == 'overtime':
        adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,
                                                             adjustment_reason="Extra Hours").first()
        if not adjustment_reason:
            adjustment_reason = create_adjustment_reason(time_request_details.company_id.id, "Extra Hours", "addition")

        if (time_request_details.attendance_id.ot_policy_on == 'basic_salary'):
            adjustment_amount = ((basic_hourly_rate * float(
                time_request_details.attendance_id.ot_policy_multiplier)) / 60) * int(
                time_request_details.attendance_id.approved_ot_minutes)
        else:
            adjustment_amount = ((hourly_rate * float(
                time_request_details.attendance_id.ot_policy_multiplier)) / 60) * int(
                time_request_details.attendance_id.approved_ot_minutes)

    # Todo: Create a CPA Record
    if adjustment_amount > 0:
        new_data = CompanyPayrollAdjustment(
            company_id=time_request_details.company_id.id,
            employee_details_id=time_request_details.attendance_id.employee_details_id._id,
            adjustment_reason_id=adjustment_reason._id,
            adjustment_type=adjustment_reason.adjustment_type,
            adjustment_amount=str(adjustment_amount),
            adjustment_on=start_of_month,
            adjustment_month_on_payroll=start_of_month.strftime('%B'),
            adjustment_year_on_payroll=start_of_month.year)
        status = new_data.save()

    return True


def generate_timeoff_on_approval(time_request_details_id):
    # Todo: Check if the Adjustment reasons are already added else add; for late and early create Deducution Adjustment Reason; for OT Create Addition Adjustment Reason; 
    # Todo: Calculate the hourly rate of the employee
    # Wages Details
    time_request_details = EmployeeTimeRequest.objects(_id=ObjectId(time_request_details_id)).first()
    employee_data = EmployeeDetails.objects(_id=time_request_details.attendance_id.employee_details_id._id).first()
    # employee_attendance.basic_monthly_salary = basic_monthly_salary
    calendar_working_days = CompanyDetails.objects(user_id=time_request_details.company_id.id).only('working_days',
                                                                                                    'daily_working_hour').first()
    # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
    # Todo: Check for the schedule in order to get total working hours of employee or else get default working hour from WTs
    existing_schedule = CompanyEmployeeSchedule.objects(
        employee_id=time_request_details.attendance_id.employee_details_id._id,
        schedule_from=time_request_details.attendance_id.attendance_date).first()
    if existing_schedule:
        total_working_hours = existing_schedule.work_timings.total_working_hour
    else:
        # Default Work Timings
        if not employee_data.employee_company_details.work_timing:
            default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,
                                                       is_default=True).first()
        else:
            default_work_timings = employee_data.employee_company_details.work_timing

        # default_work_timings = WorkTimings.objects(company_id=time_request_details.company_id.id,is_default=True).first() 

        total_working_hours = default_work_timings.total_working_hour

    total_working_hour = datetime.strptime(total_working_hours, '%I:%M:%S')

    calender_working_hour = float(calendar_working_days.daily_working_hour) * 60
    # Convert In minutes
    working_hour = (total_working_hour.hour * 60 + total_working_hour.minute)
    # Daily Working Hour in Minutes 

    daily_working_hour = working_hour if working_hour else calender_working_hour  # Default Set to daily_working_hour

    time_off_balance = 0.0
    start_of_month = time_request_details.attendance_id.attendance_date.replace(day=1, minute=0, hour=0, second=0,
                                                                                microsecond=0)

    if time_request_details.request_type == 'early' or time_request_details.request_type == 'late':
        if time_request_details.request_type == 'early':
            # Todo: Check if the Deduction Reason Exist or else Create a new;
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,
                                                                 adjustment_reason="Early Departure").first()
            if not adjustment_reason:
                adjustment_reason = create_adjustment_reason(time_request_details.company_id.id, "Early Departure",
                                                             "deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            # adjustment_amount = (hourly_rate/60)*float(time_request_details.attendance_id.approved_early_minutes)
            extra_time = int(time_request_details.attendance_id.approved_early_minutes)
            time_off_balance = extra_time / daily_working_hour

            # adjustment_amount = round((hourly_rate/60)*float(time_request_details.attendance_id.approved_early_minutes),2)

        elif time_request_details.request_type == 'late':
            adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,
                                                                 adjustment_reason="Late Arrival").first()
            if not adjustment_reason:
                adjustment_reason = create_adjustment_reason(time_request_details.company_id.id, "Late Arrival",
                                                             "deduction")
            # Desired Formula for Calculating the lates/tardiness is Lates/Dardines = Hourly Rate/60 x Total No of Minutes Late (Convert hours to minutes)
            # adjustment_amount =  (hourly_rate/60)*float(time_request_details.attendance_id.approved_late_minutes)
            extra_time = int(time_request_details.attendance_id.approved_late_minutes)
            time_off_balance = extra_time / daily_working_hour

            # adjustment_amount =  round((hourly_rate/60)*float(time_request_details.attendance_id.approved_late_minutes),2)

    elif time_request_details.request_type == 'overtime':
        adjustment_reason = CompanyAdjustmentReasons.objects(company_id=time_request_details.company_id.id,
                                                             adjustment_reason="Extra Hours").first()
        if not adjustment_reason:
            adjustment_reason = create_adjustment_reason(time_request_details.company_id.id, "Extra Hours", "addition")

        extra_time = int(time_request_details.attendance_id.approved_ot_minutes)
        time_off_balance = extra_time / daily_working_hour

    # Todo: Create a CPA Record
    if time_off_balance > 0:
        new_data = CompanyTimeOffAdjustment(
            company_id=time_request_details.company_id.id,
            employee_details_id=time_request_details.attendance_id.employee_details_id._id,
            adjustment_reason_id=adjustment_reason._id,
            adjustment_type='increment' if adjustment_reason.adjustment_type == "addition" else 'decrement',
            time_request_details_id=time_request_details_id,
            time_off_balance=float(time_off_balance),
            approved_minutes=extra_time,
            daily_working_hour=daily_working_hour
        )
        status = new_data.save()

    return True


def create_adjustment_reason(company_id, adjustement_reason, adjustment_type):
    # Todo: Check for the time approver if exist create record else return false; 
    new_adjustment_reason = CompanyAdjustmentReasons()
    new_adjustment_reason.company_id = company_id
    new_adjustment_reason.adjustment_reason = adjustement_reason
    new_adjustment_reason.adjustment_type = adjustment_type
    new_adjustment_reason.save()
    update_details = CompanyDetails.objects(user_id=company_id).update(
        push__adjustment_reasons=new_adjustment_reason.id)

    return new_adjustment_reason


@employee.route('/request/extratime/', methods=['POST'])
def request_extratime():
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        employee_details_id = request.form.get('employee_details_id')
        attendance_id = request.form.get('employee_attendance_id')
        if employee_details_id:
            employee_details = EmployeeDetails.objects(_id=ObjectId(employee_details_id)).only(
                'employee_company_details').first()
            time_request = create_time_request(ObjectId(company_id), ObjectId(attendance_id),
                                               employee_details.employee_company_details.department, 'overtime')
        if time_request:
            msg = json.dumps({"status": "success"})
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg = json.dumps({"status": "failed"})
            msghtml = json.loads(msg)
            return msghtml
    else:
        return redirect(url_for('employee.profile'))


@employee.route('/attendancehistory', methods=["GET", "POST"])
@login_required
@roles_accepted('employee')
def attendance_history():
    if request.method == "POST":
        attendance_from = request.form.get('attendance_date_from')
        attendance_to = request.form.get('attendance_date_to')

        start_of_month = datetime.strptime(attendance_from, '%d/%m/%Y')
        end_of_the_month = datetime.strptime(attendance_to, '%d/%m/%Y')

        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        monthly_att_data = EmployeeAttendance.objects(company_id=ObjectId(employee_details.company_id),
                                                      employee_details_id=ObjectId(employee_details._id),
                                                      attendance_date__gte=start_of_month,
                                                      attendance_date__lte=end_of_the_month).order_by(
            '-attendance_date')

    else:
        start_of_month = datetime.today().replace(day=1, minute=0, hour=0, second=0, microsecond=0)
        nxt_mnth = start_of_month.replace(day=28) + timedelta(days=4)
        end_of_the_month = nxt_mnth - timedelta(days=nxt_mnth.day)
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        monthly_att_data = EmployeeAttendance.objects(company_id=ObjectId(employee_details.company_id),
                                                      employee_details_id=ObjectId(employee_details._id),
                                                      attendance_date__gte=start_of_month,
                                                      attendance_date__lte=end_of_the_month).order_by(
            '-attendance_date')

    return render_template('employee/attendance_history.html', employee_details=employee_details,
                           attendance_history=monthly_att_data, start=start_of_month, end=end_of_the_month)


@employee.route('/reimbursement')
@login_required
@roles_accepted('employee')
def reimbursement():
    employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
    reimbursement_data = EmployeeReimbursement.objects(employee_details_id=employee_details._id)
    return render_template('employee/reimbursement.html', employee_details=employee_details,
                           reimbursement_data=reimbursement_data)


@employee.route('/create/reimbursement', methods=['GET', 'POST'])
@roles_accepted('admin', 'company', 'expensemanager')
@login_required
def create_reimbursement():
    company_details = CompanyDetails.objects(user_id=current_user.id).only('employees', 'adjustment_reasons',
                                                                           'company_name').first()
    company_id = current_user.id
    if not company_details:
        employee_details = EmployeeDetails.objects(user_id=current_user.id).first()
        company_details = CompanyDetails.objects(user_id=employee_details.company_id).only('adjustment_reasons',
                                                                                           'company_name').first()
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

            for item in range(0, total_adjustments):
                adjustment_reason = adjustment_reason_list[item]
                adjustment_on = datetime.strptime(adjustment_on_list[item], '%d/%m/%Y')
                adjustment_amount = adjustment_amount_list[item]
                adjustment_document = adjustment_document_list[item]

                if adjustment_reason:
                    flag = True
                    adjustment_reason_details = CompanyAdjustmentReasons.objects(
                        _id=ObjectId(adjustment_reason)).first()
                    if adjustment_reason_details:
                        # Create a new record for payroll adjustment
                        # todo: Check if the payment is recurring; if recurring then create all the records of the terms with their respective amounts
                        adjustment_document_name = ""
                        if adjustment_document:
                            adjustment_document_name = upload_adjustment_document(adjustment_document,
                                                                                  company_details.company_name)

                        new_data = EmployeeReimbursement(
                            company_id=company_id,
                            employee_details_id=employee_details._id,
                            adjustment_reason_id=adjustment_reason_details._id,
                            adjustment_type=adjustment_reason_details.adjustment_type,
                            reimbursement_amount=adjustment_amount,
                            reimbursement_document=adjustment_document_name,
                            reimbursement_on=adjustment_on
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
        start_of_month = datetime.today().replace(day=1, minute=0, hour=0, second=0, microsecond=0)
        return render_template('employee/create_reimbursement.html', company_details=company_details,
                               start_of_month=start_of_month)


def upload_adjustment_document(file, company_name):
    fname = ''
    if file:
        filename = secure_filename(file.filename)
        fn = os.path.splitext(filename)[0]
        file_ext = str.lower(os.path.splitext(filename)[1])
        fname = fn + str(uuid.uuid4()) + file_ext
        if file_ext not in current_app.config['UPLOAD_REIMBURSEMENT_DOCUMENT_EXTENSIONS']:
            flash('Please insert document with desired format!')
            return redirect(url_for('employee.reimbursement'))
        file_path = current_app.config['UPLOAD_DOCUMENT_FOLDER'] + company_name.strip() + '/adjustments/'
        # if not os.path.exists(app.config['UPLOAD_DOCUMENT_FOLDER']):
        #     os.makedirs(app.config['UPLOAD_DOCUMENT_FOLDER'])
        # file.save(os.path.join(app.config['UPLOAD_DOCUMENT_FOLDER'], fname))
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        file.save(os.path.join(file_path, fname))
    return fname


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


@employee.route('/superapproveleaverequest', methods=['POST'])
def super_approve_leave_request():
    leave_request_id = request.form.get('leave_request_id')
    comment = request.form.get('approver_comment')
    new_leave_till = None
    new_leave_from = None

    has_edited = request.form.get('edit_leave_date')
    if has_edited:
        new_leave_range = request.form.get('daterange').split(' - ')
        new_leave_from = datetime.strptime(new_leave_range[0], '%d/%m/%Y')
        new_leave_till = datetime.strptime(new_leave_range[1], '%d/%m/%Y')
        new_no_of_days = request.form.get('no_of_days')
        delta = new_leave_till - new_leave_from
        no_of_days = delta.days

    if leave_request_id:
        leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
        # check if the data exist or not 
        if leave_request_details:
            leave_application_details = EmployeeLeaveApplication.objects(
                _id=leave_request_details.employee_leave_app_id._id).first()
            if comment:
                super_employee = EmployeeDetails.objects(user_id=current_user.id).first()
                super_approver_details = SuperLeaveApprovers.objects(employee_details_id=super_employee._id).first()
                leave_application_details.update(is_super_approved=True, super_approver_comment=comment,
                                                 super_approver=super_approver_details._id)
            # if edited the leave dates update those
            if has_edited:
                leave_application_details.update(leave_from=new_leave_from, leave_till=new_leave_till,
                                                 no_of_days=new_no_of_days)

                # Final approver
            # Todo: Check if the user has the balance to be able to get approved
            current_leave_balance = leave_application_details.employee_leave_policy.balance
            asking_leave_days = int(leave_application_details.no_of_days)
            # if True:
            if (current_leave_balance >= asking_leave_days):  #Todo: This condition need to be checked
                # if True:
                # Todo: Change the leave status of both the application and request
                # leave_request_details.request_status = "approved"
                # leave_request_details.approved_on = datetime.now()
                leave_request_details.update(request_status="approved", approved_on=datetime.now(), comment=comment)
                leave_policy_details = EmployeeLeavePolicies.objects(
                    _id=leave_application_details.employee_leave_policy._id).first()

                # ---end of gathering data for leave adjustment----

                adj_days = str(asking_leave_days if not has_edited else new_no_of_days)
                after_adj = str(current_leave_balance - float(adj_days))

                new_data = EmployeeLeaveAdjustment(
                    company_id=leave_policy_details.company_id,
                    employee_details_id=leave_policy_details.employee_details_id,
                    employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
                    adjustment_type='decrement',
                    adjustment_days=adj_days,
                    adjustment_comment=str(comment),
                    before_adjustment=str(current_leave_balance),
                    after_adjustment=after_adj
                )
                status = new_data.save()

                leave_application_details.update(leave_adjustment=new_data._id)
                leave_application_details.save()

                # --------------------------end of creating leave adjustment---------------------------------

                # Todo: Deduct the leave balance
                new_balance = current_leave_balance - asking_leave_days
                if leave_policy_details:
                    leave_policy_details.update(balance=new_balance)
                # if any Comment By the Approver

                leave_application_details.update(current_approval_level="", leave_status="approved",
                                                 balance_before_approval=current_leave_balance,
                                                 balance_after_approval=new_balance, approved_on=datetime.now())
                # Todo: Add the record in the Shift Scheduler
                # Firstly get the day off worktimings details, if not exist create one??
                work_timings = WorkTimings.objects(is_day_off=True,
                                                   company_id=leave_application_details.company_id.id).first()
                if not work_timings:
                    # Create a new work timings of day off data
                    work_timings = WorkTimings(name="Day Off",
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
                    update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(
                        push__worktimings=work_timings._id)

                # .................send an email to the leave applicant about approval ...........
                send_approval_email(leave_application_details, comment, has_edited)

                #.................end of sending email.............................................

                start_date = leave_application_details.leave_from
                end_date = leave_application_details.leave_till
                while start_date <= end_date:
                    is_already_scheduled = CompanyEmployeeSchedule.objects(work_timings=work_timings._id,
                                                                           employee_id=leave_application_details.employee_details_id._id,
                                                                           schedule_from=start_date,
                                                                           schedule_till=start_date).first()
                    if not is_already_scheduled:
                        employee_schedule = CompanyEmployeeSchedule(company_id=leave_application_details.company_id.id,
                                                                    work_timings=work_timings._id,
                                                                    employee_id=leave_application_details.employee_details_id._id,
                                                                    schedule_from=start_date,
                                                                    schedule_till=start_date,
                                                                    allow_outside_checkin=False,
                                                                    is_leave=True,
                                                                    leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
                                                                    )
                        employee_schedule.save()
                        update_details = CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(
                            push__employee_schedules=employee_schedule._id)
                        # Add attendance Data as well
                        employee_attendance = EmployeeAttendance()
                        employee_attendance.employee_id = leave_application_details.employee_details_id.employee_company_details.employee_id
                        employee_attendance.employee_details_id = leave_application_details.employee_details_id._id
                        employee_attendance.attendance_date = start_date
                        employee_attendance.company_id = leave_application_details.company_id.id
                        employee_attendance.leave_name = leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
                        employee_attendance.attendance_status = "absent"
                        employee_attendance.save()
                    # start_date = start_date + timedelta(days=1)
                    # todo: Create an adjustment record if the leave policy type is unpaid
                    if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
                        start_of_month = start_date.replace(day=1)
                        nxt_mnth = start_date.replace(day=28) + timedelta(days=4)
                        # subtracting the days from next month date to
                        # get last date of current Month
                        end_of_the_month = nxt_mnth - timedelta(days=nxt_mnth.day)
                        # Todo: Create a adjustment record by deducting the off day amount
                        # Check if the adjustment reason is defined if not create a adjustment reason for Unpaid Leaves
                        adjustment_reason = CompanyAdjustmentReasons.objects(
                            company_id=leave_application_details.company_id.id,
                            adjustment_reason="Unpaid Leaves").first()
                        if not adjustment_reason:
                            adjustment_reason = create_adjustment_reason(leave_application_details.company_id.id,
                                                                         "Unpaid Leaves", "deduction")

                        # Todo: Calculate the daily wage of employee based on no of days in config or by default no of days on payroll month;
                        total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary

                        current_month = start_date.strftime('%B')

                        calendar_working_days = CompanyDetails.objects(
                            user_id=leave_application_details.company_id.id).only('working_days').first()
                        # Go through Working Days to find out the no of working Days in Calendar Month of Employee Checked in  
                        working_days = list(
                            filter(lambda x: x['month'] == current_month.lower(), calendar_working_days.working_days))

                        no_of_working_days = int(working_days[0][
                                                     'days']) if working_days else end_of_the_month.days()  # By Default Set to 30 Days

                        adjustment_amount = round(int(total_salary) / no_of_working_days, 0)

                        adjustment_exists = CompanyPayrollAdjustment.objects(
                            company_id=leave_application_details.company_id.id,
                            employee_details_id=leave_application_details.employee_details_id._id,
                            adjustment_reason_id=adjustment_reason._id,
                            attendance_date=start_date).first()
                        if adjustment_exists:
                            adjustment_exists.delete()

                        new_data = CompanyPayrollAdjustment(
                            company_id=leave_application_details.company_id.id,
                            employee_details_id=leave_application_details.employee_details_id._id,
                            adjustment_reason_id=adjustment_reason._id,
                            adjustment_type=adjustment_reason.adjustment_type,
                            adjustment_amount=str(adjustment_amount),
                            adjustment_on=start_of_month,
                            adjustment_month_on_payroll=start_of_month.strftime('%B'),
                            adjustment_year_on_payroll=start_of_month.year,
                            attendance_date=start_date,
                        )
                        new_data.save()
                    start_date = start_date + timedelta(days=1)
            else:
                msg = json.dumps({"status": "failed"})
                msghtml = json.loads(msg)
                return msghtml
                # Pass the approval proocess to next approver

            msg = json.dumps({'status': 'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg = json.dumps({"status": "failed"})
        msghtml = json.loads(msg)
        return msghtml


@employee.route('/superrejectleaverequest', methods=['POST'])
def super_reject_leave_request():
    leave_request_id = request.form.get('leave_request_id')
    leave_reject_reason = request.form.get('leave_reject_reason')
    if leave_request_id:
        leave_request_details = EmployeeLeaveRequest.objects(_id=ObjectId(leave_request_id)).first()
        # check if the data exist or not 
        if leave_request_details:
            leave_application_details = EmployeeLeaveApplication.objects(
                _id=leave_request_details.employee_leave_app_id._id).first()
            # Change the status of LeaveRequest by the previous/Current approver
            leave_request_details.update(request_status="rejected", rejected_on=datetime.now())

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

            msg = json.dumps({'status': 'success'})
            msghtml = json.loads(msg)
            return msghtml
    else:
        msg = json.dumps({"status": "failed"})
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
                    'approved_on': item.approved_on.strftime('%b %d') if hasattr(item, 'approved_on') else '',
                    'comment': item.comment,
                    'approver_name': item.approver_id.employee_details_id.first_name + ' ' + item.approver_id.employee_details_id.last_name,
                    'status': item.request_status,
                }
                data.append(details)

        # attendance_data = loads(attendance_details.to_json())
        msg = json.dumps({'status': 'success', 'details': data})
        msghtml = json.loads(msg)
        return msghtml
    else:
        msg = json.dumps({"status": "failed"})
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
        company_details = CompanyDetails.objects(user_id=leave_application_details.company_id).only(
            'email_config').first()
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
            html = render_template('email/leave_notification.html', leave_application_details=leave_application_details,
                                   approver_name=approver_name)
            msg = Message('Leave Application Approval Required! | Cubes HRMS',
                          sender=("Cubes HRMS", current_app.config['MAIL_USERNAME']), recipients=[receiver_email])
            msg.html = html
            mail.send(msg)
            return True


@employee.route("/process_pending_leaves", methods=['GET'])
def process_pending_requests():
    result = process_pending_leave_requests()

    # return json response to browser
    return jsonify(result)
