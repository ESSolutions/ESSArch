import logging
import os
import shutil
import uuid
from zipfile import ZipFile

from django.template.loader import render_to_string

from ESSArch_Core.essxml.util import parse_mets
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.util import stable_path
from ESSArch_Core.WorkflowEngine.polling.backends.base import (
    BaseWorkflowPoller,
)

logger = logging.getLogger('essarch.workflow.polling.XWorkflowPoller')


class TreservaWorkflowPoller(BaseWorkflowPoller):
    def poll(self, path, sa=None):
        for entry in os.listdir(path):
            subpath = os.path.join(path, entry)

            if subpath.endswith('.xml'):
                continue
            if '.DS' in subpath:
                continue
            if not stable_path(subpath):
                continue
            SIZE = os.path.getsize(subpath)
            MD5 = calculate_checksum(subpath, 'MD5')
            with ZipFile(subpath) as sipzip:
                with sipzip.open('sip.xml') as sipfile:
                    sip_mets = parse_mets(sipfile)
                    agents = (sip_mets['agents'])
                    if sip_mets['altrecordids']['SUBMISSIONAGREEMENT'][0]:
                        SA_name = sip_mets['altrecordids']['SUBMISSIONAGREEMENT'][0]

                    elif sip_mets['altrecordids']['DELIVERYSPECIFICATION'][0]:
                        SA_name = sip_mets['altrecordids']['DELIVERYSPECIFICATION'][0]

                    else:
                        raise

                    OBJID = entry.split(".")[0]
                    SA = SubmissionAgreement.objects.get(name=SA_name)
                    template = 'treserva_sd.xml'
                    render = render_to_string(template, {"SA": SA.id, "LABEL": sip_mets['LABEL'],
                                                         "ID": str(uuid.uuid4()), "OBJID": OBJID,
                                                         "FILE": entry, "FILE_ID": str(uuid.uuid4()),
                                                         "FILE_GRP_ID": str(uuid.uuid4()),
                                                         "FILE_SEC_ID": str(uuid.uuid4()),
                                                         "SIZE": SIZE, "MD5": MD5,
                                                         "ARCHIVIST_SOFTWARE": agents['ARCHIVIST_SOFTWARE']['name'],
                                                         "ARCHIVIST_SOFTWARE_VERSION":
                                                             agents['ARCHIVIST_SOFTWARE']['notes'][0],
                                                         "ARCHIVIST_ORGANIZATION": agents['ARCHIVIST_ORGANIZATION'][
                                                             'name'],
                                                         "ARCHIVIST_ORGANIZATION_NOTE":
                                                             agents['ARCHIVIST_ORGANIZATION']['notes'][0],
                                                         "CREATOR_ORGANIZATION": agents['CREATOR_ORGANIZATION'][
                                                             'name'],
                                                         "CREATOR_ORGANIZATION_NOTE":
                                                             agents['CREATOR_ORGANIZATION']['notes'][0],

                                                         })
                    with open(os.path.join(path, f'{OBJID}.xml'), 'w') as sdfile:
                        sdfile.write(render)

                    shutil.move(subpath, os.path.join('/ESSArch/data/ingest/reception', entry))

                    shutil.move(os.path.join(path, f'{OBJID}.xml'),
                                os.path.join('/ESSArch/data/ingest/reception', f'{OBJID}.xml'))

            if os.path.isfile(subpath):
                continue

        return []
