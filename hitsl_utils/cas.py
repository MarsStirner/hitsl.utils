# -*- coding: utf-8 -*-
import logging
import blinker
import requests
import urllib2
from flask import request, redirect, json, session
from hitsl_utils.api import jsonify

__author__ = 'viruzzz-kun'


logger = logging.getLogger('CasExtension')
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


class CasError(Exception):
    pass


class CasNotAvailable(CasError):
    message = u'Castiel not available'


class CasAuthApiException(CasError):
    message = u'Пользователь не аутентифицирован'


class CasExtension(object):
    """
    Extension for working with CAS Castiel
    """
    user_id_changed = blinker.Signal()

    def __init__(self, app=None):
        if app is None:
            self.cookie_name = 'CastielAuthToken'
            self.cas_external_address = 'http://127.0.0.1:5001/'
            self.cas_internal_address = self.cas_external_address
        else:
            self.init_app(app)
        self.app = app

    @staticmethod
    def __make_config(app):
        config = app.config.get('CASTIEL', {})
        for key, value in app.config.iteritems():
            if key.startswith('CASTIEL_'):
                config[key[7:]] = value.strip().rstrip('/')
        config['ADDRESS'] = app.config['COLDSTAR_URL']
        config.setdefault('AUTH_COOKIE', 'CastielAuthToken')
        config.setdefault('ADDRESS', 'http://127.0.0.1:5001')
        config.setdefault('ADDRESS_INTERNAL', config['ADDRESS'])
        return config

    def init_app(self, app):
        """
        Install Extension at app
        :type app: flask.app.Flask
        :param app: Application
        :return:
        """
        self.app = app
        config = self.__make_config(app)
        self.cookie_name = config['AUTH_COOKIE']
        self.cas_external_address = config['ADDRESS']
        self.cas_internal_address = config['ADDRESS_INTERNAL']
        app.before_request(self._before_request)
        app.errorhandler(CasNotAvailable)(self._cas_not_available)
        app.errorhandler(CasAuthApiException)(self._cas_auth_api_exception)

    def _before_request(self):
        if not (request.endpoint and 'static' not in request.endpoint and
                not getattr(self.app.view_functions[request.endpoint], 'cas_is_public', False)):
            return

        token = request.cookies.get(self.cookie_name)
        if not token:
            return self._abort()

        cas_response = self._check_cas_token(token)
        if cas_response.status_code != 200:
            return self._abort()

        cas_data = cas_response.json()
        if not cas_data['success']:
            return self._abort()

        user_id = cas_data['user_id']
        if user_id != session.get('user_id'):
            self.user_id_changed.send(self.app, old=session.get('cas_user_id'), new=user_id)
            session['cas_user_id'] = user_id

    def _check_cas_token(self, token):
        try:
            result = requests.post(
                self.cas_internal_address + 'cas/api/check',
                data=json.dumps({'token': token, 'prolong': True}),
                headers={'Referer': request.url.encode('utf-8')}
            )
        except requests.ConnectionError:
            raise CasNotAvailable
        return result

    def _abort(self):
        is_api = getattr(self.app.view_functions[request.endpoint], 'is_api', False)
        return self._api_auth_error() if is_api else self._redirect_to_cas()

    def _redirect_to_cas(self):
        return redirect(
            self.cas_external_address +
            'cas/login?back=%s' % urllib2.quote(request.url.encode('utf-8'))
        )

    def _api_auth_error(self):
        raise CasAuthApiException

    def _cas_not_available(self, e):
        is_api = getattr(self.app.view_functions[request.endpoint], 'is_api', False)
        msg = u'Невозможно связаться с подсистемой централизованной аутентификации'
        if is_api:
            return jsonify(None, 500, msg)
        else:
            return msg

    def _cas_auth_api_exception(self, e):
        return jsonify(None, 401, e.message)

    def public(self, function):
        """
        Use this decorator to indicate that view function is public and should not be passed through CAS
        :param function:
        :return:
        """
        function.cas_is_public = True
        return function
