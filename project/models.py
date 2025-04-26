# models.py

# from flask_login import UserMixin, RoleMixin
import datetime
from . import db
from bson import ObjectId
from mongoengine import *
from flask_mongoengine import BaseQuerySet
from flask_security import Security, MongoEngineUserDatastore, \
    UserMixin, RoleMixin, login_required
import pytz
class Role(db.Document, RoleMixin):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)

class User(db.DynamicDocument, UserMixin):
    email = db.StringField(max_length=255)
    password = db.StringField(max_length=255)
    active = db.BooleanField(default=True)
    active_till =  db.DateTimeField(default=None)
    confirmed = db.BooleanField(default=False)
    confirmed_at = db.DateTimeField(default=datetime.datetime.now)
    roles = db.ListField(db.ReferenceField(Role), default=[])
    type=db.StringField(choices=['admin','company','employee'])
    
user_datastore = MongoEngineUserDatastore(db, User, Role)

class Departments(db.EmbeddedDocument):
    dep_id = db.ObjectIdField(default=ObjectId, primary_key=True)
    department_name = db.StringField()

class Designations(db.EmbeddedDocument):
    designation_id = db.ObjectIdField(default=ObjectId, primary_key=True)
    designation_name = db.StringField()

class WorkTimings(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    name = db.StringField(max_length=80)
    office_start_at = db.StringField()
    office_end_at = db.StringField()
    is_half_day = db.BooleanField(default=False)
    late_arrival_later_than = db.StringField(default="0")
    early_departure_earliar_than = db.StringField(default="0")
    consider_absent_after = db.StringField(default="0")
    allow_breaks = db.StringField(default="0")
    is_day_off = db.BooleanField(default=False)
    out_of_office_check_in = db.BooleanField(default=False)
    created_at = db.DateTimeField(default=datetime.datetime.now)
    schedule_color = db.StringField(default="#0d6efd")
    minimum_ot = db.StringField(default="30")
    
    meta = { 'collection': 'work_timings', 'queryset_class': BaseQuerySet}
    
    def to_json(self):
        return {
            "_id": str(self.pk),
            "name": self.name,
            "office_start_at": self.office_start_at,
            "is_half_day": self.is_half_day,
            "late_arrival__later_than": self.late_arrival_later_than,
            "early_departure_earliar_than": self.early_departure_earliar_than,
            "consider_absent_after": self.consider_absent_after,
            "allow_breaks": self.allow_breaks,
            "out_of_office_check_in": self.out_of_office_check_in
        }
class CompanyOvertimePolicies(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    ot_policy_name = db.StringField()
    ot_policy_on = db.StringField()
    ot_policy_multiplier = db.StringField(default="1.5")
    is_default = db.BooleanField(default=False)
    
    
    meta = { 'collection': 'company_overtime_policies', 'queryset_class': BaseQuerySet}
        
class CompanyEmployeeSchedule(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    employee_id = db.ReferenceField('EmployeeDetails')
    work_timings = db.ReferenceField(WorkTimings)
    working_office = db.ReferenceField('CompanyOffices')
    company_id = db.ReferenceField('User')
    schedule_from = db.DateTimeField()
    schedule_till = db.DateTimeField()  
    allow_outside_checkin = db.BooleanField(default=False)
    
    meta = { 'collection': 'company_employee_schedules', 'queryset_class': BaseQuerySet}

class CompanyHolidays(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    occasion_date = db.DateTimeField()
    occasion_for = db.StringField()
    is_recurring = db.BooleanField(default=False)
    frequency = db.StringField(default="yearly")
    is_working_day = db.BooleanField(default=False)  
    ot_policy= db.ReferenceField('CompanyOvertimePolicies')
      
    
    meta = { 'collection': 'company_holidays', 'queryset_class': BaseQuerySet}

class CompanyOffices(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    office_name = db.StringField()
    location_name = db.StringField()
    location_radius = db.StringField(default="100")
    location_latitude = db.StringField()
    location_longitude = db.StringField()
    
    meta = { 'collection': 'company_offices_location', 'queryset_class': BaseQuerySet}

class CompanyAdjustmentReasons(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    adjustment_reason = db.StringField()
    adjustment_type = db.StringField()
    
    meta = { 'collection': 'company_adjustment_reasons', 'queryset_class': BaseQuerySet}

class CompanyClockInOptions(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    clock_in_from = db.StringField()
    outside_office = db.BooleanField(default=False)
    
    meta = { 'collection': 'company_clock_in_options', 'queryset_class': BaseQuerySet}
    
class SubCompanies(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    company_name = db.StringField()
    company_unique_id = db.StringField()
    company_account_number = db.StringField()
    company_routing_code = db.StringField()
    
    meta = { 'collection': 'sub_companies', 'queryset_class': BaseQuerySet}

class CompanyPayrollAdjustment(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    adjustment_reason_id = db.ReferenceField(CompanyAdjustmentReasons)
    adjustment_type = db.StringField()
    adjustment_amount = db.StringField()
    adjustment_document =  db.StringField(default="")
    created_at = db.DateTimeField(default=datetime.datetime.now)
    
    meta = { 'collection': 'company_payroll_adjustment', 'queryset_class': BaseQuerySet}

class CompanyTimeOffAdjustment(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    leave_policy_id = db.ReferenceField('CompanyLeavePolicies')
    adjustment_reason_id = db.ReferenceField(CompanyAdjustmentReasons)
    adjustment_type = db.StringField()
    time_off_balance = db.FloatField(default=0.0)
    daily_working_hour = db.IntField()
    approved_minutes = db.IntField()
    employee_leave_adjustments = db.ReferenceField('EmployeeLeaveAdjustment')
    time_request_details_id = db.ReferenceField('EmployeeTimeRequest')
    time_off_status = db.StringField(default="pending")
    leave_name = db.StringField(default='')
    created_at = db.DateTimeField(default=datetime.datetime.now)
    
    meta = { 'collection': 'company_time_off_adjustment', 'queryset_class': BaseQuerySet}
     
class CompanyPayroll(db.DynamicDocument):
       _id = db.ObjectIdField(default=ObjectId, primary_key=True)
       company_id = db.ReferenceField('User')
       employee_details_id = db.ReferenceField('EmployeeDetails')
       adjustment_additions = db.ListField(ReferenceField('CompanyPayrollAdjustment'),default=[])
       adjustment_deductions = db.ListField(ReferenceField('CompanyPayrollAdjustment'),default=[])
       total_deductions = db.DecimalField(default=0.0)
       total_additions = db.DecimalField(default=0.0)
       sif_details = db.ReferenceField('CompanySif')
       working_sub_company = db.ReferenceField('SubCompanies')
       
class CompanyEmailConfiguration(db.DynamicEmbeddedDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_email_host = db.StringField()
    company_email_port = db.StringField()
    company_email_user = db.StringField()
    company_email_password = db.StringField()
    company_email_name = db.StringField()
    company_email_from = db.StringField()
    company_email_tls = db.BooleanField(default=False)
    company_email_ssl = db.BooleanField(default=True)      
       
class CompanyLeavePolicies(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    leave_policy_name = db.StringField()
    allowance_days = db.StringField(default="0")
    allowance_type = db.StringField(default="annual")
    leave_type = db.StringField(default="paid")
    allow_on_probation = db.BooleanField(default=False)
    
    carry_over = db.BooleanField(default=False)
    non_probabtion_allowance_days = db.StringField(default="0")
    probabtion_allowance_days = db.StringField(default="0")

    meta = { 'collection': 'company_leave_policies', 'queryset_class': BaseQuerySet}
    
class CompanyLeaveApprovers(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    department_name = db.StringField()
    department_approval_level = db.StringField()
    approvers = db.ListField(ReferenceField('EmployeeLeaveApprover'),default=[])

    meta = { 'collection': 'company_leave_approvers', 'queryset_class': BaseQuerySet}
    
class CompanyTimeApprovers(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    department_name = db.StringField()
    approver = db.ReferenceField('EmployeeDetails')

    meta = { 'collection': 'company_time_approvers', 'queryset_class': BaseQuerySet}

class SuperLeaveApprovers(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    assigned_on = db.DateTimeField(default=datetime.datetime.now)
                 
class CompanyDetails(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_name = db.StringField()
    user_id = db.ReferenceField(User)
    email = db.StringField(unique=True)
    contact_no = db.StringField(max_length=15)
    employees = db.ListField(ReferenceField('EmployeeDetails'),default=[])
    # payment_id = db.StringField()
    # cancelled_subscription_on = db.DateTimeField(default=datetime.datetime.utcnow)
    no_of_employees = db.IntField(default=2)
    plan = db.StringField(default='trial')
    daily_working_hour = db.StringField(default='8.0')
    working_days= db.ListField()
    is_subscribed = db.BooleanField(default=False)
    departments = db.ListField(db.EmbeddedDocumentField('Departments'))
    designations = db.ListField(db.EmbeddedDocumentField('Designations'))
    worktimings = db.ListField(db.ReferenceField('WorkTimings'), default=[])
    employee_schedules = db.ListField(db.ReferenceField('CompanyEmployeeSchedule'), default=[])
    holidays = db.ListField(db.ReferenceField('CompanyHolidays'), default=[])
    overtime_policies = db.ListField(db.ReferenceField('CompanyOvertimePolicies'), default=[])
    offices = db.ListField(db.ReferenceField('CompanyOffices'), default=[])
    adjustment_reasons = db.ListField(db.ReferenceField('CompanyAdjustmentReasons'), default=[])
    clock_in_options = db.ListField(db.ReferenceField('CompanyClockInOptions'), default=[])
    leave_policies = db.ListField(db.ReferenceField('CompanyLeavePolicies'), default=[])
    leave_approvers = db.ListField(db.ReferenceField('CompanyLeaveApprovers'), default=[])
    time_approvers = db.ListField(db.ReferenceField('CompanyTimeApprovers'), default=[])
    company_roles = db.ListField(db.ReferenceField('CompanyRole'), default=[])
    company_memos = db.ListField(db.ReferenceField('CompanyMemo'), default=[])
    company_signatures = db.ListField(db.ReferenceField('CompanySignature'), default=[])
    company_exchanges = db.ListField(db.ReferenceField('CompanyExchange'), default=[])
    sub_companies = db.ListField(db.ReferenceField('SubCompanies'), default=[])
    email_config = db.EmbeddedDocumentField('CompanyEmailConfiguration')
    receiver_emails = db.StringField()
    super_leave_approvers = db.ListField(db.ReferenceField('SuperLeaveApprovers'), default=[])
    biometric_devices = db.ListField(db.ReferenceField('CompanyBiometricDevice'), default=[])
    

    disable_leave_application = db.BooleanField(default=False)
    
    def to_ajax_json(self):
            return {"worktiming_ajax": self.worktimings}    
    meta = { 'collection': 'company_details', 'queryset_class': BaseQuerySet}
    
    
class CompanyRole(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    role = db.ReferenceField('Role')
    assigned_on = db.DateTimeField(default=datetime.datetime.now)

class ActivityLog(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    log_user = db.ReferenceField('User')
    remote_addr = db.StringField()
    method = db.StringField()
    scheme = db.StringField()
    full_path = db.StringField()
    status = db.StringField()
    request_form = db.DynamicField()
    created_at = db.DateTimeField(default=datetime.datetime.now)
    
    meta = { 'collection': 'company_activity_log', 'queryset_class': BaseQuerySet}
    
class CompanyMemo(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    memo_title = db.StringField()
    memo_description = db.StringField()
    memo_attachment = db.StringField()
    memo_priority = db.StringField()
    memo_expiry = db.DateTimeField()
    created_at = db.DateTimeField(default=datetime.datetime.now)
    
    meta = { 'collection': 'company_memo', 'queryset_class': BaseQuerySet}
    
class BankDetails(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    bank_name = db.StringField()
    routing_code = db.StringField()
    
    meta = { 'collection': 'bank_details', 'queryset_class': BaseQuerySet}
    
    
class CompanySif(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    sif_type = db.StringField()
    pay_start = db.StringField()
    pay_end = db.StringField()
    days_in_month = db.StringField()
    salary = db.StringField()
    fixed_salary = db.StringField()
    variable_pay = db.FloatField(default=0.0)
    on_leave_days = db.StringField(default='0')
    sif_month = db.DateTimeField()
    created_at = db.DateTimeField(default=datetime.datetime.now)
    
    meta = { 'collection': 'company_sif', 'queryset_class': BaseQuerySet}

class CompanySignature(db.DynamicDocument):
   _id = db.ObjectIdField(default=ObjectId, primary_key=True)
   company_id = db.ReferenceField('User')
   employee_details_id = db.ReferenceField('EmployeeDetails')
   signature_path =  db.StringField()
   uploaded_on = db.DateTimeField(default=datetime.datetime.now)
   meta = { 'collection': 'company_signature', 'queryset_class': BaseQuerySet}
   
class CompanyExchange(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    exchange_name = db.StringField(default="")
    company_routing_code = db.StringField()
    
    meta = { 'collection': 'company_exchanges', 'queryset_class': BaseQuerySet}

class CompanyBiometricDevice(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    device_name = db.StringField()
    device_ip_address = db.StringField()
    device_port = db.StringField()
    device_username = db.StringField()
    device_password = db.StringField()
    device_index = db.StringField(default="")
    
    meta = { 'collection': 'company_biometric_devices', 'queryset_class': BaseQuerySet}

class CompanyBiometricAttendance(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_id = db.StringField()
    device_name = db.StringField()
    device_ip_address = db.StringField()
    device_port = db.StringField()
    attendance_date = db.DateTimeField()
    attendance_status = db.StringField()
    employee_check_in_at = db.DateTimeField(default_timezone=pytz.timezone('Asia/Dubai'))
    employee_check_out_at = db.DateTimeField(default_timezone=pytz.timezone('Asia/Dubai'))
    
    meta = { 'collection': 'company_biometric_attendance', 'queryset_class': BaseQuerySet}
