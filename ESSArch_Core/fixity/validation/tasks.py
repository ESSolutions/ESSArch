from ESSArch_Core.fixity.validation import get_backend
from ESSArch_Core.WorkflowEngine.dbtask import DBTask


class Validate(DBTask):
    def run(self, name, path, context=None, options=None):
        options = {} if options is None else options
        klass = get_backend(name)

        validator = klass(context=context, ip=self.ip, task=self.get_processtask(), options=options)
        validator.validate(path)
