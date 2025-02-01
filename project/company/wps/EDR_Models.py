from datetime import datetime
from abc import ABC, abstractmethod, ABCMeta
import math
from mongoengine import (
    Document,
    StringField,
    DateField,
    IntField,
    LongField,
    ReferenceField,
    DateTimeField,
    FloatField,
    SequenceField
)
from mongoengine.base import TopLevelDocumentMetaclass


from .helper_functions import get_shortname, bank_dict

# Combine ABCMeta and TopLevelDocumentMetaclass
class CombinedMeta(ABCMeta, TopLevelDocumentMetaclass):
    pass

class EDR(ABC, Document, metaclass=CombinedMeta):
    employee = ReferenceField('EmployeeDetails', required=True)

    meta = {
        'allow_inheritance': True,
        'collection': 'edr',
    }

    @abstractmethod
    def create_edr(self):
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
    def calculate_leave_days(unpaid_leaves, half_days):
        return math.ceil(half_days / 2) + unpaid_leaves

    @staticmethod
    def validate_employee_details(employee_details, required_fields):
        for field in required_fields:
            try:
                field_value = employee_details
                for attr in field.split('.'):
                    field_value = getattr(field_value, attr, None)
                if not field_value:
                    print(f"{employee_details.first_name} doesn't have a valid value for '{field}'")
                    return [False, f"{employee_details.first_name} doesn't have a valid value for '{field}'"]
            except AttributeError:
                print(f"{employee_details.first_name} doesn't have the attribute '{field}'")
                return [False, "{employee_details.first_name} doesn't have the attribute '{field}'"]
        return True
    
    @staticmethod
    def check_and_delete(employee, start_date, end_date):
        existing_edr = EDR.objects(employee=employee, start_date=start_date, end_date=end_date).first()
        if existing_edr:
            existing_edr.delete()
            print(f"Existing EDR for employee {employee.id} with start_date {start_date} and end_date {end_date} has been deleted.")

    def get_fields_dict(self):
        fields_dict = {}
        for field_name, field_value in self._data.items():
            field_obj = self._fields.get(field_name)
            if field_obj:
                db_field = field_obj.db_field
                fields_dict[db_field] = field_value
        return fields_dict


class Mashreq_EDR(EDR):

    record_type = StringField(max_length=3, min_length=3, required=True, db_field='Record Type')
    unique_employee_id = StringField(min_length=14, max_length=35, required=True, db_field='Employee Unique ID')
    routing_code = StringField(max_length=9, required=True, db_field='Routing Code of AGENT')
    employee_account = StringField(max_length=23, required=True, db_field='Employee Account')
    start_date = DateField(required=True, db_field='Pay Start Date')
    end_date = DateField(required=True, db_field='Pay End Date')
    days = IntField(required=True, max_value=9999, db_field='Days in Period')
    fixed_component = LongField(required=True, max_value=999999999999999, db_field='Income Fixed Component')
    variable_component = LongField(required=True, max_value=999999999999999, db_field='Income Variable Component')
    leave_days = IntField(default=True, max_value=9999, db_field='Days on Leave for period')



    @classmethod
    def create_edr(cls, employee_details, employee_payroll_details):
        start_date, end_date = EDR.parse_dates(employee_payroll_details.start_date, employee_payroll_details.end_date)
        total_additions = float(getattr(employee_payroll_details, 'total_additions', 0.00))
        unpaid_leaves = getattr(employee_payroll_details, 'unpaid_leaves', 0)
        half_days = getattr(employee_payroll_details, 'half_days', 0)

        EDR.check_and_delete(employee_details, start_date, end_date)
        

        return cls(
            employee = employee_details,
            record_type ='EDR',
            unique_employee_id = employee_details.employee_sif_details.employee_mol_no,
            routing_code = employee_details.employee_bank_details.routing_code,
            employee_account = employee_details.employee_bank_details.account_no,
            start_date=start_date,
            end_date=end_date,
            days=(end_date - start_date).days,
            fixed_component=float(employee_details.employee_company_details.total_salary),
            variable_component=total_additions,
            leave_days=math.ceil(half_days / 2) + unpaid_leaves
        )

    def __str__(self):
        return f"Mashreq {self.record_type}-{self.unique_employee_id}-{self.routing_code}-{self.employee_account}-{self.start_date}-{self.end_date}-{self.days}-{self.fixed_component}-{self.variable_component}-{self.leave_days}"


