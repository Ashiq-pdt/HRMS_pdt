# models.py

# from flask_login import UserMixin, RoleMixin
import datetime
from random import choices
from secrets import choice
from .. import db
from bson import ObjectId
from mongoengine import *
from flask_mongoengine import BaseQuerySet
from ..models import User,CompanyOffices
from flask import Flask
import datetime


class EmployeeCompanyDetails(db.DynamicEmbeddedDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    employee_id = db.StringField(default=None)
    department = db.StringField()
    working_sub_company = db.ReferenceField('SubCompanies')
    designation = db.StringField(default=None)
    working_office = db.ReferenceField('CompanyOffices')
    work_timing = db.ReferenceField('WorkTimings')
    allow_outside_checkin = db.BooleanField(default=False)
    home_option = db.BooleanField(default=True)
    date_of_joining = db.StringField()
    probation_end_date = db.StringField()
    date_of_resignation = db.StringField()
    date_of_termination = db.StringField()
    credit_leaves = db.StringField()
    type = db.StringField()
    salary = db.StringField()
    fuel_allowance = db.IntField(default=0)
    mobile_allowance = db.IntField(default=0)
    medical_allowance = db.IntField(default=0)
    status = db.BooleanField(default=False)
    
class EmployeeBankDetails(db.DynamicEmbeddedDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    account_holder = db.StringField()
    account_no = db.StringField()
    bank_name = db.StringField()
    branch_location = db.StringField()
    ifsc_code = db.StringField()
    tax_id = db.StringField()
    routing_code = db.StringField()

class EmployeeDocuments(db.DynamicEmbeddedDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    document_type = db.StringField()
    document_name = db.StringField()
    document_expiry_on = db.DateTimeField(default=datetime.datetime.now)
    days_before_expiry_alert = db.StringField(default='90')
    document_remark = db.StringField(default='')
    email_alert_status = db.StringField(default='not_sent')
    email_alert_sent_on = db.DateTimeField(default=datetime.datetime.now)
    email_alert_message = db.StringField(default='')
    uploaded_on = db.DateTimeField(default=datetime.datetime.now)
 
class EmployeeLeavePolicies(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    leave_policy_id = db.ReferenceField('CompanyLeavePolicies')
    balance = db.FloatField(default=0.0)
    employee_leave_adjustments = db.ListField(db.ReferenceField('EmployeeLeaveAdjustment'))
    
    meta = { 'collection': 'employee_leaves', 'queryset_class': BaseQuerySet}   

class EmployeeLeaveAdjustment(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    employee_leave_pol_id = db.ReferenceField('EmployeeLeavePolicies')
    adjustment_type = db.StringField()
    adjustment_comment = db.StringField()
    adjustment_days = db.StringField()
    before_adjustment = db.StringField()
    after_adjustment = db.StringField()
    created_at = db.DateTimeField(default=datetime.datetime.now)
    modified_by = db.ReferenceField('EmployeeDetails')
    modified_on = db.DateTimeField(default=datetime.datetime.now)
    meta = { 'collection': 'employee_leave_adjustment', 'queryset_class': BaseQuerySet}
  
class EmployeeSifDetails(db.DynamicEmbeddedDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_exchange = db.ReferenceField('CompanyExchange')
    employee_mol_no = db.StringField()
    company_mol_no = db.StringField()
              
class EmployeeDetails(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    user_id = db.ReferenceField(User)
    first_name = db.StringField()
    last_name = db.StringField()
    father_name = db.StringField()
    contact_no = db.StringField()
    emergency_contact_no_1 = db.StringField()
    emergency_contact_no_2 = db.StringField()
    dob = db.StringField()
    gender = db.StringField()
    marital_status = db.StringField()
    blood_group = db.StringField()
    present_address = db.StringField()
    permanent_address = db.StringField()
    personal_email = db.StringField()
    passport_number = db.StringField()
    emirates_id_no = db.StringField()
    profile_pic = db.StringField()
    email_notification = db.BooleanField(default=False)
    is_deleted = db.BooleanField(default=False)
    is_approver = db.BooleanField(default=False)
    is_super_leave_approver = db.BooleanField(default=False)
    is_time_approver = db.BooleanField(default=False)
    employee_company_details = db.EmbeddedDocumentField('EmployeeCompanyDetails')
    employee_bank_details = db.EmbeddedDocumentField('EmployeeBankDetails')
    documents = db.ListField(db.EmbeddedDocumentField('EmployeeDocuments'),default=[])
    employee_leave_policies = db.ListField(db.ReferenceField('EmployeeLeavePolicies'))
    activity_history = db.ListField(db.ReferenceField('ActivityLog'))
    employee_sif_details = db.EmbeddedDocumentField('EmployeeSifDetails')
    

    meta = { 'collection': 'employee_details', 'queryset_class': BaseQuerySet}

    def to_dict(self):
        # Convert the document to a dictionary
        data = self.to_mongo().to_dict()
        # Convert ObjectId to string
        data['_id'] = str(data['_id'])
        data['user_id'] = str(data['user_id']) if data['user_id'] else None

        # Convert embedded documents and lists
        if self.employee_company_details:
            data['employee_company_details'] = self.employee_company_details.to_mongo().to_dict()
        if self.employee_bank_details:
            data['employee_bank_details'] = self.employee_bank_details.to_mongo().to_dict()
        if self.documents:
            data['documents'] = [doc.to_mongo().to_dict() for doc in self.documents]
        if self.employee_leave_policies:
            data['employee_leave_policies'] = [str(policy) for policy in self.employee_leave_policies]
        if self.activity_history:
            data['activity_history'] = [str(activity) for activity in self.activity_history]
        if self.employee_sif_details:
            data['employee_sif_details'] = self.employee_sif_details.to_mongo().to_dict()

        return data
    
    
class EmployeeAttendance(db.DynamicDocument):
   _id = db.ObjectIdField(default=ObjectId, primary_key=True)
   has_overtime = db.BooleanField(default=False)
   is_late = db.BooleanField(default=False)
   has_left_early = db.BooleanField(default=False)
   employee_details_id = db.ReferenceField(EmployeeDetails)
   break_history = db.ListField(db.ReferenceField('EmployeeBreakHistory'))
   working_from = db.ReferenceField('CompanyClockInOptions')
   on_break = db.BooleanField(default=False)
   working_office = db.ReferenceField('CompanyOffices')
   
   early_approval_status = db.BooleanField(default=False)
   late_approval_status = db.BooleanField(default=False)
   ot_approval_status = db.BooleanField(default=False)
   half_day = db.BooleanField(default=False)
   has_next_day_clockout = db.BooleanField(default=False)
   
   approved_late_minutes = db.StringField(default='0')
   approved_early_minutes = db.StringField(default='0')
   approved_ot_minutes = db.StringField(default='0')
   activity_history = db.ListField(db.ReferenceField('ActivityLog'))
   leave_name = db.StringField(default='')


   def to_json(self):

    return {
        "_id": str(self._id),
        "has_overtime": self.has_overtime,
        "is_late": self.is_late,
        "has_left_early": self.has_left_early,
        "employee_details_id": str(self.employee_details_id.id) if self.employee_details_id else None,
        "break_history": [str(break_history.id) for break_history in self.break_history],
        "working_from": str(self.working_from.id) if self.working_from else None,
        "on_break": self.on_break,
        "working_office": str(self.working_office.id) if self.working_office else None,
        "early_approval_status": self.early_approval_status,
        "late_approval_status": self.late_approval_status,
        "ot_approval_status": self.ot_approval_status,
        "half_day": self.half_day,
        "has_next_day_clockout": self.has_next_day_clockout,
        "approved_late_minutes": self.approved_late_minutes,
        "approved_early_minutes": self.approved_early_minutes,
        "approved_ot_minutes": self.approved_ot_minutes,
        "employee_check_in_at": self.employee_check_in_at,
        "activity_history": [str(activity.id) for activity in self.activity_history],
        "leave_name": self.leave_name
        
    }

    
   meta = { 'collection': 'employee_attendance', 'queryset_class': BaseQuerySet,"auto_create_index": False,"index_background": True,"indexes": ["employee_details_id","has_early_deduction","has_late_deduction","has_overtime","attendance_date"]}


class CeleryTaskMeta(db.DynamicDocument):
   status =  db.StringField()
   pass
   meta = { 'collection': 'celery_taskmeta', 'queryset_class': BaseQuerySet}
   

class ScheduledBackgroundTask(db.DynamicDocument):
   _id = db.ObjectIdField(default=ObjectId, primary_key=True)
   company_id = db.ReferenceField('User')
   task_type =  db.StringField()
   message =  db.StringField(default='The task has been ')
   celery_task_id = db.ReferenceField(CeleryTaskMeta)
   uploaded_on = db.DateTimeField()
   meta = { 'collection': 'celery_bg_tasks', 'queryset_class': BaseQuerySet}
   
class EmployeeLeaveApprover(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    department_name = db.StringField()
    employee_details_id = db.ReferenceField('EmployeeDetails')
    employee_approval_level = db.StringField() #1,2,3..

    meta = { 'collection': 'employee_leave_approver', 'queryset_class': BaseQuerySet}
    
class EmployeeLeaveApplication(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    leave_adjustment = db.ReferenceField('EmployeeLeaveAdjustment')
    no_of_days = db.StringField(default='1')
    leave_from = db.DateTimeField(default=datetime.datetime.now)
    leave_till = db.DateTimeField(default=datetime.datetime.now)
    employee_leave_policy = db.ReferenceField('EmployeeLeavePolicies') 
    reason = db.StringField()
    leave_status = db.StringField(default='pending')
    company_approver = db.ReferenceField('CompanyLeaveApprovers')
    current_aprrover = db.ReferenceField('EmployeeLeaveRequest')    
    application_on = db.DateTimeField(default=datetime.datetime.now)
    approver_comments = db.ListField(db.ReferenceField('EmployeeLeaveRequest'))
    approver_list = db.ListField(db.ReferenceField('EmployeeLeaveRequest'))
    is_super_approved = db.BooleanField(default=False)
    super_approver_comment = db.StringField(default='')
    super_approver = db.ReferenceField('SuperLeaveApprovers')
    emergency_contact = db.StringField(default='')
    contact_address = db.StringField(default='')
    modified_by = db.ReferenceField('EmployeeDetails')
    modified_on = db.DateTimeField(default=datetime.datetime.now)
    meta = { 'collection': 'employee_leave_application', 'queryset_class': BaseQuerySet}
    
class EmployeeLeaveRequest(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_leave_app_id = db.ReferenceField('EmployeeLeaveApplication')
    approver_id = db.ReferenceField('EmployeeLeaveApprover')
    request_status = db.StringField(default='pending')
    
    email_alert_status = db.StringField(default='not_sent')
    email_alert_sent_on = db.DateTimeField(default=datetime.datetime.now)
    email_alert_message = db.StringField(default='')
    email_alert_sent_count = db.IntField(default=0)
    comment = db.StringField(default='No Comment')
    
    meta = { 'collection': 'employee_leave_request', 'queryset_class': BaseQuerySet}
    
class EmployeeTimeRequest(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    attendance_id = db.ReferenceField('EmployeeAttendance')
    approver_id = db.ReferenceField('CompanyTimeApprovers')
    request_status = db.StringField(default='pending')
    request_type = db.StringField() # Late,OT,Early Departure
    
    meta = { 'collection': 'employee_time_request', 'queryset_class': BaseQuerySet}
    
class EmployeeReimbursement(db.DynamicDocument):
    _id = db.ObjectIdField(default=ObjectId, primary_key=True)
    company_id = db.ReferenceField('User')
    employee_details_id = db.ReferenceField('EmployeeDetails')
    adjustment_reason_id = db.ReferenceField('CompanyAdjustmentReasons')
    adjustment_type = db.StringField()
    reimbursement_amount = db.StringField()
    reimbursement_document =  db.StringField(default="")
    reimbursement_status =  db.StringField(default="pending")
    reimbursement_on = db.DateTimeField(default=datetime.datetime.now)
    created_at = db.DateTimeField(default=datetime.datetime.now)
    
    meta = { 'collection': 'employee_reimbursement', 'queryset_class': BaseQuerySet}    


class ValidEmbeddedDocument(db.EmbeddedDocument):
    enable = BooleanField(required=True)
    timeType = StringField(required=True)
    beginTime = DateTimeField(required=True)
    endTime = DateTimeField(required=True)

class RightPlanEmbeddedDocument(db.EmbeddedDocument):
    doorNo = IntField(required=True)
    planTemplateNo = StringField(required=True)

class BioMetricUserData(DynamicDocument):
    employeeNo = StringField(required=True, unique=True)
    name = StringField(required=True)
    userType = StringField(required=True)
    closeDelayEnabled = BooleanField(required=True)
    password = StringField(required=False)
    doorRight = StringField(required=True)
    maxOpenDoorTime = StringField(required=True)
    openDoorTime = StringField(required=True)
    localUIRight = BooleanField(required=True)
    userVerifyMode = StringField(required=False)
    deviceId = StringField(required=True)

    meta = {
        'collection': 'BioMetricUserData'
    }

class BioMetricActivity(DynamicDocument):
    internet_access = IntField(db_field='InternetAccess', default=0)
    mac_addr = StringField(db_field='MACAddr', default="")
    rs485_no = IntField(db_field='RS485No', default=0)
    access_channel = IntField(db_field='accessChannel', default=0)
    alarm_in_no = IntField(db_field='alarmInNo', default=0)
    alarm_out_no = IntField(db_field='alarmOutNo', default=0)
    attendance_status = StringField(db_field='attendanceStatus', default="checkIn")
    card_no = StringField(db_field='cardNo', default="")
    card_reader_kind = IntField(db_field='cardReaderKind', default=0)
    card_reader_no = IntField(db_field='cardReaderNo', default=1)
    card_type = IntField(db_field='cardType', default=1)
    case_sensor_no = IntField(db_field='caseSensorNo', default=0)
    device_no = IntField(db_field='deviceNo', default=0)
    distract_control_no = IntField(db_field='distractControlNo', default=0)
    door_no = IntField(db_field='doorNo', default=1)
    employee_no_string = StringField(db_field='employeeNoString')
    local_controller_id = IntField(db_field='localControllerID', default=0)
    major = IntField(db_field='major')
    minor = IntField(db_field='minor')
    multi_card_group_no = IntField(db_field='multiCardGroupNo', default=0)
    net_user = StringField(db_field='netUser', default="")
    remote_host_addr = StringField(db_field='remoteHostAddr', default="0.0.0.0")
    report_channel = IntField(db_field='reportChannel', default=0)
    serial_no = LongField(db_field='serialNo', unique=True)
    status_value = IntField(db_field='statusValue', default=1)
    swipe_card_type = IntField(db_field='swipeCardType', default=0)
    time = DateTimeField(db_field='time', default=datetime.datetime.now)
    record_type = IntField(db_field='type', default=0)
    verify_no = IntField(db_field='verifyNo', default=0)
    white_list_no = IntField(db_field='whiteListNo', default=0)
    name = StringField(db_field='name', default="Unregistered User")

    meta = {'collection': 'BioMetricActivity'}  # specify collection name

    @classmethod
    def with_employee_name(cls):
        records = list(cls.objects)
        employee_nos = {record.employee_no_string for record in records}
        users = BioMetricUserData.objects(employeeNo__in=employee_nos)
        user_map = {user.employeeNo: user.name for user in users}

        for record in records:
            record.name = user_map.get(record.employee_no_string, None)
        return records

    @property
    def employee_name(self):
        user = BioMetricUserData.objects(employeeNo=self.employee_no_string).first()
        return user.name if user else None