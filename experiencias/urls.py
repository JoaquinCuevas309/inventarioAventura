from django.urls import path

from . import views

urlpatterns = [
    path('catalogo/', views.CatalogoView.as_view(), name='catalogo'),
    path('catalogo/<int:pk>/', views.ExperienciaDetalleView.as_view(), name='experiencia_detalle'),
    path('reservar/<int:pk>/', views.ReservarView.as_view(), name='reservar'),
    path('mis-reservas/', views.MisReservasView.as_view(), name='mis_reservas'),

    path('categorias/', views.CategoriaListView.as_view(), name='categoria_lista'),
    path('categorias/nueva/', views.CategoriaCreateView.as_view(), name='categoria_crear'),
    path('categorias/<int:pk>/editar/', views.CategoriaUpdateView.as_view(), name='categoria_actualizar'),
    path('categorias/<int:pk>/eliminar/', views.CategoriaDeleteView.as_view(), name='categoria_borrar'),

    path('experiencias/', views.ExperienciaListView.as_view(), name='experiencia_lista'),
    path('experiencias/nueva/', views.ExperienciaCreateView.as_view(), name='experiencia_crear'),
    path('experiencias/<int:pk>/editar/', views.ExperienciaUpdateView.as_view(), name='experiencia_actualizar'),
    path('experiencias/<int:pk>/eliminar/', views.ExperienciaDeleteView.as_view(), name='experiencia_borrar'),

    path('reservas/', views.InscripcionListView.as_view(), name='inscripcion_lista'),
    path('reservas/nueva/', views.InscripcionCreateView.as_view(), name='inscripcion_crear'),
    path('reservas/<int:pk>/editar/', views.InscripcionUpdateView.as_view(), name='inscripcion_actualizar'),
    path('reservas/<int:pk>/eliminar/', views.InscripcionDeleteView.as_view(), name='inscripcion_borrar'),
]
