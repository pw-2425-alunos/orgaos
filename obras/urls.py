
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns_ = [
    path('', views.landing_view, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('pesquisa/', views.pesquisa_view, name='pesquisa'),
    path('obras/novo', views.criar_obra_view, name="criar_obra"),
    path('compositores/', views.compositores_view, name='compositores'),
    path('compositores/<int:id>', views.compositor_view, name="compositor"),
    path('obras/<int:id>', views.obra_view, name="obra"),
    path('obras/<int:id>/editar', views.editar_obra_view, name="editar_obra"),
]
