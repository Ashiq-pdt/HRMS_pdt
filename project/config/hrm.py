import urllib
from datetime import timedelta
from celery.schedules import crontab


class AppConfig:

    def __init__ (self, env):
        self.env = env

    celery_conf_beat_schedule = {
        'check-document-expiration': {
            'task': 'Check-Document-Expiration',
            'schedule': timedelta(days=1),
        },
        'pending-leave-approval-email': {
            'task': 'Leave-Approval-Email',
            'schedule': timedelta(days=1),
        },
        'weekly-pending-leave-approval-email': {
            'task': 'Weekly-Leave-Approval-Email',  # Replace with the actual task function
            'schedule': crontab(day_of_week=0, minute=0, hour=0) #this will run at 4:00 AM in morning if set as 1 ie Monday minute 0 hour 0 
        },
        'weekly-pending-leave-approval-email': {
            'task': 'Weekly-Leave-Approval-Email',  # Replace with the actual task function
            'schedule': crontab(day_of_week=0, minute=0, hour=0) #this will run at 4:00 AM in morning if set as 1 ie Monday minute 0 hour 0 
        },
        'monthly-leave-accrual': {
            'task': 'Monthly-Accrual-Leaves',  # Replace with the actual task function
            'schedule': crontab(day_of_month='1', minute=0, hour=0) #this will run at 12AM of Start of Month 
        },
        'yearly-leave-reset': {
        'task': 'Yearly-Reset-Leaves',  # Replace with the actual task function
        'schedule': crontab(month_of_year=1, day_of_month=1, minute=0, hour=0)#this will run at 12AM of Start of Month 
        }
    } 

    app_config_server_name = '127.0.0.1:5000'

    app_config_login_url_mail = 'hrms.cubes-intl.com'

    db_uri="mongodb://localhost:27017/hrm-test-db-live_latest"


    # app_config_server_name = 'hrms.cubes-intl.com'

    # app_config_login_url_mail = 'hrms.cubes-intl.com'

    # db_uri = "mongodb://hrms_live:Pdtcubes0913!hrms_live@127.0.0.1:27017/hrms_live"

