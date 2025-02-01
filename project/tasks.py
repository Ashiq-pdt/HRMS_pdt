import logging
from celery import shared_task
from datetime import datetime, timedelta
from project.models import CompanyDetails
import sys
import os

# Add the parent directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import celery

from  project.company.model import EmployeeLeavePolicies, EmployeeLeaveAdjustment
# from project.company.routes import monthly_accrual_leaves1

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# @shared_task
# def run_monthly_accrual_leaves():
#     current_date = datetime.now()
#     return monthly_accrual_leaves1(current_date)

@shared_task
def run_monthly_accrual_leaves():

    current_date = datetime.now() # Monthly Ending Date

    company_details = CompanyDetails.objects().all()

    for company_detail in company_details:
        leave_adjustments = []
        active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
        one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']
        if one_time_leave_policies:
            for employee in active_employees:
                if employee.employee_company_details.date_of_joining:
                    try:
                        date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
                        # Further processing for valid dates
                        date_of_joining=datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
                        days_worked = (current_date - date_of_joining).days
                        if days_worked < 365:
                            # print("Less Than 1 Year of Joining");
                            for leave_policy in one_time_leave_policies:
                                new_leave_balance = 0 
                                before_adjustment = 0
                                prorated_accruals = 0
                                employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
                                # Check if the current month is the joining month of the employee
                                # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
                                # no of days worked = current_date - joining_date
                                # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
                                                        # OR
                                # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
                                # Check if the current month is the joining month
                                if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
                                    # if days_worked < 365:  # Assuming probation period is less than a year
                                    prorated_accruals = (days_worked / 30) * 2 
                                    # else:
                                    #     prorated_accruals = (days_worked / 30) * 2.5
                                if employee_leave_policy:
                                        print(employee_leave_policy) 
                                        before_adjustment = employee_leave_policy.balance
                                        new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days))
                                else:
                                        #create New with the new amount    
                                        new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.probabtion_allowance_days)
                                        employee_leave_policy = EmployeeLeavePolicies()
                                        employee_leave_policy.company_id = company_detail.user_id
                                        employee_leave_policy.employee_details_id = employee._id
                                        employee_leave_policy.leave_policy_id = leave_policy._id
                                        employee_leave_policy.balance = new_leave_balance
                                        employee_leave_policy.save()
                                        employee.update(push__employee_leave_policies=employee_leave_policy._id)
                                        
                                if  new_leave_balance > 0:     
                                        previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
                                        adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month  
                                        # adjustment_comment = 'Monthly Accrual Adjustment for Month ' + datetime.now().strftime("%B %Y")
                                        new_data = EmployeeLeaveAdjustment(
                                                    company_id = company_detail.user_id,
                                                    employee_details_id =  employee._id,
                                                    employee_leave_pol_id = employee_leave_policy._id, 
                                                    adjustment_type = 'increment',
                                                    adjustment_days = str(new_leave_balance),
                                                    adjustment_comment = adjustment_comment,
                                                    before_adjustment=  str(employee_leave_policy.balance),
                                                    after_adjustment = str(new_leave_balance)
                                                )
                                        status = new_data.save()
                                        company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
                        else:
                            # print("More Than 1 year of joining");
                            for leave_policy in one_time_leave_policies:
                                new_leave_balance = 0 
                                before_adjustment = 0
                                prorated_accruals = 0
                                employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy,employee_details_id=employee._id).first()
                                # Check if the current month is the joining month of the employee
                                # if true then calculate the amount they will recieve the accurals based on the joining date calculate based on the below formula
                                # no of days worked = current_date - joining_date
                                # prorated_accurals = no of days worked / 24 (this if employees who are on probabtion and less than a year of joining i.e they will get only 24 working days annual leave)
                                                        # OR
                                # prorated_accurals = no of days worked / 30 (this if employees who are more than a year of joining i.e they will get only 30 working days annual leave)
                                # Check if the current month is the joining month
                                if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
                                        prorated_accruals = (days_worked / 30) * 2.5 
                                if employee_leave_policy:
                                        before_adjustment = employee_leave_policy.balance
                                        new_leave_balance = employee_leave_policy.balance + (prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days))
                                else:
                                        #create New with the new amount     
                                        new_leave_balance = prorated_accruals if prorated_accruals > 0 else float(leave_policy.non_probabtion_allowance_days)
                                        employee_leave_policy = EmployeeLeavePolicies()
                                        employee_leave_policy.company_id = company_detail.user_id
                                        employee_leave_policy.employee_details_id = employee._id
                                        employee_leave_policy.leave_policy_id = leave_policy._id
                                        employee_leave_policy.balance = new_leave_balance
                                        employee_leave_policy.save()
                                        employee.update(push__employee_leave_policies=employee_leave_policy._id)
                                if  new_leave_balance > 0:       
                                    previous_month = (datetime.now() - timedelta(days=30)).strftime("%B %Y")
                                    adjustment_comment = "Monthly Accrual Adjustment for Month " + previous_month
                                    print(adjustment_comment)
                                    new_data = EmployeeLeaveAdjustment(
                                                company_id = company_detail.user_id,
                                                employee_details_id =  employee._id,
                                                employee_leave_pol_id = employee_leave_policy._id, 
                                                adjustment_type = 'increment',
                                                adjustment_days = str(new_leave_balance),
                                                adjustment_comment = adjustment_comment,
                                                before_adjustment=  str(employee_leave_policy.balance),
                                                after_adjustment = str(new_leave_balance)
                                            )
                                    status = new_data.save()
                                    company_details = employee_leave_policy.update(push__employee_leave_adjustments=new_data._id,balance=new_leave_balance)  
                    except ValueError:
                        # Handling for invalid date format
                        continue
    return True
  

