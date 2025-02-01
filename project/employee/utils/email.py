from flask import Blueprint, jsonify, render_template,request,flash,redirect,url_for,json,session
from flask_mail import Message

from ... import create_app,create_celery_app, mail

celery = create_celery_app()


@celery.task(track_started=True, result_extended=True, name='Leave-Application-Status-Update')
def send_email(template, data, current_app):

    mail_server = current_app.config['MAIL_SERVER']
    mail_port = current_app.config['MAIL_PORT']
    mail_use_tls = current_app.config['MAIL_USE_TLS']
    mail_username = current_app.config['MAIL_USERNAME']
    mail_password = current_app.config['MAIL_PASSWORD']

    current_app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USERNAME=mail_username,
        MAIL_PASSWORD=mail_password
    )
    mail.init_app(current_app)

    with current_app.app_context():
        receiver_email = data['receiver_email']
        html = render_template(template_name_or_list=template, data=data)
        msg = Message('Leave Application Approval Required! | Cubes HRMS', sender=("Cubes HRMS", current_app.config['MAIL_USERNAME']), recipients=[receiver_email])
        msg.html = html
        mail.send(msg)
        return True
