# init.py

from flask import Flask, render_template
from flask_login import LoginManager 
from flask_mail import Mail
import urllib
from werkzeug.security import generate_password_hash, check_password_hash

from flask_security import Security, MongoEngineUserDatastore, \
    UserMixin, RoleMixin, login_required

from flask_mongoengine import mongoengine as db
from flask_wtf.csrf import CSRFProtect
# init SQLAlchemy so we can use it later in our models
from celery import Celery
from celery.schedules import crontab
from flask_session import Session
from datetime import date, datetime, timedelta,time

mail = Mail()
session = Session()
def create_celery_app(app=None):
    app = app or create_app()
    
    celery = Celery(app.import_name,broker=app.config['CELERY_BROKER_URL'],backend=app.config['RESULT_BACKEND'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self,*args, **kwargs)
    celery.Task = ContextTask
    # Use Celery Beat to schedule the task to run daily
    celery.conf.beat_schedule = {
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
    },
    }     
    return celery

def error_templates(app=None):
    app = app or create_app()
    
    def render_status(status):
        code = getattr(status,'code',500)
        return render_template('errors/{0}.html'.format(code)),code
    
    for error in [400,401,403,404,500,503]:
        app.errorhandler(error)(render_status)
    
    return None

def create_app(settings_override=None):
    app = Flask(__name__)
    app.config['TIMEZONE'] = 'Asia/Muscat'
    app.secret_key = b'\xcc^\x91\xea\x17-\xd0W\x03\xa7\xf8J0\xac8\xc5'
    app.config['SECURITY_REGISTERABLE'] = 'True'
    app.config['SECURITY_PASSWORD_SALT'] = 'sahdbshdbacbahbcbshbcabcihbdiadibqiuwd'
    app.config['SECURITY_SEND_REGISTER_EMAIL'] = True
    app.config['SECURITY_RECOVERABLE'] = True
    app.config['SECURITY_CHANGEABLE'] = True
    app.config['SECURITY_TRACKABLE'] = True
    app.config['SECURITY_UNAUTHORIZED_VIEW '] = '/logout'
    app.config['SECURITY_MSG_UNAUTHORIZED'] =  (('You do not have permission to view/(perform action on) this resource.'), 'danger')
    
    app.config['SERVER_NAME'] = '127.0.0.1:5000'
    app.config['LOG_IN_URL_MAIL'] = 'pdthrms.cubes-intl.com'
    # app.config['SERVER_NAME'] = 'pdthrmapp.ml'
    app.config['WTF_CSRF_TIME_LIMIT'] = 36000
    
    # 8KTDGOO60J
    app.config["SESSION_PERMANENT"] = True
    app.config["SESSION_TYPE"] = "filesystem"
    # app.config['MAIL_SERVER']='smtp.mailtrap.io'
    # app.config['MAIL_PORT'] = 2525
    # app.config['MAIL_USERNAME'] = 'f692a1ac30a13c'
    # app.config['MAIL_PASSWORD'] = '0678ee020bbfd9'
    # app.config['MAIL_USE_TLS'] = True
    # app.config['MAIL_USE_SSL'] = False
    
    app.config['MAIL_SERVER']='smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USERNAME'] = 'donotreply.cubes@gmail.com'
    app.config['MAIL_PASSWORD'] = 'bnbqsumjnffqeblm'
    # bnbqsumjnffqeblm
    # app.config['MAIL_USERNAME'] = 'arslaanmuallim28@gmail.com'
    # app.config['MAIL_PASSWORD'] = 'wdmsqnagfkmjetju' #email pass for arslaanmuallim28
    
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True
    
    app.config.from_object('config.settings')
    app.config.from_pyfile('settings.py', silent=True)
    if settings_override:
        app.config.update(settings_override)
    
    app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.jpeg']
    app.config['UPLOAD_DOCUMENT_EXTENSIONS'] = ['.jpg', '.png', '.jpeg','.doc','.pdf','.docx']
    app.config['UPLOAD_REIMBURSEMENT_DOCUMENT_EXTENSIONS'] = ['.jpg', '.png', '.jpeg']
    app.config['UPLOAD_FOLDER'] = 'project/static/uploads/profile'
    app.config['UPLOAD_LETTER_FOLDER'] = 'project/static/uploads/letters'
    app.config['UPLOAD_DOCUMENT_FOLDER'] = 'project/static/uploads/documents/'
    
    app.config['UPLOAD_MEMO_DOCUMENT_FOLDER'] = 'project/static/uploads/memo/documents/'
    app.config['UPLOAD_FILE_EXTENSIONS'] = ['.csv']
    app.config['UPLOAD_FILE_FOLDER'] = 'project/static/uploads/documents/payroll/'
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

    # db.init_app(app)
    database_name = "pdt_uae_hrm"
    # Live
    # DB_URI = "mongodb+srv://pdtuae-hrm:"+urllib.parse.quote("pass@123")+"@cluster0.mf10u.mongodb.net/hrm-test-db?retryWrites=true&w=majority"
    # Local
    DB_URI = "mongodb+srv://pdtuae-hrm:"+urllib.parse.quote("pass@123")+"@cluster0.mf10u.mongodb.net/hrm?retryWrites=true&w=majority"
    # DB_URI = "mongodb+srv://pdtuae-hrm:"+urllib.parse.quote("pass@123")+"@cluster0.mf10u.mongodb.net/hrm-fen?retryWrites=true&w=majority"
    # DB_URI = "mongodb+srv://pdtuae-hrm:"+urllib.parse.quote("pass@123")+"@cluster0.mf10u.mongodb.net/db?retryWrites=true&w=majority"

    # DB_URI = "mongodb://localhost:27017/HRMS-TEST"

    # mongodb://localhost:27017
    db.connect(host=DB_URI)
    app.config['CELERY_BROKER_URL'] = 'redis://127.0.0.1:6379'
    app.config['RESULT_BACKEND'] = DB_URI
    app.config['task_soft_time_limit'] = 300
    app.config['max_retries'] = 5

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User,user_datastore

    @login_manager.user_loader
    def load_user(_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        # return User.query.get(int(user_id))
        return User.objects(_id=_id).exclude('employee').first()

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
     # blueprint for employees parts of app
    from .company.routes import company as company_blueprint
    app.register_blueprint(company_blueprint)
    
    # blueprint for employees parts of app
    from .employee.routes import employee as employee_blueprint
    app.register_blueprint(employee_blueprint)
    
    error_templates(app)
    csrf = CSRFProtect(app)  
    csrf.init_app(app)
    mail.init_app(app)
    session.init_app(app)
    # Setup Flask-Security
    # user_datastore = MongoEngineUserDatastore(db, User, Role)
    security = Security(app, user_datastore)
    # security.init_app(app,user_datastore)

    # Create a user to test with
    # @app.before_first_request
    # def create_user():
    #     user_datastore.create_user(email='admin@pdtuae.com', password=generate_password_hash('password', method='sha256'),roles=['admin','company','employee'],type='admin')
    app.jinja_env.cache = {}
    return app

celery = create_celery_app(create_app())