

class Instance:
    def __init__(self):
        self.InstanceId = None
        self.InstanceName = None
        self.InstanceType = None
        self.InstanceState = None
        self.InstanceStateCode = 0

    def __repr__(self):
        r = f'{self.InstanceId} | {self.InstanceName} | {self.InstanceType} | {self.InstanceState}'
        return r
