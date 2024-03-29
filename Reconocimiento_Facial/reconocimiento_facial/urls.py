
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from recognition import views as recog_views
from users import views as users_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', recog_views.home, name='home'),

    path('dashboard/', recog_views.dashboard, name='dashboard'),
    path('train/', recog_views.train, name='train'),
    path('add_photos/', recog_views.add_photos, name='add-photos'),

    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='recognition/home.html'), name='logout'),
    path('register/', users_views.register, name='register'),
    path('mark_your_attendance', recog_views.mark_your_attendance,
         name='mark-your-attendance'),
    path('mark_your_attendance_out', recog_views.mark_your_attendance_out,
         name='mark-your-attendance-out'),
    path('view_attendance_home', recog_views.view_attendance_home,
         name='view-attendance-home'),

    path('view_attendance_date', recog_views.view_attendance_date,
         name='view-attendance-date'),
    path('view_attendance_employee', recog_views.view_attendance_employee,
         name='view-attendance-employee'),
    path('view_my_attendance', recog_views.view_my_attendance_employee_login,
         name='view-my-attendance-employee-login'),
    path('view_configuracion_horarios', recog_views.view_configuracion_horarios,
         name='view_configuracion_horarios'),


    path('not_authorised', recog_views.not_authorised, name='not-authorised'),
    path('mostrar_horarios', recog_views.mostrar_horarios, name='mostrar_horarios')

]