class CBD_EDR(EDR):
    mol_id = StringField(max_length=35, required=True, db_field='MOLId ')
    salary = LongField(required=True, max_value=999999999999999, db_field='Salary')
    variable_pay = LongField(required=True, max_value=999999999999999, db_field='VarPay')
    from_date = DateField(required=True, db_field='Fromdate')
    to_date = DateField(required=True, db_field='Todate')
    account_no = StringField(required=True, max_length=50, db_field='Accountno')
    routing_code = StringField(required=True, max_length=15, db_field='RoutingCode')
    leave = IntField(required=True, max_value=9999, db_field='Leave')

    @classmethod
    def create_edr(cls, employee_details, employee_payroll_details):
        start_date, end_date = EDR.parse_dates(employee_payroll_details.start_date, employee_payroll_details.end_date)
        
        EDR.check_and_delete(employee_details, start_date, end_date)

        required_fields = [
            'employee_sif_details.employee_mol_no',
            'employee_bank_details.routing_code',
            'employee_company_details.total_salary'
        ]

        validation = EDR.validate_employee_details(employee_details, required_fields)
        if type(validation) is list:
            return validation

        return cls(
            employee=employee_details,
            mol_id=employee_details.employee_sif_details.employee_mol_no,
            salary=employee_payroll_details.salary_to_be_paid,
            variable_pay=employee_payroll_details.total_additions,
            from_date=start_date,
            to_date=end_date,
            account_no=employee_details.employee_bank_details.iban_no,
            routing_code=employee_details.employee_bank_details.routing_code,
            leave=EDR.calculate_leave_days(employee_payroll_details.unpaid_leaves, employee_payroll_details.half_days)
        )
    
    def __str__(self):
        return f"CBD {self.employee.first_name}-{self.salary}-{self.variable_pay}-{self.from_date}-{self.to_date}-{self.leave}"


class Joyalukkas_EDR(EDR):
    comp_mol_code = StringField(max_length=35, db_field='COMPMOLCODE')
    emp_mol_id = StringField(max_length=35, db_field='EMPMOLID')
    emp_name = StringField(max_length=50, db_field='EMPNAME')
    fixed_component = LongField(max_value=999999999999999, db_field='INCOMEFIX')
    variable_component = LongField(max_value=999999999999999, db_field='INCOMEVAR')
    leave = IntField(max_value=9999, db_field='LEAVEDAYS')
    month = IntField(max_value=12, db_field='SALMNTH')
    year = IntField(max_value=9999, db_field='SALYR')
    bank_acc_no = StringField(max_length=30, db_field='BANKACCNO')
    bank_name = StringField(max_length=30, db_field='BANKNAME')

    @classmethod
    def create_edr(cls, employee_details, employee_payroll_details):
        start_date, end_date = EDR.parse_dates(employee_payroll_details.start_date, employee_payroll_details.end_date)

        EDR.check_and_delete(employee_details, start_date, end_date)

        total_additions = float(getattr(employee_payroll_details, 'total_additions', 0.00))
        unpaid_leaves = getattr(employee_payroll_details, 'unpaid_leaves', 0)
        half_days = getattr(employee_payroll_details, 'half_days', 0)

        required_fields = [
            'employee_sif_details.company_mol_no',
            'employee_sif_details.employee_mol_no',
            # 'first_name',
            # 'last_name',
            # 'employee_company_details.total_salary',
            # 'employee_bank_details.account_no',  #Added By Ashiq  date: 11/09/2024  issues: wps 
            # 'employee_bank_details.bank_name'
        ]

        validation = EDR.validate_employee_details(employee_details, required_fields)
        if type(validation) is list:
            return validation

        return cls(
            employee=employee_details,
            comp_mol_code=employee_details.employee_sif_details.company_mol_no,
            emp_mol_id=employee_details.employee_sif_details.employee_mol_no,
            emp_name=f"{employee_details.first_name} {employee_details.last_name}",
            fixed_component=float(employee_details.employee_company_details.total_salary),
            variable_component=total_additions,
            leave=EDR.calculate_leave_days(unpaid_leaves, half_days),
            month=int(start_date.strftime('%m')),
            year=int(start_date.strftime('%Y')),
            # bank_acc_no=employee_details.employee_bank_details.account_no,
            # bank_name=employee_details.employee_bank_details.bank_name

               
            # Handle null for bank account number  #Added By Ashiq  date: 11/09/2024  issues: wps 
            bank_acc_no=employee_details.employee_bank_details.iban_no if employee_details.employee_bank_details.iban_no else 'Unknown iban_no',
            
            # Handle null for bank name   #Added By Ashiq  date: 11/09/2024  issues: wps 
            bank_name=employee_details.employee_bank_details.bank_name if employee_details.employee_bank_details.bank_name else 'Unknown Bank Name'
        )

    def __str__(self):
        return f"JOYALUKKAS {self.emp_name}-{self.fixed_component}-{self.variable_component}-{self.leave}-{self.month}-{self.year}-{self.bank_acc_no}-{self.bank_name}"
    
