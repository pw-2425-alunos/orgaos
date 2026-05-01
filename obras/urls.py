
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.cache import never_cache
from . import views

urlpatterns = [
    path('', never_cache(views.landing_view), name='landing'),
    path('web/', never_cache(views.landing_view)),
    path('login/', never_cache(views.login_view), name='login'),
    path('logout/', never_cache(views.logout_view), name='logout'),
    path('pesquisa/', never_cache(views.pesquisa_view), name='pesquisa'),
    path('obras/novo', never_cache(views.criar_obra_view), name="criar_obra"),
    path('compositores/', never_cache(views.compositores_view), name='compositores'),
    path('compositores/novo', never_cache(views.criar_compositor_view), name='criar_compositor'),
    path('compositores/<int:id>', never_cache(views.compositor_view), name="compositor"),
    path('compositores/<int:id>/editar', never_cache(views.editar_compositor_view), name='editar_compositor'),
    path('obras/<int:id>', never_cache(views.obra_view), name="obra"),
    path('obras/<int:id>/editar', never_cache(views.editar_obra_view), name="editar_obra"),
    path('sobre/', never_cache(views.sobre_view), name="sobre"),
]
