from flocker.node import BackendDescription, DeployerType
from emc_xtremio_flocker_plugin.emc_xtremio_blockdevice import xio_from_configuration

def api_factory(cluster_id, **kwargs):
    return xio_from_configuration(cluster_id=cluster_id, xms_user=kwargs[u'xms_user'], xms_password=kwargs[u'xms_password'], xms_ip=kwargs['xms_ip'])

FLOCKER_BACKEND = BackendDescription(
    name=u"emc_xtremio_flocker_plugin", # name isn't actually used for 3rd party plugins
    needs_reactor=False, needs_cluster_id=True,
    api_factory=api_factory, deployer_type=DeployerType.block)
