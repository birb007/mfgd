from django import template

register = template.Library()

@register.filter
def subject(value):
    return value.split("\n", maxsplit=1)[0]
