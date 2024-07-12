from datetime import timedelta, datetime

from bson import ObjectId
from ..model import EmployeeAttendance
from ...models import CompanyEmployeeSchedule, CompanyDetails, CompanyHolidays

def add_leave_schedules(start_date, end_date, leave_application, work_timings):
    while start_date <= end_date:
        employee_schedule = CompanyEmployeeSchedule(
            company_id=leave_application.company_id.id,
            work_timings=work_timings._id,
            employee_id=leave_application.employee_details_id._id,
            schedule_from=start_date,
            schedule_till=start_date,
            allow_outside_checkin=False,
            is_leave=True,
            leave_name=leave_application.employee_leave_policy.leave_policy_id.leave_policy_name
        )
        employee_schedule.save()
        CompanyDetails.objects(user_id=ObjectId(leave_application.company_id.id)).update(push__employee_schedules=employee_schedule._id)
        start_date += timedelta(days=1)

# Function to remove leave schedules
def remove_leave_schedules(start_date, end_date, leave_application, work_timings):
    while start_date <= end_date:
        employee_schedule = CompanyEmployeeSchedule.objects(
            company_id=leave_application.company_id.id,
            work_timings=work_timings._id,
            employee_id=leave_application.employee_details_id._id,
            schedule_from=start_date,
            schedule_till=start_date,
            allow_outside_checkin=False,
            is_leave=True,
            leave_name=leave_application.employee_leave_policy.leave_policy_id.leave_policy_name
        ).first()
        if employee_schedule:
            employee_schedule.delete()
        start_date += timedelta(days=1)


def add_sundays_to_attendace(data, start_date, end_date, employee_details):
    result = []
    attendance_map = {}
    attendance_dates = set()


    for day in data:
        attendance_map[day.attendance_date] = day
        attendance_dates.add(day.attendance_date)

    current_date = start_date
    while current_date <= end_date:
        is_holiday = CompanyHolidays.objects(occasion_date=current_date).first()
        is_on_leave = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,
                        schedule_from=current_date, is_leave=True).first()

        if current_date in attendance_dates and not is_holiday:
            result.append(attendance_map[current_date])

        else:
            if is_holiday:
                holiday_entry = {
                    'attendance_date': current_date,
                    'status': 'holiday',
                    'attendance_status': 'holiday',
                    'day_label':  is_holiday.occasion_for if is_holiday.occasion_for else "Unnamed Company Holiday" ,
                    'occasion_for': is_holiday.occasion_for if is_holiday.occasion_for else "Unnamed Company Holiday",
                    'employee_details_id': employee_details,
                    'break_history': [],
                    'total_hrs_worked': '0:0:0',
                    'working_from': 'week off',
                    'working_office': 'week off'
                }
                result.append(holiday_entry)

            elif current_date.weekday() == 6:  # Sunday
                holiday_entry = {
                    'attendance_date': current_date,
                    'status': 'dayoff',
                    'attendance_status': 'dayoff',
                    'day_label': 'Sunday',
                    'employee_details_id': employee_details,
                    'break_history': [],
                    'total_hrs_worked': '0:0:0',
                    'working_from': 'week off',
                    'working_office': 'week off'
                }
                result.append(holiday_entry)

            elif is_on_leave:
                leave_entry = {
                    'attendance_date': current_date,
                    'status': 'absent',
                    'attendance_status': 'absent',
                    'day_label': 'absent',
                    'employee_details_id': employee_details,
                    'break_history': [],
                    'total_hrs_worked': '0:0:0',
                    'working_from': 'absent',
                    'working_office': 'absent',
                    'leave_name': is_on_leave.leave_name
                }
                result.append(leave_entry)

            else:
                absence_entry = {
                    'attendance_date': current_date,
                    'status': 'absent',
                    'attendance_status': 'absent',
                    'day_label': 'absent',
                    'employee_details_id': employee_details,
                    'break_history': [],
                    'total_hrs_worked': '0:0:0',
                    'working_from': 'absent',
                    'working_office': 'absent',
                    'leave_name': ''
                }
                result.append(absence_entry)

        current_date += timedelta(days=1)

    return result

