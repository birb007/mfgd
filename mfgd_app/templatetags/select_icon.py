from django import template
from mfgd_app import utils
from mfgd_app.types import ObjectType

register = template.Library()

@register.inclusion_tag("icon.html")
def select_icon (entry):
    context = {}
    if entry.type == ObjectType.BLOB:
        context["alt"] = "blob"
        if entry.is_binary:
            context["icon"] = "icons/binary_file.png"
        else:
            context["icon"] = "icons/file.png"
    else:
        context["alt"] = "tree"
        context["icon"] = "icons/dir.png"
    return context
