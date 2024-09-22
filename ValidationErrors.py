from enum import Enum
from ColouredText import colours

### CLASSES ###
class ErrorType(Enum):
    MISSING_REQUIRED_VALUE = "MISSING REQUIRED VALUE"
    DUPLICATE = "DUPLICATE"
    UNKNOWN_NAME_REFERENCED = "UNKNOWN REFERENCE"
    INVALID_VALUE = "INVALID VALUE"



class ValidationError:
    errorType: ErrorType
    errorMessage: str
    context: str
    contextEnabled: bool = False

    ## Initialization
    def __init__(self, newErrType: ErrorType, newErrMsg: str, newContext: str):
        self.errorType = newErrType
        self.errorMessage = newErrMsg
        self.context = newContext

    def toggle_context(self):
        self.contextEnabled = not self.contextEnabled


    def __str__(self):
        contextString = ""
        if self.contextEnabled:
            contextString = f"\n{colours.BOLD}Error Context:\n{colours.ENDC}{self.context}\n"

        return f"{colours.BOLD}{colours.FAIL}[{self.errorType.value}] {colours.ENDC}{colours.FAIL}{self.errorMessage}{colours.ENDC} {contextString}"