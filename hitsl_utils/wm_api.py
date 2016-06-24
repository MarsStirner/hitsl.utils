# -*- coding: utf-8 -*-

import functools
import json
import traceback
import datetime
import sys
import flask

from decimal import Decimal
from pytz import timezone


__author__ = 'viruzzz-kun'


class WebMisJsonEncoder(json.JSONEncoder):
    flask_app = None
    unicodes = ()

    def default(self, o):
        if isinstance(o, datetime.datetime):
            if self.flask_app:
                try:
                    return timezone(self.flask_app.config['TIME_ZONE']).localize(o).astimezone(tz=timezone('UTC')).isoformat()
                except OverflowError:
                    pass
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


class ApiException(Exception):
    """Исключение в API-функции
    :ivar code: HTTP-код ответа и соответствующий код в метаданных
    :ivar message: текстовое пояснение ошибки
    """
    def __init__(self, code, message, **kwargs):
        self.code = code
        self.message = message
        self.extra = kwargs

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        if not self.extra:
            return u'<ApiException(%s, u\'%s\')>' % (self.code, self.message)
        else:
            return u'<ApiException(%s, u\'%s\', %s)' % (
                self.code,
                self.message,
                u', '.join(u'%s=%r' % (k, v) for k, v in self.extra.iteritems())
            )


def json_dumps(result, pretty=False):
    more_args = {}
    if pretty:
        more_args.update(dict(sort_keys=True, indent=4, separators=(',', ': ')))
    return json.dumps(result, cls=WebMisJsonEncoder, encoding='utf-8', ensure_ascii=False, **more_args)


def encode_tb(part):
    enc = 'utf-8'
    return [
        part[0].decode(enc) if part[2] else None,
        part[1],
        part[2].decode(enc) if part[2] else None,
        part[3].decode(enc) if part[3] else None,
    ]


class RawApiResult(object):
    """
    Способ управления процессом json-ификации объекта с передачей параметров в
    nemesis.lib.utils.jsonify()
    :ivar obj: arbitrary object
    :ivar result_code: HTTP response code and meta.code
    :ivar result_name: meta.name
    :ivar extra_headers: extra headers
    :ivar indent: indent size for jsonification
    """
    def __init__(self, obj, result_code=200, result_name='OK', extra_headers=None, indent=None):
        if isinstance(obj, RawApiResult):
            self.obj = obj.obj
            self.result_code = obj.result_code
            self.result_name = obj.result_name
            self.extra_headers = obj.extra_headers
            self.indent = obj.indent
        else:
            self.obj = obj
            self.result_code = result_code
            self.result_name = result_name
            self.extra_headers = extra_headers
            self.indent = indent


def jsonify_ok(obj, custom_meta_code=None, custom_meta_name=None):
    return (
        json_dumps({
            'meta': {
                'code': custom_meta_code or 200,
                'name': custom_meta_name or 'OK',
            },
            'result': obj
        }),
        200,
        {'content-type': 'application/json; charset=utf-8'}
    )


def jsonify_api_exception(exc, tb):
    meta = dict(
        exc.extra,
        code=exc.code,
        name=exc.message,
    )
    if flask.current_app.debug:
        meta['traceback'] = map(encode_tb, tb)
    return (
        json_dumps({'meta': meta, 'result': None}),
        exc.code,
        {'content-type': 'application/json; charset=utf-8'}
    )


def jsonify_exception(exc, tb):
    meta = dict(
        code=500,
        name=repr(exc),
    )
    if flask.current_app.debug:
        meta['traceback'] = map(encode_tb, tb)
    return (
        json_dumps({'meta': meta, 'result': None}),
        500,
        {'content-type': 'application/json; charset=utf-8'}
    )


def api_method(func=None, hook=None):
    """Декоратор API-функции. Автомагически оборачивает результат или исключение в jsonify-ответ
    :param func: декорируемая функция
    :type func: callable
    :param hook: Response hook
    :type: callable
    """
    def decorator(func):
        func.is_api = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
            except ApiException, e:
                traceback.print_exc()
                j, code, headers = jsonify_api_exception(e, traceback.extract_tb(sys.exc_info()[2]))
                if hook:
                    hook(code, j, e)
            except Exception, e:
                traceback.print_exc()
                j, code, headers = jsonify_exception(e, traceback.extract_tb(sys.exc_info()[2]))
                if hook:
                    hook(code, j, e)
            else:
                if isinstance(result, RawApiResult):
                    j, code, headers = jsonify_ok(result.obj, result.result_code, result.result_name)
                    if result.extra_headers:
                        headers.update(result.extra_headers)
                else:
                    j, code, headers = jsonify_ok(result)
                if hook:
                    hook(code, j)
            return flask.make_response(j, code, headers)

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


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