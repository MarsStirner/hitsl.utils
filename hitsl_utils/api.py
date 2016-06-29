# -*- coding: utf-8 -*-
from decimal import Decimal
import functools
import json
import traceback
import datetime
from flask import make_response

__author__ = 'viruzzz-kun'


class ApiException(Exception):
    """Исключение в API-функции
    :ivar code: HTTP-код ответа и соответствующий код в метаданных
    :ivar message: текстовое пояснение ошибки
    """
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return u'%s %s' % (self.code, self.message)


def json_default_webmis(o, app):
    from pytz import timezone

    if app:
        try:
            return timezone(app.config['TIME_ZONE']).localize(o).astimezone(tz=timezone('UTC')).isoformat()
        except OverflowError:
            pass


class WebMisJsonEncoder(json.JSONEncoder):
    flask_app = None
    unicodes = ()

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        elif isinstance(o, (datetime.date, datetime.time)):
            return o.isoformat()
        elif isinstance(o, Decimal):
            return float(o)
        elif hasattr(o, '__json__'):
            return o.__json__()
        elif isinstance(o, self.unicodes) and hasattr(o, '__unicode__'):
            return unicode(o)
        return json.JSONEncoder.default(self, o)


def jsonify_int(obj, result_code=200, result_name='OK', indent=None):
    """
    Преобразование объекта к стандартному json-ответу с данными и метаданными без формирования http-ответа
    :param obj: сериализуемый объект
    :param result_code: код результата
    :param result_name: наименование результата
    :return: json-строка
    :type obj: any
    :type result_code: int
    :type result_name: str|unicode
    :rtype: str
    """
    return json.dumps({
        'result': obj,
        'meta': {
            'code': result_code,
            'name': result_name,
        }
    }, indent=indent, cls=WebMisJsonEncoder, encoding='utf-8', ensure_ascii=False)


def jsonify_response(body, result_code=200, extra_headers=None):
    """
    Формирование http-ответа из json-ифицированного тела
    :param body: json-ифицированное тело (jsonify_int)
    :param result_code: http-код результата
    :param extra_headers: дополнительные http-заголовки
    :return: flask response
    :type body: str
    :type result_code: int
    :type extra_headers: list
    :rtype: flask.wrappers.Response
    """
    headers = [('content-type', 'application/json; charset=utf-8')]
    if extra_headers:
        headers.extend(extra_headers)
    return make_response((body, result_code, headers))


def jsonify(obj, result_code=200, result_name='OK', extra_headers=None, indent=None):
    """
    Convenience-функция, преобразуцющая объект к стандартному http-json-ответу
    :param obj: сериализуемый объект
    :param result_code: код результата, http-код
    :param result_name: наименование результата
    :param extra_headers: дополнительные заголовки
    :return: flask response
    :type obj: any
    :type result_code: int
    :type result_name: str|unicode
    :type extra_headers: list
    :rtype: flask.wrappers.Response
    """
    return jsonify_response(jsonify_int(obj, result_code, result_name, indent), result_code, extra_headers)


def api_method(func):
    """Декоратор API-функции. Автомагически оборачивает результат или исключение в jsonify-ответ
    :param func: декорируемая функция
    :type func: callable
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except ApiException, e:
            traceback.print_exc()
            return jsonify(None, e.code, e.message)
        except Exception, e:
            traceback.print_exc()
            return jsonify(None, 500, repr(e))
        else:
            return jsonify(result)
    return wrapper


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, datetime.timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = flask.current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and flask.request.method == 'OPTIONS':
                resp = flask.current_app.make_default_options_response()
            else:
                resp = flask.make_response(f(*args, **kwargs))
            if not attach_to_all and flask.request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return functools.update_wrapper(wrapped_function, f)
    return decorator
