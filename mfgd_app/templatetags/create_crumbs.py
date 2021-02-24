from django import template

register = template.Library()


@register.inclusion_tag("crumbs.html")
def create_crumbs(path, depth):
    chunks = path.rstrip("/").split("/")
    block = [(path, chunks[-1])]

    for i in range(1, depth):
        block.append(("/".join(chunks[:-i]) + "/", chunks[-i - 1]))
    return {"crumbs": block[::-1]}
