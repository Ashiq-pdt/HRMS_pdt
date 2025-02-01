import urllib
from celery.schedules import crontab


class AppConfig:
    def __init__ (self, env):
        self.env = env
    
    celery_conf_beat_schedule = {
        'monthly-leave-accrual': {
            'task': 'Monthly-Accrual-Leaves',  # Replace with the actual task function
            'schedule': crontab(day_of_month='1', minute=0, hour=0) #this will run at 12AM of Start of Month 
        },
        'yearly-leave-reset': {
        'task': 'Yearly-Reset-Leaves',  # Replace with the actual task function
        'schedule': crontab(month_of_year=1, day_of_month=1, minute=0, hour=0)#this will run at 12AM of Start of Month 
        },
    }

    app_config_server_name = '127.0.0.1:5000'

    app_config_login_url_mail = 'pdthrms.cubes-intl.com'

    db_uri = "mongodb+srv://pdtuae-hrm:"+urllib.parse.quote("pass@123")+"@cluster0.mf10u.mongodb.net/hrm?retryWrites=true&w=majority"

