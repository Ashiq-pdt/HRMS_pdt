from datetime import timedelta, datetime

from bson import ObjectId
from ..model import EmployeeAttendance, EmployeeDetails
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
                'status': 'Holiday',
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
            pass

        current_date = current_date + timedelta(days=1)

    for item in data:
        result.append(item)

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
    late_threshold_minute = 15

    employee_details = CompanyEmployeeSchedule.objects(employee_id = ObjectId(employee_details_id)).first()

    if employee_details:
        work_timings = getattr(employee_details, 'work_timings', None)
        late_arrival_str = getattr(employee_details.work_timings, 'late_arrival_later_than', None)

        if (work_timings and late_arrival_str):
            if int(employee_details.work_timings.late_arrival_later_than) > late_threshold_minute:
                late_threshold_minute = int(employee_details.work_timings.late_arrival_later_than)

    # Access the collection
    collection = EmployeeAttendance._get_collection()
    collection2 = CompanyEmployeeSchedule._get_collection()

    print(late_threshold_hour, late_threshold_minute)

    
    pipeline2 = [
        {
            "$match": {
                "company_id": ObjectId(company_id),  
                "attendance_date": {
                    "$gte": start_date,
                    "$lte": end_date
                },
                "employee_details_id": ObjectId(employee_details_id) 
            }
        },
        {
            "$lookup": {
                "from": "CompanyEmployeeSchedule",
                "let": { "att_date": "$attendance_date", "emp_id": "$employee_details_id" },
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    { "$eq": ["$employee_id", "$$emp_id"] },
                                    { "$eq": ["$start_date", "$$att_date"] }
                                ]
                            }
                        }
                    },
                    {
                        "$project": {
                            "office_starts_at": 1,
                            "late_threshold_minute": 1
                        }
                    }
                ],
                "as": "schedule"
            }
        },
        {
            "$unwind": "$schedule"
        },
        {
            "$addFields": {
                "adjusted_start_time": {
                    "$dateAdd": {
                        "startDate": "$schedule.office_starts_at",
                        "unit": "minute",
                        "amount": "$schedule.late_threshold_minute"
                    }
                }
            }
        },
        {
            "$addFields": {
                "is_late": {
                    "$gte": ["$employee_check_in_at", "$adjusted_start_time"]
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "late_count": {
                    "$sum": {
                        "$cond": ["$is_late", 1, 0]
                    }
                },
                "absent_count": {
                    "$sum": {
                        "$cond": ["$is_leave", 1, 0]
                    }
                }
            }
        }
    ]


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
    result = list(collection2.aggregate(pipeline2))

    # Extract the count of late days
    late_days_count = result[0]['late_days'] if result else 0

    return late_days_count


def get_set_of_absent_days(records, start_date, end_date):
    set_of_present_days = set(record.attendance_date for record in records)
    set_of_absent_days = set()
    while start_date < end_date:
        if (start_date not in set_of_present_days):
            set_of_absent_days.add(start_date)
        day = timedelta(days=1)
        start_date += day

    return set_of_absent_days

def generate_date_range(start_date, end_date):
    """Generate a list of dates between start_date and end_date."""
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date.date())
        current_date += timedelta(days=1)
    return date_list

def find_missing_attendance_records(company_id, start_date, end_date):
    # Step 1: Generate a set of all dates within the specified range, excluding Sundays
    all_dates = set()
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() != 6:  # Exclude Sundays (6 represents Sunday)
            all_dates.add(current_date)
        current_date += timedelta(days=1)

    # Step 2: Use the aggregation pipeline to find the dates with records
    pipeline = [
        {
            "$match": {
                "company_id": company_id,
                "attendance_date": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "employee_details_id": "$employee_details_id",
                    "attendance_date": "$attendance_date"
                }
            }
        },
        {
            "$project": {
                "employee_details_id": "$_id.employee_details_id",
                "attendance_date": "$_id.attendance_date",
                "_id": 0
            }
        }
    ]

    attendance_collection = EmployeeAttendance._get_collection()  # Update with your collection name

    existing_records = list(attendance_collection.aggregate(pipeline))

    # Step 3: Organize the existing dates by employee
    employee_dates = {}
    for record in existing_records:
        emp_id = record['employee_details_id']
        date = record['attendance_date']
        if emp_id not in employee_dates:
            employee_dates[emp_id] = set()
        employee_dates[emp_id].add(date)

    # Step 4: Generate the absent dates for each employee using set operations
    absent_dates = []
    for emp_id, present_dates in employee_dates.items():
        absent_dates_for_emp = all_dates - present_dates
        for date in absent_dates_for_emp:
            absent_dates.append({"date": date, "employee_details_id": emp_id})

    return absent_dates



def get_late_and_absent (emp_id, company_id, start_date, end_date):
    collection = EmployeeAttendance._get_collection()

    pipeline = [
        {
            "$match": {
                "employee_id": ObjectId(emp_id),
                "attendance_date": {
                    "$gte": start_date, 
                    "$lte": end_date 
                }
            }
        },
        {
            "$group": {
                "_id": None,
                "late_count": {
                    "$sum": {
                        "$cond": ["$is_late", 1, 0]
                    }
                },
                "absent_count": {
                    "$sum": {
                        "$cond": [
                            {
                                "$ne": ["$attendance_status", "present"]
                            },
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]

    return list(collection.aggregate(pipeline))


def get_employee_schedule_statistics(company_id, start_date, end_date, env):
    # Connect to the MongoDB client
    collection = EmployeeAttendance._get_collection()

    # Perform the aggregation query
    pipeline_pdt_hrm = [
        {
            "$match": {
                "attendance_date": {
                    "$gte": start_date.replace(hour=0, minute=0, second=0, microsecond=0),
                    "$lte": end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                },
                "company_id": ObjectId(company_id)
            }
        },
        {
            "$addFields": {
                "day_of_week": { "$dayOfWeek": "$attendance_date" }
            }
        },
        {
            "$match": {
                "day_of_week": { "$ne": 1 }  # Exclude Sundays
            }
        },
        {
            "$group": {
                "_id": "$employee_details_id",
                "late_count": {
                    "$sum": { "$cond": [ "$is_late", 1, 0 ] }
                },
                "absent_count": {
                    "$sum": {
                        "$cond": [
                            { "$ne": ["$attendance_status", "present"] },
                            1,
                            0
                        ]
                    }
                },
                "present_count": {
                    "$sum": {
                        "$cond": [
                            { "$eq": ["$attendance_status", "present"] },
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]

    pipeline_hrm = [
        {
            "$match": {
                "attendance_date": {
                    "$gte": start_date.replace(hour=0, minute=0, second=0, microsecond=0),
                    "$lte": end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                },
                "company_id": ObjectId(company_id)
            }
        },
        {
            "$group": {
                "_id": "$employee_details_id",
                "late_count": {
                    "$sum": { "$cond": [ "$is_late", 1, 0 ] }
                },
                "absent_count": {
                    "$sum": {
                        "$cond": [
                            { "$ne": ["$attendance_status", "present"] },
                            1,
                            0
                        ]
                    }
                },
                "present_count": {
                    "$sum": {
                        "$cond": [
                            { "$eq": ["$attendance_status", "present"] },
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]

    pipeline = pipeline_pdt_hrm if env == "pdthrm" else pipeline_hrm

    # Run the aggregation pipeline
    result = list(collection.aggregate(pipeline))

    return result