class RAK_EDR(EDR):
    record_type = StringField(max_length=3, min_length=3, required=True, db_field='Record Type')
    unique_employee_id = StringField(min_length=14, max_length=35, required=True, db_field='Employee Unique ID')
    routing_code = StringField(max_length=9, required=True, db_field='Routing Agent Code')
    employee_account = StringField(max_length=23, required=True, db_field='IBAN/Account No')
    start_date = DateField(required=True, db_field='Pay Start Date')
    end_date = DateField(required=True, db_field='Pay End Date')
    days = IntField(required=True, max_value=9999, db_field='Days in Period')
    fixed_component = LongField(required=True, max_value=999999999999999, db_field='Income Fixed Component')
    variable_component = LongField(required=True, max_value=999999999999999, db_field='Income Variable Component')
    leave_days = IntField(default=True, max_value=9999, db_field='Days On Leave For Period')
        
    @classmethod
    def create_edr(cls, employee_details, employee_payroll_details):
        start_date, end_date = EDR.parse_dates(employee_payroll_details.start_date, employee_payroll_details.end_date)
        
        EDR.check_and_delete(employee_details, start_date, end_date)
        
        total_additions = float(getattr(employee_payroll_details, 'total_additions', 0.00))
        unpaid_leaves = getattr(employee_payroll_details, 'unpaid_leaves', 0)
        half_days = getattr(employee_payroll_details, 'half_days', 0)

        required_fields = [
            'employee_sif_details.employee_mol_no',
            'employee_bank_details.routing_code',
            'employee_bank_details.account_no',
            'employee_company_details.total_salary'
        ]

        validation = EDR.validate_employee_details(employee_details, required_fields)
        if type(validation) is list:
            return validation
            
        return cls(
            employee = employee_details,
            record_type = 'EDR',
            unique_employee_id = employee_details.employee_sif_details.employee_mol_no,
            routing_code = employee_details.employee_bank_details.routing_code,
            employee_account = employee_details.employee_bank_details.account_no,
            start_date = start_date,
            end_date = end_date,
            days = (end_date - start_date).days,
            fixed_component = float(employee_details.employee_company_details.total_salary),
            variable_component = total_additions,
            leave_days = EDR.calculate_leave_days(unpaid_leaves, half_days)
        )
    
    def __str__(self):
        return f"RAK-{self.employee}-{self.fixed_component}-{self.variable_component}"

