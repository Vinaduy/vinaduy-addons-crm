from . import models


def _post_init_hook(env):
    """Archive standard CRM stages so the pipeline only shows our 7."""
    Stage = env['crm.stage']
    standard_xml_ids = ['crm.stage_lead1', 'crm.stage_lead2', 'crm.stage_lead3', 'crm.stage_lead4']
    to_archive = Stage.browse()
    for xmlid in standard_xml_ids:
        rec = env.ref(xmlid, raise_if_not_found=False)
        if rec:
            to_archive |= rec
    if to_archive:
        to_archive.write({'active': False})
