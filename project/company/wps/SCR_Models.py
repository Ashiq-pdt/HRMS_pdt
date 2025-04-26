from datetime import datetime
from abc import ABC, abstractmethod, ABCMeta
from mongoengine import (
    Document,
    StringField,
    DateField,
    IntField,
    FloatField,
    BooleanField,
    ReferenceField,
)
from mongoengine.base import TopLevelDocumentMetaclass

class CombinedMeta(ABCMeta, TopLevelDocumentMetaclass):
    pass

class SCR(ABC, Document, metaclass=CombinedMeta):
    employer = ReferenceField('EmployeeDetails', required=True)
    start_date = DateField(required=True)
    end_date = DateField(required=True)
    show_field_names = BooleanField(default=False)
    meta = {
        'allow_inheritance': True,
        'collection': 'scr',
    }

    @abstractmethod
    def create_scr(self):
        pass

    @abstractmethod
    def update_scr(self):
        pass

    @staticmethod
    def parse_dates(start_date_str, end_date_str=None):
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            return start_date, end_date
        except (ValueError, TypeError):
            raise ValueError("Invalid date format for start_date or end_date")

    @staticmethod
    def validate_employee_details(employee_details, required_fields):
        for field in required_fields:
            try:
                field_value = employee_details
                for attr in field.split('.'):
                    field_value = getattr(field_value, attr, None)
                if not field_value:
                    print(f"{employee_details.first_name} doesn't have a valid value for '{field}'")
                    return False
            except AttributeError:
                print(f"{employee_details.first_name} doesn't have the attribute '{field}'")
                return False
        return True

    def set_common_fields(self, company_details, payroll_details):
        start_date, end_date = self.parse_dates(payroll_details.start_date, payroll_details.end_date)
        self.employer = company_details.id
        self.start_date = start_date
        self.end_date = end_date

class Mashreq_SCR(SCR):
    record_type = StringField(required=True, max_length=3, db_field='Record Type')
    employer_unique_id = StringField(required=True, min_length=13, max_length=35, db_field='Employer Unique ID')
    routing_code = StringField(required=True, max_length=9, db_field='Routing Code of the Employers Bank')
    file_creation_date = DateField(required=True, db_field='File Creation Date')
    file_creation_time = StringField(required=True, max_length=4, db_field='File Creation Time')
    salary_month = StringField(required=True, max_length=7, db_field='Salary Month')
    edr_count = IntField(required=True, db_field='EDR Count')
    total_salary = FloatField(required=True, db_field='Total Salary')
    payment_currency = StringField(required=True, max_length=3, default="AED", db_field='Payment Currency')
    employer_reference = StringField(max_length=35, db_field='Employer Reference')

    @classmethod
    def create_scr(cls,  company_details, payroll_details, currency='AED', employer_reference='None'):
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H%M')

        scr = cls(
            record_type='SCR',
            employer_unique_id= company_details.company_unique_id,
            routing_code= company_details.company_routing_code,
            file_creation_date=current_date,
            file_creation_time=current_time,
            salary_month=datetime.now().strftime('%m-%Y'),
            payment_currency=currency,
            employer_reference=payroll_details.reference,
            edr_count=0,
            total_salary=0.0
        )
        scr.set_common_fields(company_details, payroll_details)
        return scr

    def update_scr(self, edr_records):
        if edr_records:
            current_salary = edr_records.fixed_component + edr_records.variable_component
            self.edr_count += 1
            self.total_salary += current_salary

class Joyalukkas_SCR(SCR):
    total_salary = FloatField(required=True, db_field='Total Salary')

    @classmethod
    def create_scr(cls, company_details, payroll_details):
        scr = cls(total_salary=0.0)
        scr.set_common_fields(company_details, payroll_details)
        return scr

    def update_scr(self, edr_records):
        current_salary = edr_records.fixed_component + edr_records.variable_component
        self.total_salary += current_salary

class CBD_SCR(SCR):
    company_name = StringField(required=True, db_field='Company Name')
    est_id = StringField(required=True, db_field='EST ID')

    @classmethod
    def create_scr(cls, company_details, payroll_details):
        scr = cls(
            company_name = company_details.company_name,
            est_id = company_details.company_unique_id

        )
        scr.set_common_fields(company_details, payroll_details)
        return scr

    def update_scr(self, edr_records):
        pass