class DIB_EDR(EDR):
    record_type = StringField(max_length=3, min_length=3, required=True, db_field='Record Type')
    unique_employee_id = StringField(min_length=14, max_length=35, required=True, db_field='Employee Unique ID')
    routing_code = StringField(max_length=9, required=True, db_field='Routing Code of the AGENT')
    employee_account = StringField(max_length=23, required=True, db_field='Employee Account With Agent Section')
    start_date = DateField(required=True, db_field='Pay Start Date')
    end_date = DateField(required=True, db_field='Pay End Date')
    days = IntField(required=True, max_value=9999, db_field='Days in Period')
    fixed_component = LongField(required=True, max_value=999999999999999, db_field='Income Fixed Component')
    variable_component = LongField(required=True, max_value=999999999999999, db_field='Income Variable Component')
    leave_days = IntField(default=True, max_value=9999, db_field='Days on Leave for period')

    @classmethod
    def create_edr(cls, employee_details, employee_payroll_details):
        start_date, end_date = EDR.parse_dates(employee_payroll_details.start_date, employee_payroll_details.end_date)
        
        EDR.check_and_delete(employee_details, start_date, end_date)
        
        total_additions = float(getattr(employee_payroll_details, 'total_additions', 0.00))
        unpaid_leaves = getattr(employee_payroll_details, 'unpaid_leaves', 0)
        half_days = getattr(employee_payroll_details, 'half_days', 0)

        required_fields = [
            'employee_sif_details.employee_mol_no',
            'employee_bank_details.routing_code',
            'employee_bank_details.account_no',
            'employee_company_details.total_salary'
        ]


        validation = EDR.validate_employee_details(employee_details, required_fields)
        if type(validation) is list:
            return validation
        
        return cls(
            employee = employee_details,
            record_type = 'EDR',
            unique_employee_id = employee_details.employee_sif_details.employee_mol_no,
            routing_code = employee_details.employee_bank_details.routing_code,
            employee_account = employee_details.employee_bank_details.account_no,
            start_date = start_date,
            end_date = end_date,
            days = (end_date - start_date).days,
            fixed_component = float(employee_details.employee_company_details.total_salary),
            variable_component = total_additions,
            leave_days = EDR.calculate_leave_days(unpaid_leaves, half_days)
        )
    
    def __str__(self):
        return f"DIB {self.employee.first_name}-{self.start_date}-{self.end_date}"

class Emirates_Islamic_SCR(Document):
    record_type = StringField(max_length=3, min_length=3, required=True, db_field='Record Type')
    unique_employee_id = StringField(min_length=14, max_length=35, required=True, db_field='Employee Unique ID')
    emp_bank_code = StringField(max_length=9, required=True, db_field='Bank Code of the Employer')
    created_date = DateField(default=datetime.today(), db_field='File Creation Date')
    created_time = DateTimeField(default=datetime.now().strftime("%H:%M"), db_field='File Creation Time')
    month = DateField(required=True, db_field='Month')
    pass

