class BaseWorkflowPoller():
    def poll(self, path, sa=None):
        raise NotImplementedError('subclasses of BaseWorkflowPoller must provide a poll() method')