def add_workingdays_to_attendace(data, start_date, end_date, employee_details):
    result = []
    attendance_map = {}
    attendance_dates = set()
    late_count = 0


    for day in data:
        attendance_map[day.attendance_date] = day
        attendance_dates.add(day.attendance_date)

    current_date = start_date
    while current_date <= end_date:
        shedule_details = CompanyEmployeeSchedule.objects(employee_id=employee_details._id, schedule_from=current_date).first()
        is_holiday = CompanyHolidays.objects(occasion_date=current_date).first()
        is_on_leave = CompanyEmployeeSchedule.objects(employee_id=employee_details._id,
                        schedule_from=current_date, is_leave=True).first()

        if current_date in attendance_dates and not is_holiday:
            if (shedule_details):
                # count late comming
                office_start_time = datetime.strptime(shedule_details.work_timings.office_start_at, '%I:%M %p').time()

                # Subtract 15 minutes from employee_check_in_at
                grace_period = timedelta(minutes=15)
                adjusted_check_in_time = (attendance_map[current_date].employee_check_in_at - grace_period).time()

                if (office_start_time < adjusted_check_in_time):
                    late_count += 1

            result.append(attendance_map[current_date])

        else:
            if is_holiday:
                pass


            elif current_date.weekday() == 6:  # Sunday
                pass


            elif is_on_leave:
                leave_entry = {
                    'attendance_date': current_date,
                    'status': 'absent',
                    'attendance_status': 'absent',
                    'day_label': 'absent',
                    'employee_details_id': employee_details,
                    'break_history': [],
                    'total_hrs_worked': '0:0:0',
                    'working_from': 'absent',
                    'working_office': 'absent',
                    'leave_name': is_on_leave.leave_name
                }
                result.append(leave_entry)

            else:
                absence_entry = {
                    'attendance_date': current_date,
                    'status': 'absent',
                    'attendance_status': 'absent',
                    'day_label': 'absent',
                    'employee_details_id': employee_details,
                    'break_history': [],
                    'total_hrs_worked': '0:0:0',
                    'working_from': 'absent',
                    'working_office': 'absent',
                    'leave_name': ''
                }
                result.append(absence_entry)

        current_date += timedelta(days=1)

    return result, late_count


def add_sundays_to_attendace_company_level(data, start_date, end_date, employee_details):
    attendance_dates = [day.attendance_date for day in data]
    result = []

    current_date = start_date
    while current_date <= end_date:
        is_holiday = CompanyHolidays.objects(occasion_date=current_date).first()
        next_item_same_date = False

        if current_date.weekday() == 6:  # Sunday
            holiday_entry = {
                'attendance_date': current_date,
                'status': 'Holiday',
                'day_label': 'Sunday',
                'break_history': [],
                'total_hrs_worked': '0:0:0',
                'working_from': 'week off',
                'working_office': 'week off'
            }
            result.append(holiday_entry)

        elif is_holiday:
            holiday_entry = {
                'attendance_date': current_date,
                'status': 'holiday',
                'attendance_status': 'holiday',
                'day_label':  is_holiday.occasion_for if is_holiday.occasion_for else "Unnamed Company Holiday" ,
                'occasion_for': is_holiday.occasion_for if is_holiday.occasion_for else "Unnamed Company Holiday",
                'break_history': [],
                'total_hrs_worked': '0:0:0',
                'working_from': 'week off',
                'working_office': 'week off'
            }
            result.append(holiday_entry)
            
        else:
            if current_date in attendance_dates:
                attendance_dates.pop(0)
                for index, day in enumerate(data):
                    if day.attendance_date == current_date:
                        result.append(day)
                        data.pop(index)
                        if len(data):
                            next_item_same_date = data[index].attendance_date == current_date
                        else:
                            next_item_same_date = False

        current_date = current_date if next_item_same_date  else current_date + timedelta(days=1)

    return result

def count_sundays(start_date, end_date):
    # Initialize the count of Sundays
    sunday_count = 0
    total_days = 0
    # Iterate through the dates from start_date to end_date
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 6:  # 6 corresponds to Sunday
            sunday_count += 1
        current_date += timedelta(days=1)
        total_days += 1
    
    return sunday_count, total_days


def get_late_days_aggregate(company_id, employee_details_id, start_date, end_date, late_threshold):
    # Extract hour and minute from late_threshold
    late_threshold_hour = late_threshold.hour
    late_threshold_minute = late_threshold.minute

    # Access the collection
    collection = EmployeeAttendance._get_collection()

    # Define the aggregation pipeline
    pipeline = [
        {
            "$match": {
                "employee_details_id": employee_details_id,
                "attendance_date": {
                    "$gte": start_date,
                    "$lte": end_date
                },
                "employee_check_in_at": {"$ne": None}
            }
        },
        {
            "$project": {
                "attendance_date": 1,
                "employee_check_in_hour": {"$hour": "$employee_check_in_at"},
                "employee_check_in_minute": {"$minute": "$employee_check_in_at"}
            }
        },
        {
            "$match": {
                "$or": [
                    {"employee_check_in_hour": {"$gt": late_threshold_hour}},
                    {
                        "$and": [
                            {"employee_check_in_hour": {"$eq": late_threshold_hour}},
                            {"employee_check_in_minute": {"$gt": late_threshold_minute}}
                        ]
                    }
                ]
            }
        },
        {
            "$count": "late_days"
        }
    ]

    # Execute the aggregation pipeline
    result = list(collection.aggregate(pipeline))

    # Extract the count of late days
    late_days_count = result[0]['late_days'] if result else 0

    return late_days_count