class Emirates_Islamic_EDR(EDR):
    record_type = StringField(max_length=3, min_length=3, required=True, db_field='Record Type')
    unique_employee_id = StringField(min_length=14, max_length=35, required=True, db_field='Employee Unique ID')
    routing_code = StringField(max_length=9, required=True, db_field='Agent ID')
    employee_account = StringField(max_length=23, required=True, db_field='Employee Account with Agent')
    start_date = DateField(required=True, db_field='Pay Start Date')
    end_date = DateField(required=True, db_field='Pay End Date')
    days = IntField(required=True, max_value=9999, db_field='Days in Period')
    fixed_component = LongField(required=True, max_value=999999999999999, db_field='Income Fixed Component')
    variable_component = LongField(required=True, max_value=999999999999999, db_field='Income Variable Component')
    leave_days = IntField(default=True, max_value=9999, db_field='Days on Leave for period')

    @classmethod
    def create_edr(cls, employee_details, employee_payroll_details):
        start_date, end_date = EDR.parse_dates(employee_payroll_details.start_date, employee_payroll_details.end_date)
        
        EDR.check_and_delete(employee_details, start_date, end_date)

        total_additions = float(getattr(employee_payroll_details, 'total_additions', 0.00))
        unpaid_leaves = getattr(employee_payroll_details, 'unpaid_leaves', 0)
        half_days = getattr(employee_payroll_details, 'half_days', 0)

        required_fields = [
            'employee_sif_details.employee_mol_no',
            'employee_bank_details.routing_code',
            'employee_bank_details.account_no',
            'employee_company_details.total_salary'
        ]


        validation = EDR.validate_employee_details(employee_details, required_fields)
        if type(validation) is list:
            return validation

        return cls(
            employee = employee_details,
            record_type = 'EDR',
            unique_employee_id = employee_details.employee_sif_details.employee_mol_no,
            routing_code = employee_details.employee_bank_details.routing_code,
            employee_account = employee_details.employee_bank_details.account_no,
            start_date = start_date,
            end_date = end_date,
            days = (end_date - start_date).days,
            fixed_component = float(employee_details.employee_company_details.total_salary),
            variable_component = total_additions,
            leave_days = EDR.calculate_leave_days(unpaid_leaves, half_days)
        )
    
    def __str__(self):
        return f"Emirates_Islamic {self.employee.first_name}--{self.start_date}-{self.end_date}-"


class Al_Ansari_EDR(EDR):
    record_type = StringField(max_length=3, min_length=3, required=True, db_field='Record Type')
    #unique_employee_id = StringField(min_length=1, max_length=35, required=True, db_field='Employee Unique ID')
    unique_employee_id = StringField(max_length=35, required=True, db_field='Employee Unique ID') #change  min length 14 to 1 chabged by ashiq  date :11/09/2024 issues : wps
    emp_name = StringField(max_length=50, required=True, db_field='Employee Name')
    agent_id = StringField(max_length=35, required=True, db_field='Agent ID')
    account_no = StringField(max_length=23, required=True, db_field='IBAN/Account No')
    start_date = DateField(required=True, db_field='Pay Start Date')
    end_date = DateField(required=True, db_field='Pay End Date')
    total_days = IntField(required=True, max_value=9999, db_field='Days in Period')
    fixed_component = LongField(required=True, max_value=999999999999999, db_field='Income Fixed Component')
    variable_component = LongField(required=True, max_value=999999999999999, db_field='Income Variable Component')
    leave = IntField(required=True, max_value=9999, db_field='Days On Leave For Period')

    @classmethod
    def create_edr(cls, employee_details, employee_payroll_details):
        start_date, end_date = EDR.parse_dates(employee_payroll_details.start_date, employee_payroll_details.end_date)
        
        EDR.check_and_delete(employee_details, start_date, end_date)

        total_additions = float(getattr(employee_payroll_details, 'total_additions', 0.00))
        unpaid_leaves = getattr(employee_payroll_details, 'unpaid_leaves', 0)
        half_days = getattr(employee_payroll_details, 'half_days', 0)

        required_fields = [
            #'employee_sif_details.employee_mol_no', #Added By Ashiq  date: 11/09/2024  issues: wps 
            #'employee_bank_details.routing_code',  #Added By Ashiq  date: 11/09/2024  issues: wps 
            #'employee_bank_details.account_no',  #Added By Ashiq  date: 11/09/2024  issues: wps 
            'employee_company_details.total_salary'
        ]


        validation = EDR.validate_employee_details(employee_details, required_fields)
        if type(validation) is list:
            return validation

        return cls(
            employee = employee_details,
            record_type = 'EDR',
            unique_employee_id = employee_details.employee_sif_details.employee_mol_no,
            emp_name = f"{employee_details.first_name} {employee_details.last_name}",
            # agent_id = employee_details.employee_bank_details.routing_code,
            # account_no = employee_details.employee_bank_details.account_no,
            # Handle null for routing code and account number  #Added By Ashiq  date: 11/09/2024  issues: wps 

            agent_id = employee_details.employee_bank_details.routing_code if employee_details.employee_bank_details.routing_code else 'Unknown Routing Code',
            account_no = employee_details.employee_bank_details.iban_no if employee_details.employee_bank_details.iban_no else 'Unknown iban_no',
            
            start_date = start_date,
            end_date = end_date,
            total_days = (end_date - start_date).days,
            fixed_component = float(employee_details.employee_company_details.total_salary),
            variable_component = total_additions,
            leave = EDR.calculate_leave_days(unpaid_leaves, half_days)
        )
    
    def __str__(self):
        return f"Al_Ansari {self.emp_name}-{self.fixed_component}-{self.start_date}-{self.end_date}-{self.leave}"

