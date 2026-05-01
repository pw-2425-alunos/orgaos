import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()


from django.contrib.auth.models import User


# Verificar se o utilizador admin já existe
if not User.objects.filter(username='admin').exists():
    User.objects.create_user(
        username='org',
        password='org26'
    )
    print("✓ Utilizador 'admin' criado com sucesso!")
else:
    print("✓ Utilizador 'admin' já existe.")
