# -*- coding:utf-8 -*-

from flask import Blueprint

main = Blueprint('main', __name__)

@main.app_context_processor
def inject_permission():
    return dict(Permission=Permission)

from . import errors, views
