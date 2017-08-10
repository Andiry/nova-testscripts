
class JackalException(Exception):
    pass
            
class TimeoutException(JackalException):
    pass

class ResetFailedException(JackalException):
    pass

class CantRebootToNovaException(JackalException):
    pass

