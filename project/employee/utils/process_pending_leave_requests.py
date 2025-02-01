from datetime import datetime, timedelta
from bson import ObjectId
from project.company.model import EmployeeLeaveRequest, EmployeeLeaveApplication, EmployeeAttendance

def process_pending_leave_requests():
    start_of_july = datetime(2024, 7, 1)
    end_of_july = datetime(2024, 7, 31, 23, 59, 59)
    approved_leave_requests = EmployeeLeaveRequest.objects(
        request_status="approved",
        approved_on__gte=start_of_july,
        approved_on__lte=end_of_july
    )

    # Debugging: Print the count of matching leave requests
    print(f"Found {approved_leave_requests.count()} approved leave requests for July 2024")

    for leave_request_details in approved_leave_requests:
        leave_application_details = EmployeeLeaveApplication.objects(
            _id=leave_request_details.employee_leave_app_id._id).first()

        if leave_application_details:
            create_attendance_records(leave_application_details)

    return {"status": "success", "message": "Pending leave requests for July 2024 processed"}

def create_attendance_records(leave_application_details):
    start_date = leave_application_details.leave_from
    end_date = leave_application_details.leave_till

    while start_date <= end_date:
        if not EmployeeAttendance.objects(employee_details_id=leave_application_details.employee_details_id._id,
                                          attendance_date=start_date).first():
            employee_attendance = EmployeeAttendance(
                employee_id=leave_application_details.employee_details_id.employee_company_details.employee_id,
                employee_details_id=leave_application_details.employee_details_id._id,
                attendance_date=start_date,
                company_id=leave_application_details.company_id.id,
                leave_name=leave_application_details.employee_leave_policy.leave_policy_id.leave_policy_name,
                attendance_status="absent"
            )
            employee_attendance.save()
            print(f"Attendance record created for date {start_date} and employee {leave_application_details.employee_details_id._id}")
        else:
            print(f"Attendance already exists for date {start_date} and employee {leave_application_details.employee_details_id._id}")

        start_date += timedelta(days=1)

