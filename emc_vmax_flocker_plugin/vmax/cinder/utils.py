# Copyright 2015 EMC Corporation
import oslo_i18n

_translators = oslo_i18n.TranslatorFactory(domain='oslo.log')
_ = _translators.primary

_LI = _translators.log_info
_LW = _translators.log_warning
_LE = _translators.log_error
_LC = _translators.log_critical


def extract_host(host, level='backend', default_pool_name=False):
    value = None

    host_ar = host.split('#')
    if level == 'host':
        value = host_ar[0].split('@')[0]
    elif level == 'backend':
        value = host_ar[0]
    elif level == 'pool':
        if len(host_ar) == 2:
            value = host_ar[1]
        elif default_pool_name is True:
            value = '_pool0'

    return value
