from django import template

register = template.Library()

@register.inclusion_tag("icon.html")
def select_icon(entry):
    context = {}
    if entry.isdir():
        context["alt"] = "tree"
        context["icon"] = "icons/dir.png"
    elif entry.issubmod():
        context["alt"] = "submodule"
        context["icon"] = "icons/mod.png"
    else:
        context["alt"] = "blob"
        if entry.is_binary:
            context["icon"] = "icons/binary_file.png"
        else:
            context["icon"] = "icons/file.png"

    return context