class Generic_EDR(EDR):
    from_date = DateField(required=True)
    to_date = DateField(required=True)
    record_type = StringField(required=False, db_field='Record Type')
    unique_employee_id = StringField(required=False, db_field='Employee Unique ID')
    routing_code = StringField(required=False, db_field='Routing Code of AGENT')
    employee_account = StringField(required=False, db_field='Employee Account')
    start_date = DateField(required=False, db_field='Pay Start Date')
    end_date = DateField(required=False, db_field='Pay End Date')
    days = IntField(required=False, db_field='Days in Period')
    fixed_component = LongField(required=False, db_field='Income Fixed Component')
    variable_component = LongField(required=False, db_field='Income Variable Component')
    leave_days = IntField(required=False, db_field='Days on Leave for period')
    employee = ReferenceField('EmployeeDetails', required=False)

    @classmethod
    def create_edr(cls, employee_details=None, employee_payroll_details=None):
        # Helper function to safely get attributes with default
        def safe_getattr(obj, attr, default=None):
            return getattr(obj, attr, default) if obj else default

        # Convert date strings to datetime objects if provided
        start_date = safe_getattr(employee_payroll_details, 'start_date', None)
        end_date = safe_getattr(employee_payroll_details, 'end_date', None)

        EDR.check_and_delete(employee_details, start_date, end_date)

        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            except (ValueError, TypeError):
                start_date = None

        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except (ValueError, TypeError):
                end_date = None

        # Calculate days in period if dates are provided
        days_in_period = (end_date - start_date).days if start_date and end_date else None

        # Ensure default values for attributes
        total_additions = safe_getattr(employee_payroll_details, 'total_additions', 0.00)
        unpaid_leaves = safe_getattr(employee_payroll_details, 'unpaid_leaves', 0)
        half_days = safe_getattr(employee_payroll_details, 'half_days', 0)
        leave_days = math.ceil(half_days / 2) + unpaid_leaves

        return cls(
            record_type='EDR',  # Default record type
            unique_employee_id=safe_getattr(employee_details.employee_sif_details, 'employee_mol_no', ''),
            # routing_code=safe_getattr(employee_details.employee_bank_details, 'routing_code', ''),
            # employee_account=safe_getattr(employee_details.employee_bank_details, 'account_no', ''),

            # Handle null values for routing code and account number  #Added By Ashiq  date: 11/09/2024  issues: wps 
            routing_code=safe_getattr(employee_details.employee_bank_details, 'routing_code', None),
            employee_account=safe_getattr(employee_details.employee_bank_details, 'account_no', None),
            
            from_date=start_date,
            to_date=end_date,
            start_date=start_date,
            end_date=end_date,
            days=days_in_period,
            fixed_component=float(safe_getattr(employee_details.employee_company_details, 'total_salary', 0.0)),
            variable_component=total_additions,
            leave_days=leave_days,
            employee=employee_details
        )

    def __str__(self):
        return f"""Generic EDR: {self.record_type} - {self.unique_employee_id} - {self.routing_code}
          - {self.employee_account} - {self.start_date} - {self.end_date} - {self.days} - 
          {self.fixed_component} - {self.variable_component} - {self.leave_days}"""
    

