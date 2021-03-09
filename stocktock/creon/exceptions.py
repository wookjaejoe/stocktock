class CreonError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class CreonRequestError(CreonError):
    @classmethod
    def check(cls, component):
        if component.GetDibStatus() != 0:
            raise CreonRequestError(component.GetDibMsg1())
