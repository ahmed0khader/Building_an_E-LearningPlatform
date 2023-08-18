from typing import Any, Dict
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from braces.views import  CsrfExemptMixin, JsonRequestResponseMixin
# Adding content to course modules
from django.forms.models import modelform_factory
from django.apps import apps
from .forms import ModuleFormSet
from .models import Course, Module, Content, Subject
from django.db.models import Count
from students.forms import CourseEnrollForm
# Memcached
from django.core.cache import cache

# Create your views here.

# يسرد الدورات التدريبية التي أنشأها المستخدم. يرث من OwnerCourseMixin
class ManageCourseListView(ListView):
    model = Course
    template_name = 'courses/manage/course/list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)
    
class OwnerMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin:
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)
    
# لبناء نموذج النموذج وكذلك الفئات الفرعية
class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin, PermissionRequiredMixin):
    model = Course
    fields = ['subject', 'title', 'slug', 'overview']
    success_url = reverse_lazy('manage_course_list')


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    template_name = 'courses/manage/course/form.html'
    
# يسرد الدورات التدريبية التي أنشأها المستخدم. يرث من OwnerCourseMixin
# إدارة عرض قائمة المقرر الدراسي
class ManageCourseListView(OwnerCourseMixin, ListView):
    template_name = 'courses/manage/course/list.html'
    permission_required = 'courses.view_course'
    
# يستخدم نموذجًا لإنشاء كائن دورة تدريبية جديد
class CourseCreateView(OwnerCourseEditMixin, CreateView):
    permission_required = 'courses.add_course'

# يسمح بتحرير كائن الدورة التدريبية الموجود. يستخدم الحقول المحددة
class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    permission_required = 'courses.change_course'

# يسمح بحذف كائن الدورة التدريبية الموجودة
class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = 'courses/manage/course/delete.html'
    permission_required = 'courses.delete_course'
    
    
    
# 581
class CourseModuleUpdateView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/formset.html'
    course = None
    
    # أنت تحدد هذه الطريقة لتجنب تكرار الكود لبناء مجموعة formset.
    def get_formset(self, data=None):
        return ModuleFormSet(instance=self.course, data=data)
    
    def dispatch(self, request, pk):
        self.course = get_object_or_404(Course, id=pk, owner=request.user)
        return super().dispatch(request, pk)
    
    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response({
            'course': self.course,
            'formset': formset
            })

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response({
            'course': self.course,
            'formset': formset
        })
        
# Adding content to course modules # إضافة محتوى إلى وحدات الدورة

class ContentCreateUpdateView(TemplateResponseMixin, View):
    module = None
    model = None
    obj = None
    template_name = 'courses/manage/content/form.html'
    
    # تتحقق من أن اسم النموذج المحدد هو أحد نماذج المحتوى الأربعة
    def get_model(self, model_name):
        if model_name in ['text', 'video', 'image', 'file']:
            return apps.get_model(app_label='courses', model_name=model_name)
        return None
    
    # يمكنك إنشاء نموذج ديناميكي باستخدام وظيفة modelform_factory () للنموذج
    def get_form(self, model, *args, **kwargs):
        Form = modelform_factory(model, exclude=['owner',
                                                'order',
                                                'created',
                                                'updated'])
        return Form(*args, **kwargs)
    
    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(Module, id=module_id, course__owner=request.user)
        self.model = self.get_model(model_name)
        if id:
            self.obj = get_object_or_404(self.model, id=id, owner=request.user)
        return super().dispatch(request, module_id, model_name, id)
    
    # يتم تنفيذه عند استلام طلب GET
    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response({
            'form': form,
            'object': self.obj
            })
    
    # يتم تنفيذه عند استلام طلب POST
    def post(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model,
                                instance=self.obj,
                                data=request.POST,
                                files=request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            if not id:
                # new content
                Content.objects.create(module=self.module, item=obj)
            return redirect('module_content_list', self.module.id)
        return self.render_to_response({
            'form': form,
            'object': self.obj
            })
        
class ContentDeleteView(View):
    def post(self, request, id):
        content = get_object_or_404(Content,
                                    id=id,
                                    module__course__owner=request.user)
        module = content.module
        content.item.delete()
        content.delete()
        return redirect('module_content_list', module.id)
    
class ModuleContentListView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/content_list.html'

    def get(self, request, module_id):
        module = get_object_or_404(Module,
                                    id=module_id,
                                    course__owner=request.user)
        return self.render_to_response({'module': module})
    
    
# 596 => 569 Using mixins from django-braces
# هذا هو عرض ، الذي يسمح لك بتحديث ترتيب وحدات الدورة التدريبية.
class ModuleOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Module.objects.filter(id=id, course__owner=request.user).update(order=order)
        return self.render_json_response({'saved': 'OK'})
    
    
class ContentOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Content.objects.filter(id=id, module__course__owner=request.user).update(order=order)
        return self.render_json_response({'saved': 'OK'})
    

# Chapter 14
class CourseListView(TemplateResponseMixin, View):
    model = Course
    template_name = 'courses/course/list.html'
    def get(self, request, subject=None):
        subjects = cache.get('all_subjects')
        
        if not subjects:
            # # إذا لم يتم العثور على أي مفتاح (لم يتم تخزينه مؤقتًا أو تخزينه مؤقتًا ولكن انتهت مهلته)
            subjects = Subject.objects.annotate(total_courses=Count('courses'))
            # قم بتخزين النتيجة بشكل مؤقت
            cache.set('all_subjects', subjects)
            
        # يمكنك استرداد جميع الدورات التدريبية المتاحة ، بما في ذلك إجمالي عدد الوحدات الموجودة في كل منها
        all_courses = Course.objects.annotate(total_modules=Count('modules'))
        
        if subject:
            subject = get_object_or_404(Subject, slug=subject)
            key = f'subject_{subject.id}_courses'
            courses = cache.get(key)
            if not courses:
                courses = all_courses.filter(subject=subject)
                cache.set(key, courses)
        else:
            courses = cache.get('all_courses')
            if not courses:
                courses = all_courses
                cache.set('all_courses', courses)
                
        return self.render_to_response({
            'subjects': subjects,
            'subject': subject,
            'courses': courses
            })
        
        
# إنشاء عرض تفصيلي لعرض نظرة عامة على الدورة التدريبية الواحدة
class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'
    
    # هذا يحدد القيمة الأولية للحقل "course" من النموذج
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enroll_form'] = CourseEnrollForm(
            initial={'course':self.object}
        )
        return context