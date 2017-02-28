# -*- coding:utf-8 -*-

from datetime import datetime, timedelta

from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user,logout_user,  login_required, current_user
from . import auth
from .. import db, oauth
from ..email import send_mail
from ..models import User, Client, Grant, Token
from .forms import LoginForm, RegistrationForm, ChangePasswordForm,\
                   PasswordResetRequestForm, ResetPasswordForm, EmailChangeRequestForm


@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.':
            return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Invalid username or password')
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_mail(user.email, 'Confirm Your Account',
                   'auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_mail(current_user.email, 'Confirm Your Accout',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('auth.unconfirmed'))

@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.new_password.data
            db.session.add(current_user)
            flash('Your password already changed.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid Password')
    return render_template('auth/change_password.html', form=form)

@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_mail(user.email, "Reset Your Password",
                      "auth/email/reset_password", user=user,
                      token=token, next=request.args.get('next'))
            flash('An email with instructions to reset your password has been '
                  'sent to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)

@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def email_change_request():
    form = EmailChangeRequestForm()
    if form.validate_on_submit():
        if current_user.verify_password(password=form.password.data):
            new_email = form.email.data
            token = current_user.generate_change_email_token(new_email)
            send_mail(new_email, 'Change Email',
                      'auth/email/change_email', user=current_user,
                      token=token)
            flash('A change email message already sent to you by email.')
            return redirect(url_for('main.index'))
        else:
            flash("Invalid email or password")
    return render_template('auth/change_email.html', form=form)

@auth.route('/change-email/<token>')
@login_required
def email_change(token):
    if current_user.change_email(token):
        flash('Your email has been change.')
    else:
        flash('Invalid Request.')
    return redirect(url_for('main.index'))

@oauth.clientgetter
def load_client(client_id):
    return Client.query.filter_by(client_id=client_id).first()

@oauth.grantgetter
def load_grant(client_id, code):
    return Grant.query.filter_by(client_id=client_id, code=code).first()

@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    expires = datetime.utcnow() + timedelta(seconds=600)
    grant = Grant(
        client_id = client_id,
        code = code['code'],
        redirect_url = request.redirect_uri,
        _scopes = ' '.join(request.scopes),
        user = request.user,
        expires = expires
    )
    db.session.add(grant)
    db.session.commit()
    return grant

@oauth.tokengetter
def load_token(access_token=None, refresh_token=None):
    if access_token:
        return Token.query.filter_by(access_token=access_token).first()
    elif refresh_token:
        return Token.query.filter_by(refresh_token=refresh_token).first()

@oauth.tokensetter
def save_token(token, request, *args, **kwargs):
    toks = Token.query.filter_by(client_id=request.client.client_id,
                                  user_id=request.user.id)
    for t in toks:
        db.session.delete(t)

    expires_in = token.get('expires_in')
    expires = datetime.utcnow() + timedelta(seconds=expires_in)

    tok = Token(
        access_token = token['access_token'],
        refresh_token = token['refresh_token'],
        token_type = token['token_type'],
        _scopes = token['scopes'],
        expires = expires,
        client_id = request.client.client_id,
        user_id = request.user.id
    )
    db.session.add(tok)
    db.session.commit()
    return tok

@auth.route('/oauth/authorize', methods=['GET', 'POST'])
@login_required
@oauth.authorize_handler
def authorize(*args, **kwargs):
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        kwargs['client'] = client
        return render_template('oauthorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'

@auth.route('/oauth/token')
@oauth.token_handler
def access_token():
    return None

@auth.route('/oauth/revoke', methods=['GET'])
@oauth.revoke_handler
def revoke_token():
    pass

@auth.route('/client')
@login_required
def client():
    form = Client()
    if form.validate_on_submit():
        item = Client(
            name=form.name.data,
            description=form.description.data,
            user=current_user._get_current_object(),
            client_id=form.client_id.data,
            client_secret=form.client_secret.data,
            is_confidential=form.is_confidential.data,
            _redirect_urls=form._redirect_urls.data,
            _default_scopes=form._default_scopes.data
        )
        db.session.add(item)
        db.session.commit()
        flash('client has been update.')
        return redirect(url_for('main.index'))
    return render_template('auht/client.html')

