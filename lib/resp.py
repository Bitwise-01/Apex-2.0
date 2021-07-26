class Resp:

    FAILED_CODE = 0
    SUCCESS_CODE = 1

    DEFAULT_MSG = ""
    DEFAULT_VALUE = None

    def __init__(self):
        self.__msg = Resp.DEFAULT_MSG
        self.__status = Resp.FAILED_CODE
        self.__value = Resp.DEFAULT_VALUE

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, s):
        self.__status = s

    @property
    def msg(self):
        return self.__msg

    @msg.setter
    def msg(self, m):
        self.__msg = m

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, v):
        self.__value = v

    @property
    def serialize(self):
        return {"status": self.status, "msg": self.msg, "value": self.value}
