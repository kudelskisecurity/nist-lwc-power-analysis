class RunObject:
    def __init__(self, parameters, status, runtime, measurables):
        self.measurables = measurables
        self.runtime = runtime
        self.status = status
        self.parameters = parameters
