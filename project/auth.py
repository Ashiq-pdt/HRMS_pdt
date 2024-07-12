# auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash,session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required,current_user
from .models import User,CompanyDetails,user_datastore
from . import db,mail
from flask_security import roles_accepted
from bson.objectid import ObjectId
from .token import generate_confirmation_token, confirm_token
import datetime
from flask_mail import Message
from flask import current_app
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.objects(email=email).first()
    # print(user.to_json())
    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not check_password_hash(user.password, password): 
        flash('Please check your login details and try again.','danger')
        return redirect(url_for('auth.login',current_user=current_user)) # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    logged_in = login_user(user, remember=remember)
    if(logged_in):
         return redirect(url_for('main.index'))
    else:
        flash('Your account is Inactive. Please contact admin for further support.','danger')
        return redirect(url_for('auth.login'))
   

@auth.route('/signup')
def signup():
    return redirect(url_for('security.register'))

@auth.route('/signup', methods=['POST'])
def signup_post():

    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    # is_admin = False

    user = User.objects(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again  
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))

    # create new user with the form data. Hash the password so plaintext version isn't saved.
    user = user_datastore.create_user(email=email, password=generate_password_hash(password, method='sha256'),roles=['company'],type='company')
    if user:
        token = generate_confirmation_token(user.email)
        confirm_url = url_for('auth.confirm_email', token=token, _external=True)
        html = render_template('email/confirmation.html', confirm_url=confirm_url)
        msg = Message('Please confirm your email!', sender = current_app.config['MAIL_USERNAME'], recipients = [user.email])
        msg.html = html
        mail.send(msg)
        company_details = CompanyDetails(user_id=ObjectId(user.id),email=email,company_name=name).save()
    return redirect(url_for('auth.login'))

@auth.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
    if email:
        user = User.objects(email=email).first()
        if user:
            if user.confirmed:
                flash('Account already confirmed.', 'success')
            else:
                user.confirmed = True
                user.confirmed_on = datetime.datetime.now()
                user.save()
                flash('You have successfully confirmed your account. Thanks!', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('auth.login'))