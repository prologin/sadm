# -*- coding: utf-8 -*-

import os
from MoinMoin.config import multiconfig

class Config(multiconfig.DefaultConfig):
    wikiconfig_dir = os.path.abspath(os.path.dirname(__file__))
    instance_dir = '/where/ever/your/instance/is'
    instance_dir = wikiconfig_dir
    data_dir = os.path.join(instance_dir, 'data', '')
    data_underlay_dir = os.path.join(instance_dir, 'underlay', '')

    sitename = u'ProloWiki'
    logo_string = u''

    superuser = [u"prologin", ]
    acl_rights_before = u"prologin:read,write,delete,revert,admin"
    password_checker = None

    navi_bar = [
        u'RecentChanges',
        u'FindPage',
        u'HelpContents',
    ]

    theme_default = 'modernized'

    language_default = 'fr'

    language_default    = 'fr'
    page_category_regex = ur'(?P<all>Cat[ée]gorie(?P<key>\S+))'
    page_dict_regex = ur'(?P<all>Dict(?P<key>\S+))'
    page_group_regex = ur'(?P<all>Groupe(?P<key>\S+))'
    page_template_regex = ur'(?P<all>Mod[eè]le(?P<key>\S+))'

    show_hosts = 1

    # We disable user account creation:
    actions_excluded = multiconfig.DefaultConfig.actions_excluded + ['newaccount']
