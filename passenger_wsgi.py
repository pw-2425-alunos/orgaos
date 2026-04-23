import sys
import os

project_home = '/home/obmdatab/repositories/orgaos-2'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
