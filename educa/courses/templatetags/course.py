from django import template
# هذا هو عامل تصفية نموذج اسم_النموذج.
register = template.Library()

@register.filter
def model_name(obj):
    try:
        return obj._meta.model_name
    except AttributeError:
        return None