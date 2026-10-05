class InvalidIdentifierError(ValueError):
    def __init__(self, message, field="identifier"):
        super().__init__(message)
        self.field = field


class InvalidRecordError(ValueError):
     def __init__(self, message, field="row"):
        super().__init__(message)
        self.field = field
