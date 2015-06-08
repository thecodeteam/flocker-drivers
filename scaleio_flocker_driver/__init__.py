# Copyright 2015 EMC Corporation

from flocker.node import BackendDescription, DeployerType
from .emc_sio import (
    scaleio_from_configuration, DEFAULT_STORAGE_POOL,
    DEFAULT_PROTECTION_DOMAIN, DEFAULT_PORT, DEBUG
)

def api_factory(cluster_id, **kwargs):

    protection_domain = DEFAULT_PROTECTION_DOMAIN
    if "protection_domain" in kwargs:
       protection_domain = kwargs[u"protection_domain"]

    storage_pool = DEFAULT_STORAGE_POOL
    if "storage_pool" in kwargs:
       storage_pool= kwargs[u"storage_pool"]

    port = DEFAULT_PORT
    if "port" in kwargs:
       port= kwargs[u"port"]

    debug = DEBUG
    if "debug" in kwargs:
       debug = kwargs[u"debug"]

    certificate = None
    if "certificate" in kwargs:
       certificate= kwargs[u"certificate"]

    return scaleio_from_configuration(cluster_id=cluster_id, username=kwargs[u"username"],
                        password=kwargs[u"password"], mdm_ip=kwargs[u"mdm"], port=port,
                        protection_domain=protection_domain, storage_pool=storage_pool,
                        certificate=certificate, ssl=kwargs[u"ssl"], debug=debug)

FLOCKER_BACKEND = BackendDescription(
    name=u"scaleio_flocker_driver",
    needs_reactor=False, needs_cluster_id=True,
    api_factory=api_factory, deployer_type=DeployerType.block)
