from django.contrib import admin
from .models import *

admin.site.register(Compositor)

class ObraAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'compositor', 'ano',)
    search_fields = ('titulo', 'compositor__nome')
    list_filter = ('genero',)

admin.site.register(Obra, ObraAdmin)
admin.site.register(Nota)
admin.site.register(Extensao)
admin.site.register(Orgao)
admin.site.register(Registacao)
admin.site.register(Genero)
