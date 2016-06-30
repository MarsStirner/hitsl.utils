# -*- coding: utf-8 -*-
import json
import uuid
import datetime
import pytz

from decimal import Decimal


__author__ = 'viruzzz-kun'


def safe_unicode(obj):
    if obj is None:
        return None
    return unicode(obj)


def safe_int(obj):
    if obj is None:
        return None
    return int(obj)


def safe_dict(obj):
    if obj is None:
        return None
    elif isinstance(obj, dict):
        for k, v in obj.iteritems():
            obj[k] = safe_dict(v)
        return obj
    elif hasattr(obj, '__json__'):
        return safe_dict(obj.__json__())
    return obj


def string_to_datetime(date_string, formats=None, tz='Europe/Moscow'):
    if formats is None:
        formats = ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%S+00:00', '%Y-%m-%dT%H:%M:%S.%f+00:00')
    elif not isinstance(formats, (tuple, list)):
        formats = (formats, )

    if date_string:
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(date_string, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError
        return pytz.timezone('UTC').localize(dt).astimezone(tz=tz).replace(tzinfo=None)
    else:
        return date_string


def safe_datetime(val, tz='Europe/Moscow'):
    if not val:
        return None
    if isinstance(val, basestring):
        try:
            val = string_to_datetime(val, tz=tz)
        except ValueError:
            try:
                val = string_to_datetime(val, '%Y-%m-%d', tz=tz)
            except ValueError:
                return None
        return val
    elif isinstance(val, datetime.datetime):
        return val
    elif isinstance(val, datetime.date):
        return datetime.datetime(val.year, val.month, val.day)
    else:
        return None


def safe_date(val, tz='Europe/Moscow'):
    if not val:
        return None
    if isinstance(val, basestring):
        try:
            val = string_to_datetime(val, tz=tz)
        except ValueError:
            try:
                val = string_to_datetime(val, '%Y-%m-%d', tz=tz)
            except ValueError:
                return None
        return val.date()
    elif isinstance(val, datetime.datetime):
        return val.date()
    elif isinstance(val, datetime.date):
        return val
    else:
        return None


def safe_time_as_dt(val):
    if not val:
        return None
    if isinstance(val, basestring):
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                val = datetime.datetime.strptime(val, fmt)
                break
            except ValueError:
                continue
        return val
    elif isinstance(val, datetime.datetime):
        return val
    else:
        return None


def safe_time(val):
    if not val:
        return None
    val = safe_time_as_dt(val)
    if isinstance(val, datetime.datetime):
        return val.time()
    else:
        return None


def safe_traverse(obj, *args, **kwargs):
    """Безопасное копание вглубь dict'а
    @param obj: точка входя для копания
    @param *args: ключи, по которым надо проходить
    @param default=None: возвращаемое значение, если раскопки не удались
    @rtype: any
    """
    default = kwargs.get('default', None)
    if obj is None:
        return default
    if len(args) == 0:
        raise ValueError(u'len(args) must be > 0')
    elif len(args) == 1:
        return obj.get(args[0], default)
    else:
        return safe_traverse(obj.get(args[0]), *args[1:], **kwargs)


def safe_traverse_attrs(obj, *args, **kwargs):
    default = kwargs.get('default', None)
    if obj is None:
        return default
    if len(args) == 0:
        raise ValueError(u'len(args) must be > 0')
    elif len(args) == 1:
        return getattr(obj, args[0], default)
    else:
        return safe_traverse_attrs(getattr(obj, args[0]), *args[1:], **kwargs)


def safe_bool(val):
    if isinstance(val, (str, unicode)):
        return val.lower() not in ('0', 'false', '\x00', '')
    return bool(val)


def safe_bool_none(val):
    if val is None:
        return None
    return safe_bool(val)


def safe_double(val):
    if val is None:
        return None
    if isinstance(val, basestring):
        val = val.replace(',', '.')
    try:
        val = float(val)
    except ValueError:
        val = None
    return val


def safe_decimal(val):
    if val is None:
        return None
    val = Decimal(val)
    return val


def format_money(val, scale=2):
    if val is None:
        return None
    if isinstance(val, Decimal):
        twoplaces = Decimal(10) ** -scale
        val = val.quantize(twoplaces)
    return '{{0:.{0}f}}'.format(scale).format(val)


def safe_uuid(val):
    if not isinstance(val, basestring):
        return None
    try:
        u_obj = uuid.UUID(val)
    except ValueError:
        return None
    return u_obj


def safe_hex_color(val):
    if not isinstance(val, basestring):
        return None
    if val.startswith('#') and len(val) == 7:
        return val[1:]


def format_hex_color(val):
    if not isinstance(val, basestring):
        return None
    if len(val) == 6:
        val = '#' + val
    if val.startswith('#') and len(val) == 7:
        return val


def format_date(d):
    if isinstance(d, datetime.date):
        return d.strftime('%d.%m.%Y')
    else:
        return d


def parse_json(json_string):
    try:
        result = json.loads(json_string)
    except (ValueError, TypeError):
        result = None
    return result


def get_utc_datetime_with_tz(dt=None, tz='Europe/Moscow'):
    """Получить датувремя в ютс с таймзоной.
    С последующим .isoformat() результат будет в таком же формате,
    как в запросе из браузера"""
    if not dt:
        dt = datetime.datetime.now()
    dt_with_tz = pytz.timezone(tz).localize(dt)
    return dt_with_tz.astimezone(pytz.timezone('UTC'))
