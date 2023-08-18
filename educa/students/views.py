from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

from courses.models import Course
from .forms import CourseEnrollForm


# Create your views here.

class StudentRegistrationView(CreateView):
    template_name = 'students/student/registration.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('student_course_list')
    
    def form_valid(self, form):
        result = super().form_valid(form)
        cd = form.cleaned_data
        user = authenticate(username=cd['username'], password=cd['password1'])
        login(self.request, user)
        return result

class StudentEnrollCourseView(LoginRequiredMixin, FormView):
    course = None
    form_class = CourseEnrollForm
    
    def form_valid(self, form):
        self.course = form.cleaned_data['course']
        self.course.students.add(self.request.user)
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('student_course_detail', args=[self.course.id])
    
class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'students/course/list.html'
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(students__in=[self.request.user])
    
    
class StudentCourseDetailView(DetailView):
    model = Course
    template_name = 'students/course/detail.html'
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(students__in=[self.request.user])
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # get course object
        # يسترجع هذا السطر نسخة الدورة التدريبية المحددة المرتبطة بطريقة العرض.
        course = self.get_object()
        
        # يتحقق الجزء التالي من الطريقة مما إذا كان عنوان URL يحتوي على معلمة module_id.
        if 'module_id' in self.kwargs:
            # get current module
            # إذا كان الأمر كذلك ، فإنه يجلب الوحدة المقابلة من الدورة ويضيفها إلى السياق.
            context['module'] = course.modules.get(
                id=self.kwargs['module_id']
            )
        else:
            # get first module
            # إذا لم يكن كذلك ، فإنه يضيف الوحدة الأولى من الدورة التدريبية إلى السياق.
            context['module'] = course.modules.all()[0]
        return context
    