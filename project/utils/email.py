# # from bson import ObjectId
# # from flask import current_app, render_template
# # from flask_mail import Message

# # # Global variable for celery
# # celery = None

# # def get_celery_app():
# #     global celery
# #     if not celery:
# #         from .. import create_celery_app
# #         from ..company.routes import company
# #         from ..employee.routes import employee
# #         celery = create_celery_app(employee_blueprint=employee, company_blueprint=company)
# #     return celery

# # # Initialize celery
# # celery = get_celery_app()

# @celery.task(track_started=True, result_extended=True, name='Leave-Application-Creation')
# def send_leave_notification_email(leave_application_id):
#     # Defer import to avoid circular import
#     from ..company.model import EmployeeLeaveApplication
#     from ..models import CompanyDetails
#     from .. import mail

#     # Get Leave application details
#     leave_application_details = EmployeeLeaveApplication.objects(_id=ObjectId(leave_application_id)).first()
#     if leave_application_details:
#         company_details = CompanyDetails.objects(user_id=leave_application_details.company_id).only('email_config').first()
#         mail_server = current_app.config['MAIL_SERVER']
#         mail_port = current_app.config['MAIL_PORT']
#         mail_use_tls = current_app.config['MAIL_USE_TLS']
#         mail_username = current_app.config['MAIL_USERNAME']
#         mail_password = current_app.config['MAIL_PASSWORD']

#         current_app.config.update(
#             MAIL_SERVER=mail_server,
#             MAIL_PORT=mail_port,
#             MAIL_USE_TLS=mail_use_tls,
#             MAIL_USERNAME=mail_username,
#             MAIL_PASSWORD=mail_password
#         )
#         mail.init_app(current_app)

#         with current_app.app_context():
#             receiver_email = leave_application_details.current_aprrover.approver_id.employee_details_id.user_id.email
#             approver_name = leave_application_details.current_aprrover.approver_id.employee_details_id.first_name
#             html = render_template('email/leave_notification.html', leave_application_details=leave_application_details, approver_name=approver_name)
#             msg = Message('Leave Application Approval Required! | Cubes HRMS', sender=("Cubes HRMS", current_app.config['MAIL_USERNAME']), recipients=[receiver_email])
#             msg.html = html
#             mail.send(msg)
#             return True

# @celery.task(track_started=True, result_extended=True, name='Leave-Application-Status-Update')
# def send_email(template, data):
#     from .. import mail
    
#     mail_server = current_app.config['MAIL_SERVER']
#     mail_port = current_app.config['MAIL_PORT']
#     mail_use_tls = current_app.config['MAIL_USE_TLS']
#     mail_username = current_app.config['MAIL_USERNAME']
#     mail_password = current_app.config['MAIL_PASSWORD']

#     current_app.config.update(
#         MAIL_SERVER=mail_server,
#         MAIL_PORT=mail_port,
#         MAIL_USE_TLS=mail_use_tls,
#         MAIL_USERNAME=mail_username,
#         MAIL_PASSWORD=mail_password
#     )
#     mail.init_app(current_app)

#     with current_app.app_context():
#         receiver_email = data['receiver_email']
#         html = render_template(template_name_or_list=template, data=data)
#         msg = Message('Leave Application Approval Required! | Cubes HRMS', sender=("Cubes HRMS", current_app.config['MAIL_USERNAME']), recipients=[receiver_email])
#         msg.html = html
#         mail.send(msg)
#         return True
