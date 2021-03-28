from django import template
from datetime import datetime

register = template.Library()


@register.inclusion_tag("date.html")
def fmt_date(unix_time):
    timestamp = datetime.utcfromtimestamp(unix_time)
    return {"date": timestamp.strftime("%Y-%m-%d")}


@register.inclusion_tag("date.html")
def fmt_datetime(unix_time):
    timestamp = datetime.utcfromtimestamp(unix_time)
    return {"date": timestamp.strftime("%Y-%m-%d %H:%M")}
