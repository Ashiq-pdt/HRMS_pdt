import logging
from celery import Celery, shared_task
from celery.schedules import crontab
from datetime import datetime
from datetime import timedelta
import sys
import os

# Add the parent directory of 'project' to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


current_date = datetime.now().date()
# from project.company.routes import monthly_accrual_leaves1

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Celery app
celery_app = Celery('celery_app', backend='redis://127.0.0.1:6379/0', broker='redis://127.0.0.1:6379/0')

# @shared_task
# def monthly_accrual_leaves():
#     logging.info("Running monthly leave accrual task.")
#     current_date = datetime.now()
#     formatted_date = current_date.strftime('%d/%m/%Y')
#     # monthly_accrual_leaves1(1,10,2024 )
#     print("Monthly accrual leaves task is being executed.")
#     return "Accrual leaves processed successfully!"


# Import your specific function
from tasks import run_monthly_accrual_leaves
@shared_task
def monthly_accrual_leaves():
    current_date = datetime.now()  # Use the current date
    day = current_date.day
    month = current_date.month
    year = current_date.year
    current_date = datetime(year, month, day)  # Use the passed date
    formatted_date = current_date.strftime('%d/%m/%Y')
    return run_monthly_accrual_leaves()  # Call the original function with the parameters

@shared_task
def yearly_reset_leaves():
    logging.info("Running yearly leave reset task.")
    # Your logic for yearly leave reset
    print("Yearly reset leaves task is being executed.")
    return "Yearly leaves reset successfully!"

# Beat schedule configuration
celery_app.conf.beat_schedule = {
    'monthly-leave-accrual': {
        'task': 'celery_app.monthly_accrual_leaves',  # Ensure this matches the full path to your task
         'schedule': crontab(minute='*'),  # Run every minute
    },
    'yearly-leave-reset': {
        'task': 'celery_app.yearly_reset_leaves',  # Ensure this matches the full path to your task
        'schedule': crontab(minute='0', hour='0', day_of_month='1', month_of_year='1'),  # Run at 12 AM on January 1st
    },
}

# celery_app.conf.beat_schedule = {
#         'check-document-expiration': {
#             'task': 'Check-Document-Expiration',
#             'schedule': timedelta(days=1),
#         },
#         'pending-leave-approval-email': {
#             'task': 'Leave-Approval-Email',
#             'schedule': timedelta(days=1),
#         },
#         'weekly-pending-leave-approval-email': {
#             'task': 'Weekly-Leave-Approval-Email',  # Replace with the actual task function
#             'schedule': crontab(day_of_week=0, minute=0, hour=0) #this will run at 4:00 AM in morning if set as 1 ie Monday minute 0 hour 0 
#         },
#         'weekly-pending-leave-approval-email': {
#             'task': 'Weekly-Leave-Approval-Email',  # Replace with the actual task function
#             'schedule': crontab(day_of_week=0, minute=0, hour=0) #this will run at 4:00 AM in morning if set as 1 ie Monday minute 0 hour 0 
#         },
#         'monthly-leave-accrual': {
#             'task': 'Monthly-Accrual-Leaves',  # Replace with the actual task function
#             'schedule': crontab(day_of_month='1', minute=0, hour=0) #this will run at 12AM of Start of Month 
#         },
#         'yearly-leave-reset': {
#         'task': 'Yearly-Reset-Leaves',  # Replace with the actual task function
#         'schedule': crontab(month_of_year=1, day_of_month=1, minute=0, hour=0)#this will run at 12AM of Start of Month 
#         }
#     } 

# Optionally: you can enable task time tracking if needed
celery_app.conf.task_track_started = True
