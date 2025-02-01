
from datetime import datetime, timedelta
import json
from project.company.model import EmployeeAttendance, EmployeeLeaveAdjustment, EmployeeLeaveApplication, EmployeeLeaveApprover, EmployeeLeavePolicies, EmployeeLeaveRequest
from project.models import CompanyAdjustmentReasons, CompanyDetails, CompanyEmployeeSchedule, CompanyPayrollAdjustment, WorkTimings


def create_adjustment_reason(company_id, adjustement_reason, adjustment_type):
    # Todo: Check for the time approver if exist create record else return false;
    new_adjustment_reason = CompanyAdjustmentReasons()
    new_adjustment_reason.company_id = company_id
    new_adjustment_reason.adjustment_reason = adjustement_reason
    new_adjustment_reason.adjustment_type = adjustment_type
    new_adjustment_reason.save()
    update_details = CompanyDetails.objects(user_id=company_id).update(push__adjustment_reasons=new_adjustment_reason.id)
        
    return new_adjustment_reason   


def process_leave_request(leave_request_details, comment, request, current_app):
    comment = request.form.get('approver_comment')
    leave_application_details = get_leave_application(leave_request_details)
    if leave_application_details:
        if comment:
            leave_request_details.update(comment=comment)
            leave_application_details.update(push__approver_comments=leave_request_details._id)
        
        edit_leave_date = request.form.get("edit_leave_date")
        process_leave_editing(leave_application_details, request, edit_leave_date)
        handle_approval_process(leave_request_details, leave_application_details, comment, edit_leave_date, current_app)



def get_leave_application(leave_request_details):
    return EmployeeLeaveApplication.objects(_id=leave_request_details.employee_leave_app_id._id).first()


def process_leave_editing(leave_application_details, request, edit_leave_date):
    if edit_leave_date:
        new_leave_range = request.form.get('daterange').split(' - ')
        new_leave_from = datetime.strptime(new_leave_range[0], '%d/%m/%Y')
        new_leave_till = datetime.strptime(new_leave_range[1], '%d/%m/%Y')
        new_no_of_days = request.form.get('no_of_days')
        leave_application_details.update(
            leave_from=new_leave_from,
            leave_till=new_leave_till,
            no_of_days=new_no_of_days
        )


def handle_approval_process(leave_request_details, leave_application_details, comment, edit_leave_date, current_app):
    current_approval_level = leave_application_details.current_approval_level
    company_approval_level = leave_application_details.company_approval_level
    
    if current_approval_level == company_approval_level:
        handle_final_approver(leave_application_details, leave_request_details, comment, edit_leave_date, current_app)
    else:
        pass_to_next_approver(leave_application_details, leave_request_details)


def handle_final_approver(leave_application_details, leave_request_details, comment, edit_leave_date, current_app):
    current_leave_balance = leave_application_details.employee_leave_policy.balance
    asking_leave_days = int(leave_application_details.no_of_days)
    
    if current_leave_balance >= asking_leave_days:
        approve_leave(leave_application_details, leave_request_details, comment, asking_leave_days, edit_leave_date, current_leave_balance, current_app)
    else:
        return json.dumps({"status": "failed"})


def approve_leave(leave_application_details, leave_request_details, comment, asking_leave_days, edit_leave_date, current_leave_balance, current_app):
    leave_request_details.update(
        request_status="approved",
        approved_on=datetime.now(),
        comment=comment
    )
    new_balance = current_leave_balance - asking_leave_days
    update_leave_policy_balance(leave_application_details, new_balance)
    leave_application_details.update(
        current_approval_level="",
        leave_status="approved",
        balance_before_approval=current_leave_balance,
        balance_after_approval=new_balance,
        approved_on=datetime.now()
    )
    create_leave_adjustment(leave_application_details, asking_leave_days, current_leave_balance, new_balance, comment)
    schedule_employee_leave(leave_application_details)
    send_approval_email(leave_application_details, comment, edit_leave_date, current_app)


def update_leave_policy_balance(leave_application_details, new_balance):
    leave_policy_details = EmployeeLeavePolicies.objects(_id=leave_application_details.employee_leave_policy._id).first()
    if leave_policy_details:
        leave_policy_details.update(balance=new_balance)


def create_leave_adjustment(leave_application_details, asking_leave_days, current_leave_balance, new_balance, comment):
    adj_days = asking_leave_days
    after_adj = current_leave_balance - adj_days
    leave_policy_details = EmployeeLeavePolicies.objects(_id=leave_application_details.employee_leave_policy._id).first()
    
    new_data = EmployeeLeaveAdjustment(
        company_id=leave_policy_details.company_id,
        employee_details_id=leave_policy_details.employee_details_id,
        employee_leave_pol_id=leave_application_details.employee_leave_policy._id,
        adjustment_type='decrement',
        adjustment_days=str(adj_days),
        adjustment_comment=str(comment),
        before_adjustment=str(current_leave_balance),
        after_adjustment=str(after_adj)
    )
    new_data.save()
    leave_application_details.update(leave_adjustment=new_data._id)
    leave_application_details.save()


def schedule_employee_leave(leave_application_details):
    work_timings = get_or_create_work_timings(leave_application_details)
    start_date = leave_application_details.leave_from
    end_date = leave_application_details.leave_till
    
    while start_date <= end_date:
        schedule_date(work_timings, leave_application_details, start_date)
        if leave_application_details.employee_leave_policy.leave_policy_id.leave_type == "unpaid":
            create_unpaid_leave_adjustment(leave_application_details, start_date)
        start_date += timedelta(days=1)


