class BaseWorkflowPoller():
    def poll(self, path, sa=None):
        raise NotImplementedError('subclasses of BaseWorkflowPoller must provide a poll() method')

    def delete_source(self, path, ip):
        pass
