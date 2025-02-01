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
from .config.config_strategy import Config_Strategy


mail = Mail()
session = Session()

# generating dynamic config using .env settings. Used to provide values that differ between different environvemnts
dynamic_config_strategy = Config_Strategy()
dynamic_config = dynamic_config_strategy.get_dynamic_config()


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
    celery.conf.beat_schedule = dynamic_config.celery_conf_beat_schedule    
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

    app.config['SERVER_NAME'] = dynamic_config.app_config_server_name
    app.config['LOG_IN_URL_MAIL'] = dynamic_config.app_config_login_url_mail
    app.config['WTF_CSRF_TIME_LIMIT'] = 36000


    # 8KTDGOO60J
    app.config["SESSION_PERMANENT"] = True
    app.config["SESSION_TYPE"] = "filesystem"
    app.config['MAIL_SERVER']='smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USERNAME'] = 'donotreply.cubes@gmail.com'
    app.config['MAIL_PASSWORD'] = 'bnbqsumjnffqeblm'


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

    DB_URI = dynamic_config.db_uri

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

    if dynamic_config.env == "hrm":
        app.logger.debug("debug log info")
        app.logger.info("Info log information")
        app.logger.warning("Warning log info")
        app.logger.error("Error log info")
        app.logger.critical("Critical log info")


    error_templates(app)
    csrf = CSRFProtect(app)
    csrf.init_app(app)
    mail.init_app(app)
    session.init_app(app)
    # Setup Flask-Security
    security = Security(app, user_datastore)
    # security.init_app(app,user_datastore)

    # Create a user to test with
    # @app.before_first_request
    # def create_user():
    #     user_datastore.create_user(email='admin@pdtuae.com', password=generate_password_hash('password', method='sha256'),roles=['admin','company','employee'],type='admin')
    app.jinja_env.cache = {}
    return app

celery = create_celery_app(create_app())