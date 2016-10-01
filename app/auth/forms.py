# -*- coding:utf-8 -*-

from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User

class LoginForm(Form):
    email = StringField('Email', validators=[Required(), Length(1,64),
                                             Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('keep me logged in')
    submit = SubmitField('Sign In')

class RegistrationForm(Form):
    email = StringField('Email', validators=[Required(), Length(1,64),
                                             Email()])
    username = StringField('Username', validators=[Required(), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                                                      'Username must have only letters,'
                                                                      'numbers, dots or underscores')])
    password = PasswordField('Password', validators=[Required(), Length(6, 32),
                                                EqualTo('password2', message="Password must match.")])
    password2 = PasswordField('Confirm Password', validators=[Required()])
    submit = SubmitField('Sign Up')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registraed.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already registraed.')

class ChangePasswordForm(Form):
    old_password = PasswordField('Old Password', validators=[Required()])
    new_password = PasswordField('New Password', validators=[Required(), Length(6,32),
                                                             EqualTo('password1', message="password must match.")])
    password1 = PasswordField('Confirm Passwrod', validators=[Required()])
    submit = SubmitField('Update Password')


class PasswordResetRequestForm(Form):
    email = StringField('Email', validators=[Required(), Length(1,64),
                                             Email()])
    submit = SubmitField('Reset Password')

class ResetPasswordForm(Form):
    email = StringField('Email', validators=[Required(), Length(1,64),
                                             Email()])
    password = PasswordField('New Password', validators=[Required(), Length(6, 64),
                                                         EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[Required()])
    submit = SubmitField('Reset Password')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError("Unknown email address")

class EmailChangeRequestForm(Form):
    email = StringField('New Email', validators=[Required(), Length(1,64),
                                             Email()])
    password = PasswordField('password',validators=[Required()])
    submit = SubmitField('Change Email')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already register.')