def get_or_create_work_timings(leave_application_details):
    work_timings = WorkTimings.objects(is_day_off=True, company_id=leave_application_details.company_id.id).first()
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
        CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__worktimings=work_timings._id)
    return work_timings


def schedule_date(work_timings, leave_application_details, start_date):
    is_already_scheduled = CompanyEmployeeSchedule.objects(
        work_timings=work_timings._id,
        employee_id=leave_application_details.employee_details_id._id,
        schedule_from=start_date,
        schedule_till=start_date
    ).first()
    
    if not is_already_scheduled:
        employee_schedule = CompanyEmployeeSchedule(
            company_id=leave_application_details.company_id.id,
            work_timings=work_timings._id,
            employee_id=leave_application_details.employee_details_id._id,
            schedule_from=start_date,
            schedule_till=start_date,
            allow_outside_checkin=False,
            is_leave=True,
            leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name
        )
        employee_schedule.save()
        CompanyDetails.objects(user_id=leave_application_details.company_id.id).update(push__employee_schedules=employee_schedule._id)
        create_employee_attendance(leave_application_details, start_date)


def create_employee_attendance(leave_application_details, start_date):
    employee_attendance = EmployeeAttendance(
        employee_id=leave_application_details.employee_details_id.employee_company_details.employee_id,
        employee_details_id=leave_application_details.employee_details_id._id,
        attendance_date=start_date,
        company_id=leave_application_details.company_id.id,
        leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name,
        attendance_status="absent"
    )
    employee_attendance.save()


def create_unpaid_leave_adjustment(leave_application_details, start_date):
    start_of_month = start_date.replace(day=1)
    end_of_the_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    adjustment_reason = get_or_create_adjustment_reason(leave_application_details)
    total_salary = leave_application_details.employee_details_id.employee_company_details.total_salary
    current_month = start_date.strftime('%B')
    calendar_working_days = CompanyDetails.objects(user_id=leave_application_details.company_id.id).only('working_days').first()
    working_days = [d['days'] for d in calendar_working_days.working_days if d['month'] == current_month.lower()]
    no_of_working_days = int(working_days[0]) if working_days else end_of_the_month.day
    adjustment_amount = round(int(total_salary) / no_of_working_days, 0)
    
    existing_adjustment = CompanyPayrollAdjustment.objects(
        company_id=leave_application_details.company_id.id,
        employee_details_id=leave_application_details.employee_details_id._id,
        adjustment_reason_id=adjustment_reason._id,
        attendance_date=start_date
    ).first()
    if existing_adjustment:
        existing_adjustment.delete()
    
    new_data = CompanyPayrollAdjustment(
        company_id=leave_application_details.company_id.id,
        employee_details_id=leave_application_details.employee_details_id._id,
        adjustment_reason_id=adjustment_reason._id,
        adjustment_type=adjustment_reason.adjustment_type,
        adjustment_amount=str(adjustment_amount),
        adjustment_on=start_of_month,
        adjustment_month_on_payroll=start_of_month.strftime('%B'),
        adjustment_year_on_payroll=start_of_month.year,
        attendance_date=start_date
    )
    new_data.save()


def get_or_create_adjustment_reason(leave_application_details):
    adjustment_reason = CompanyAdjustmentReasons.objects(
        company_id=leave_application_details.company_id.id,
        adjustment_reason="Unpaid Leaves"
    ).first()
    if not adjustment_reason:
        adjustment_reason = create_adjustment_reason(
            leave_application_details.company_id.id, "Unpaid Leaves", "deduction"
        )
    return adjustment_reason


def send_approval_email(leave_application_details, comment, edit_leave_date, current_app):
    try:
        approver = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name
        email_template = 'email/leave_approved.html'
        data = {
            'employee_details_id': leave_application_details.employee_details_id,
            'type': leave_application_details.employee_leave_policy.leave_policy_id.leave_type,
            'start_date': leave_application_details.leave_from.strftime('%Y-%m-%d'),
            'end_date': leave_application_details.leave_till.strftime('%Y-%m-%d'),
            'no_of_days': leave_application_details.no_of_days,
            'is_modified': 'Yes' if edit_leave_date else 'No',
            'aprover_remarks': comment,
            'approver_name': approver,
            'status': 'accepted',
            'receiver_email': leave_application_details.employee_details_id.personal_email
        }
        from .email import send_email

        send_email(email_template, data, current_app)
    except Exception as e:
        print(f"An error occurred: {e}")


def pass_to_next_approver(leave_application_details, leave_request_details):
    next_approval_level = int(leave_application_details.current_approval_level) + 1
    department = leave_application_details.company_approver.department_name
    approver = EmployeeLeaveApprover.objects(
        employee_approval_level=str(next_approval_level),
        department_name=department,
        company_id=leave_application_details.company_id.id
    ).first()
    if approver:
        new_request_approver = EmployeeLeaveRequest(
            employee_leave_app_id=leave_application_details._id,
            company_id=leave_application_details.company_id.id,
            approver_id=approver._id
        )
        new_request_approver.save()
        leave_application_details.update(
            current_approval_level=str(next_approval_level),
            current_aprrover=new_request_approver._id,
            add_to_set__approver_list=new_request_approver._id
        )
        leave_request_details.update(request_status="approved", approved_on=datetime.now())
        # send_leave_approval_email.delay(str(leave_application_details._id))
