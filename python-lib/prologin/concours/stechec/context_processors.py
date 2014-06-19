# -*- coding: utf-8 -*-
from django.conf import settings

def context_from_config(request):
    return {'use_maps': settings.STECHEC_USE_MAPS,
            'replay': settings.STECHEC_REPLAY}
