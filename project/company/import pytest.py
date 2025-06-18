import pytest
from datetime import datetime, timedelta
from bson import ObjectId
from unittest.mock import patch, Mock
import pandas as pd
from io import BytesIO
from ..models import CompanyDetails, EmployeeDetails, EmployeeAttendance, User
from . import routes

# project/company/test_routes.py



@pytest.fixture
def mock_current_user():
    """Create a mock current user"""
    return Mock(id=ObjectId(), type='company')

@pytest.fixture
def mock_company_details():
    """Create mock company details with test employees"""
    return Mock(
        user_id=ObjectId(),
        employees=[
            {'user_id': {'active': True}},
            {'user_id': {'active': True}}
        ],
        clock_in_options=[]
    )

@pytest.fixture
def mock_employee_attendance():
    """Create mock employee attendance records"""
    return Mock(
        attendance_date=datetime.now(),
        total_hrs_worked='0 days, 08:00:00',
        break_history=[],
        employee_details_id=Mock(
            first_name='Test',
            last_name='User'
        )
    )

@pytest.fixture
def app_context(app):
    """Create application context"""
    with app.app_context():
        yield

def test_attendance_report_download_individual_employee(app_context, mock_current_user, mock_company_details, mock_employee_attendance):
    """Test downloading individual employee attendance report"""
    
    with patch('flask_login.current_user', mock_current_user), \
         patch('project.company.routes.CompanyDetails.objects') as mock_company_query, \
         patch('project.company.routes.EmployeeAttendance.objects') as mock_attendance_query, \
         patch('project.company.routes.request') as mock_request:

        # Setup mocks
        mock_company_query.return_value.first.return_value = mock_company_details
        mock_attendance_query.return_value = [mock_employee_attendance]
        
        # Mock POST request data
        mock_request.method = 'POST'
        mock_request.form = {
            'daterange': '01/01/2023 - 31/01/2023',
            'employee_id': str(ObjectId())
        }

        # Call the function
        response = routes.attendance_report_download()

        # Verify response
        assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'Attendance_Report' in response.headers['Content-Disposition']

def test_attendance_report_download_company_wide(app_context, mock_current_user, mock_company_details, mock_employee_attendance):
    """Test downloading company-wide attendance report"""
    
    with patch('flask_login.current_user', mock_current_user), \
         patch('project.company.routes.CompanyDetails.objects') as mock_company_query, \
         patch('project.company.routes.EmployeeAttendance.objects') as mock_attendance_query, \
         patch('project.company.routes.request') as mock_request:

        # Setup mocks
        mock_company_query.return_value.first.return_value = mock_company_details
        mock_attendance_query.return_value = [mock_employee_attendance]
        
        # Mock POST request without employee_id
        mock_request.method = 'POST'
        mock_request.form = {
            'daterange': '01/01/2023 - 31/01/2023'
        }

        # Call the function
        response = routes.attendance_report_download()

        # Verify response
        assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'Company_Attendance_Report' in response.headers['Content-Disposition']

def test_attendance_report_download_default(app_context, mock_current_user, mock_company_details, mock_employee_attendance):
    """Test downloading default (today's) attendance report"""
    
    with patch('flask_login.current_user', mock_current_user), \
         patch('project.company.routes.CompanyDetails.objects') as mock_company_query, \
         patch('project.company.routes.EmployeeAttendance.objects') as mock_attendance_query, \
         patch('project.company.routes.request') as mock_request:

        # Setup mocks
        mock_company_query.return_value.first.return_value = mock_company_details
        mock_attendance_query.return_value = [mock_employee_attendance]
        
        # Mock GET request
        mock_request.method = 'GET'

        # Call the function
        response = routes.attendance_report_download()

        # Verify response
        assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'Company_Attendance_Report' in response.headers['Content-Disposition']

def test_attendance_report_download_employee_not_found(app_context, mock_current_user):
    """Test downloading report when company details not found"""
    
    with patch('flask_login.current_user', mock_current_user), \
         patch('project.company.routes.CompanyDetails.objects') as mock_company_query, \
         patch('project.company.routes.EmployeeDetails.objects') as mock_employee_query:

        # Setup mocks
        mock_company_query.return_value.first.return_value = None
        mock_employee_query.return_value.first.return_value = None

        # Call the function
        response = routes.attendance_report_download()

        # Verify empty response
        assert response.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'Company_Attendance_Report' in response.headers['Content-Disposition']

def test_generate_excel_formats(app_context, mock_employee_attendance):
    """Test Excel generation formatting"""
    
    # Test individual employee excel
    output = routes.generate_individual_employee_excel(
        [mock_employee_attendance],
        mock_employee_attendance.employee_details_id,
        datetime.now(),
        datetime.now(),
        timedelta(hours=8)
    )
    
    assert output.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    # Test company excel 
    output = routes.generate_company_excel(
        [mock_employee_attendance],
        Mock(employees=[mock_employee_attendance]),
        datetime.now(),
        datetime.now()
    )
    
    assert output.mimetype == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'