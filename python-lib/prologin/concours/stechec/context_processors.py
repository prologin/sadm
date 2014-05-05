from prologin.djangoconf import use_profile_config
cfg = use_profile_config('concours')

def context_from_config(request):
    return {'use_maps': cfg['contest']['use_maps']}