class CBT_FZE_EDR(EDR):
    no = IntField(required=True, db_field='No')
    name = StringField(required=False, db_field='Name')
    bank_short_name = StringField(required=True, db_field='Bank Short Name')
    iban_no = StringField(required=True, db_field='IBAN No')
    amount = FloatField(required=True, db_field='Amount')
    bank_full_name = StringField(required=True, db_field='Bank Full Name')
    swift_code = StringField(required=True, db_field='Swift Code')

    @classmethod
    def create_edr(cls, employee_details=None, employee_payroll_details=None):
        total_additions = float(getattr(employee_payroll_details, 'total_additions', 0.00))

        required_fields = [
            'employee_company_details.total_salary',
            'employee_bank_details.bank_name',
            'employee_bank_details.swift_code'
        ]
        
        validation = EDR.validate_employee_details(employee_details, required_fields)
        if type(validation) is list:
            return validation
        
        short_name = get_shortname(employee_details.employee_bank_details.bank_name)
        inverted_bank_dict = {v: k for k, v in bank_dict.items()}

        return cls(
            employee=employee_details,
            name=f"{employee_details.first_name} {employee_details.last_name}",
            bank_short_name=short_name,
            iban_no=employee_details.employee_bank_details.iban_no,
            amount=float(employee_details.employee_company_details.total_salary) + total_additions,
            bank_full_name=inverted_bank_dict[short_name],
            swift_code=employee_details.employee_bank_details.swift_code
        )
    
    def __str__(self):
        return f"""Generic EDR: {self.name} - {self.bank_short_name} - {self.iban_no}
         - {self.amount}"""

class NBK_EDR(EDR):
    no = IntField(required=True, db_field='Payment Serial Number')
    name = StringField(required=False, db_field='Name')
    unique_employee_id = StringField(min_length=1, max_length=35, required=True, db_field='Beneficiary Civil Id')
    iban_no = StringField(required=True, db_field='Account # for NBK A/C & IBAN for other Bank')
    bank_short_name = StringField(required=True, db_field='Bank Short Name')
    bank_full_name = StringField(required=True, db_field='Bank Full Name')
    currency = StringField(required=True, db_field='Currency', default='KWD')
    amount = FloatField(required=True, db_field='Amount')

    _counter = 1  # Class-level counter for `no`

    @classmethod
    def create_edr(cls, employee_details=None, employee_payroll_details=None):
        total_additions = getattr(employee_payroll_details, 'total_additions', 0.00)
        if isinstance(total_additions, dict):
            raise ValueError("total_additions cannot be a dictionary.")
        total_additions = float(total_additions)

        required_fields = [
            'employee_company_details.total_salary',
            'employee_bank_details.bank_name',
        ]

        validation = EDR.validate_employee_details(employee_details, required_fields)
        if isinstance(validation, list):
            return validation

        short_name = get_shortname(employee_details.employee_bank_details.bank_name)
        inverted_bank_dict = {v: k for k, v in bank_dict.items()}

        # Determine IBAN or Account Number
        bank_details = getattr(employee_details, 'employee_bank_details', {})
        if isinstance(bank_details, dict):
            iban_or_account = bank_details.get('account_no') if short_name == "NBK" else bank_details.get('iban_no')
        else:
            iban_or_account = bank_details.account_no if short_name == "NBK" else bank_details.iban_no

        bank_full_name = inverted_bank_dict.get(short_name, "Unknown Bank Name")

        edr_instance = cls(
            no=cls._counter,
            unique_employee_id=employee_details.employee_sif_details.employee_mol_no,
            employee=employee_details,
            name=employee_details.employee_bank_details.account_holder,
            bank_short_name=short_name,
            iban_no=iban_or_account,
            amount=float(employee_details.employee_company_details.total_salary) + total_additions,
            bank_full_name=bank_full_name,
            currency='KWD',
        )

        cls._counter += 1  # Increment the counter

        return edr_instance

    def __str__(self):
        return f"""Generic EDR: {self.name} - {self.bank_short_name} - {self.iban_no} - {self.amount} {self.currency}"""