# def monthly_accrual_leaves(current_date):
#     # The current_date is passed directly to this function
#     company_details = CompanyDetails.objects().all()

#     for company_detail in company_details:
#         active_employees = [employee for employee in company_detail.employees if employee.employee_company_details.status]
#         one_time_leave_policies = [leave_policy for leave_policy in company_detail.leave_policies if leave_policy.allowance_type == 'onetime']

#         for employee in active_employees:
#             if employee.employee_company_details.date_of_joining:
#                 try:
#                     date_of_joining = datetime.strptime(employee.employee_company_details.date_of_joining, '%d/%m/%Y')
#                     days_worked = (current_date - date_of_joining).days
                    
#                     # Initialize leave adjustments here
#                     leave_adjustments = []

#                     if days_worked < 365:
#                         accruals_per_month = 2
#                         fallback_days = float(leave_policy.probabtion_allowance_days)
#                     else:
#                         accruals_per_month = 2.5
#                         fallback_days = float(leave_policy.non_probabtion_allowance_days)

#                     # Iterate over leave policies once
#                     for leave_policy in one_time_leave_policies:
#                         new_leave_balance = 0
#                         prorated_accruals = 0
#                         employee_leave_policy = EmployeeLeavePolicies.objects(leave_policy_id=leave_policy._id, employee_details_id=employee._id).first()

#                         # Check if the current month is the joining month
#                         if current_date.year == date_of_joining.year and current_date.month == date_of_joining.month:
#                             prorated_accruals = (days_worked / 30) * accruals_per_month

#                         # If leave policy exists, handle existing balances
#                         if employee_leave_policy:
#                             # Get the last leave adjustment for this employee policy
#                             last_adjustment = EmployeeLeaveAdjustment.objects(employee_leave_pol_id=employee_leave_policy._id).order_by('-created_at').first()
                            
#                             # Check if the last adjustment was done today
#                             if last_adjustment and last_adjustment.created_at.strftime("%d %B %Y") == current_date.strftime("%d %B %Y"):
#                                 continue  # Skip if adjustment was already made today
                            
#                             new_leave_balance = employee_leave_policy.balance + max(prorated_accruals, fallback_days)
#                         else:
#                             new_leave_balance = max(prorated_accruals, fallback_days)
#                             employee_leave_policy = EmployeeLeavePolicies(
#                                 company_id=company_detail.user_id,
#                                 employee_details_id=employee._id,
#                                 leave_policy_id=leave_policy._id,
#                                 balance=new_leave_balance
#                             )
#                             employee_leave_policy.save()
#                             employee.update(push__employee_leave_policies=employee_leave_policy._id)

#                         if new_leave_balance > 0:
#                             previous_month = (current_date - timedelta(days=30)).strftime("%B %Y")
#                             adjustment_comment = f"Monthly Accrual Adjustment for Month {previous_month}"

#                             new_data = EmployeeLeaveAdjustment(
#                                 company_id=company_detail.user_id,
#                                 employee_details_id=employee._id,
#                                 employee_leave_pol_id=employee_leave_policy._id,
#                                 adjustment_type='increment',
#                                 adjustment_days=str(new_leave_balance),
#                                 adjustment_comment=adjustment_comment,
#                                 before_adjustment=str(employee_leave_policy.balance),
#                                 after_adjustment=str(new_leave_balance),
#                                 created_at=current_date.strftime("%d %B %Y %H:%M:%S")
#                             )
#                             new_data.save()
#                             employee_leave_policy.update(push__employee_leave_adjustments=new_data._id, balance=new_leave_balance)

#                 except ValueError:
#                     logging.error(f"ValueError for employee {employee._id}: {employee.employee_company_details.date_of_joining}")
#                     continue

#     # Format the current date and time to be displayed in the response
#     processed_datetime = current_date.strftime("%d %B %Y %H:%M:%S")
#     return f"Accrual Leaves Processed Successfully on {processed_datetime}"
