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
def Action(self, tool, pattern, rootdir, options, purpose=None):
    """
    Action task.

    attr:
        tool: Name of tool. Example 'Convert filformat'
        pattern: get value from inputform "key": "path". example: '**/*.*'
        rootdir: get value automatic from ip rootdir. example: /ESSArch/data/preingest/packages/ip1
        options: get dict with all keys and values from inputform. example: {'key1': 'xx', 'key2': 'yy',
                                                                             'path': '**/*.*'}
        purpose: get value from inputform purpose (not included in options)
    """
    logger = logging.getLogger('essarch')
    logger.debug('Action task - tool: {}, pattern: {}, rootdir: {}, options: {}, purpose: {}'.format(
        repr(tool), repr(pattern), repr(rootdir), repr(options), repr(purpose)))
    ip = self.get_information_package()
    tool = ActionTool.objects.get(name=tool)

    msg = '{type} job started, purpose: {purpose}'.format(
        type=tool.type.capitalize(),
        purpose=purpose
    )
    self.create_success_event(msg)

    def _run(filepath, rootdir, tool, options, t=None, ip=None):
        tool.run(filepath, rootdir, options, t, ip)

        relpath = PurePath(filepath).relative_to(rootdir).as_posix()
        EventIP.objects.create(
            eventType_id=50750,
            eventOutcome=EventIP.SUCCESS,
            eventOutcomeDetailNote='{type} {relpath}'.format(
                type=tool.type.capitalize(),
                relpath=relpath
            ),
            linkingObjectIdentifierValue=str(self.get_information_package().pk),
            linkingAgentIdentifierValue=User.objects.get(pk=self.responsible)
        )

        if tool.delete_original:
            os.remove(filepath)

    if tool.file_processing and pattern:
        for path in iglob(rootdir + '/' + pattern, case_sensitive=False, include_hidden=True):
            if not in_directory(path, rootdir):
                raise ValueError('Invalid file-pattern accessing files outside of package')

            if os.path.isdir(path):
                for root, _dirs, files in os.walk(path):
                    for f in files:
                        filepath = os.path.join(root, f)
                        _run(filepath, rootdir, tool, options, self.get_processtask(), ip)
            else:
                filepath = path
                _run(filepath, rootdir, tool, options, self.get_processtask(), ip)
    elif pattern:
        filepath = os.path.join(rootdir, pattern)
        _run(filepath, rootdir, tool, options, self.get_processtask(), ip)
    else:
        filepath = rootdir
        _run(filepath, rootdir, tool, options, self.get_processtask(), ip)

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

    return msg
