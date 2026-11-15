from django.contrib.auth import views as auth_views
from django.urls import include, path

from . import views

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('registro/', views.RegistroView.as_view(), name='registro'),
    path('panel/', views.DashboardView.as_view(), name='panel'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),

    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_lista'),
    path('usuarios/nuevo/', views.UsuarioCreateView.as_view(), name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_actualizar'),
    path('usuarios/<int:pk>/eliminar/', views.UsuarioDeleteView.as_view(), name='usuario_borrar'),
]
