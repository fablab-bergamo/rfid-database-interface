class DatabaseException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class DuplicatedIdException(DatabaseException):
    def __init__(self, entity: str, entity_id: int):
        message = f"Id {entity_id} already defined for entity {entity}"
        super().__init__(message)


class InvalidIdException(DatabaseException):
    def __init__(self, entity: str, entity_id: str):
        message = f"Id {entity_id} invalid for entity {entity}"
        super().__init__(message)


class InvalidQueryException(DatabaseException):
    def __init__(self, entity: str, value: str):
        message = f"Invalid value for {value} while querying for entity {entity}"
        super().__init__(message)
