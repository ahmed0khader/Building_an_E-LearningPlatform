from django import forms
from django.forms.models import inlineformset_factory
from .models import Course, Module


# • can_delete: إذا قمت بتعيين هذا على True ، فسيقوم Django بتضمين حقل منطقي لكل نموذج
ModuleFormSet = inlineformset_factory(Course, Module, 
                                        fields=['title', 'description'], 
                                        extra=2, 
                                        can_delete=True)