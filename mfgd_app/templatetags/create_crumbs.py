from django import template
from mfgd_app import utils

register = template.Library()

@register.inclusion_tag("crumbs.html")
def create_crumbs(oid, path, branches):
    crumbs = []

    chunks = utils.split_path(path)
    for i in range(len(chunks)):
        crumbs.append((utils.get_parent(len(chunks) - i - 1), chunks[i]))

    return {
        "oid": oid,
        "root": utils.get_parent(len(chunks)),
        "crumbs": crumbs,
        "branches": branches if oid in branches else list(branches) + [oid] }
