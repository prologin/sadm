# -*- encoding: utf-8 -*-
# Copyright (c) 2013 Association Prologin <info@prologin.org>
#
# Prologin-SADM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prologin-SADM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prologin-SADM.  If not, see <http://www.gnu.org/licenses/>.

from django.core.urlresolvers import reverse_lazy
from prologin.djangoconf import use_profile_config

cfg = use_profile_config('concours')

ALLOWED_URLS = ['*']

SITE_ID = 1

LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('home')

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# URL prefix for static files.
STATIC_URL = '/static/'

STATICFILES_DIRS = ()
if 'static_path' in cfg['website']:
    # Overwrite local static files with static_path assets
    STATICFILES_DIRS = (cfg['website']['static_path'],)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MIDDLEWARE_CLASSES = (
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'prologin.sso.django.SSOMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'prologin.sso.django.SSOUserBackend',
    'django.contrib.auth.backends.ModelBackend',
)

ROOT_URLCONF = 'prologin.concours.urls'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'prologin.concours.stechec.context_processors.inject_settings',
            ]
        }
    },
]

INSTALLED_APPS = (
    # Built-in
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Vendor
    'crispy_forms',

    # Prologin
    'prologin.concours.stechec',

    # Built-in or vendor (for template overriding)
    'rest_framework',
    'django.contrib.admin',

    # Monitoring
    'django_prometheus',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

# This is actually the default, explicit is better than implicit
AUTH_USER_MODEL = 'auth.User'

# crispy-forms shall use Bootstrap 3
CRISPY_TEMPLATE_PACK = 'bootstrap3'

STECHEC_ROOT = cfg["contest"]["directory"]
STECHEC_CONTEST = cfg["contest"]["game"]
STECHEC_MASTER = cfg["master"]["url"]
STECHEC_MASTER_SECRET = cfg["master"]["shared_secret"].encode('utf-8')
STECHEC_NPLAYERS = cfg["contest"]["nb_players"]
STECHEC_USE_MAPS = cfg["contest"]["use_maps"]
STECHEC_REPLAY = cfg["website"]["replay"]
STECHEC_REDMINE_ISSUE_LIST = cfg["redmine_urls"]["issue_list"]
STECHEC_REDMINE_ISSUE_NEW = cfg["redmine_urls"]["issue_new"]

# Rest Framework settings
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticatedOrReadOnly',),
    'PAGE_SIZE': 10,
    'DEFAULT_VERSION': '1',
}