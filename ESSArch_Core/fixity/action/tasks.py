import logging
import os
from pathlib import PurePath

from django.contrib.auth import get_user_model
from glob2 import iglob

from ESSArch_Core.auth.models import Notification
from ESSArch_Core.config.celery import app
from ESSArch_Core.fixity.models import ActionTool
from ESSArch_Core.ip.models import EventIP
from ESSArch_Core.util import in_directory

User = get_user_model()


@app.task(bind=True, event_type=50760)
def Action(self, tool, pattern, rootdir, options, purpose=None, delete_original=True):
    def _convert(path, rootdir, tool, options, delete_original=True):
        tool.run(path, rootdir, options)

        relpath = PurePath(path).relative_to(rootdir).as_posix()
        EventIP.objects.create(
            eventType_id=50750,
            eventOutcome=EventIP.SUCCESS,
            eventOutcomeDetailNote='Converted {}'.format(relpath),
            linkingObjectIdentifierValue=str(self.get_information_package().pk),
            linkingAgentIdentifierValue=User.objects.get(pk=self.responsible)
        )

        if delete_original:
            os.remove(path)

    ip = self.get_information_package()
    tool = ActionTool.objects.get(name=tool)

    msg = '{type} job started, purpose: {purpose}'.format(
        type=tool.type.capitalize(),
        purpose=purpose
    )
    self.create_success_event(msg)

    if tool.file_processing:
        for path in iglob(rootdir + '/' + pattern, case_sensitive=False):
            if not in_directory(path, rootdir):
                raise ValueError('Invalid file-pattern accessing files outside of package')

            if os.path.isdir(path):
                for root, _dirs, files in os.walk(path):
                    for f in files:
                        fpath = os.path.join(root, f)
                        _convert(fpath, rootdir, tool, options)
            else:
                _convert(path, rootdir, tool, options)
    else:
        filepath = os.path.join(rootdir, pattern)
        tool.run(filepath, rootdir, options)

    Notification.objects.create(
        message='{type} job done for "{ip}"'.format(
            type=tool.type.capitalize(),
            ip=ip.object_identifier_value
        ),
        level=logging.INFO,
        user_id=self.responsible,
        refresh=True
    )

    msg = '{type} job done, purpose: {purpose}'.format(
        type=tool.type.capitalize(),
        purpose=purpose
    )
    self.create_success_event(msg)
