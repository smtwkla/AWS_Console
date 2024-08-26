from enum import Enum, StrEnum


class ActionsOnInstances(StrEnum):
    START = "S"
    SHUTDOWN = "H"
    TERMINATE = "T"


class InstanceStates(Enum):
    PENDING = 0
    RUNNING = 16
    STOPPED = 80
    STOPPING = 64
    SHUTTING_DOWN = 32
    TERMINATED = 48

ActionStrings = {"Start": ActionsOnInstances.START.value,
                 "Stop": ActionsOnInstances.SHUTDOWN.value,
                 "Terminate": ActionsOnInstances.TERMINATE.value}

class Instance:
    def __init__(self):
        self.InstanceId = None
        self.InstanceName = None
        self.InstanceType = None
        self.InstanceState = None
        self.InstanceStateCode = -1
        self.PermissionString = None
        self.ApplicableActions = ""


    def __repr__(self):
        r = f'{self.InstanceId} | {self.InstanceName} | {self.InstanceType} | {self.InstanceState}'
        return r
    
    def check_permission(self, action:ActionsOnInstances)->bool:
        return (action in self.ApplicableActions) and (action in self.PermissionString)
