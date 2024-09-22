from ColouredText import *


### CLASSES ###
class Command:
    name: str
    desc: str
    usageFunc = None
    arguments: list[str]


    def __init__(self, name: str, desc: str, usageFunc, arguments: list[str]):
        self.name = name
        self.desc = desc
        self.usageFunc = usageFunc
        self.arguments = arguments


    def try_call(self, *args):
        if len(args) != len(self.arguments):
            print(pad_err(f"Expected {len(self.arguments)} arguments for command '{self.name}', got {len(args)}."))
            print(pad_err(self.get_pretty_description()))
            return False
        else:
            self.usageFunc(*args)
            return True
        

    def get_pretty_description(self):
        outputText = f"> {self.name} --- {self.desc}"
        
        if len(self.arguments) != 0:
            outputText += f"\nArguments:"
            for arg in self.arguments:
                outputText += f"\n\t{arg}"

        return outputText + f"\n\n"

    
    def __str__(self):
        commandText = f"Command '{self.name}': {self.desc} - Arguments: {self.arguments}"
        return commandText
        
    
### MODULE FUNCTIONS ###
def assemble_command_dict(commands: list[u'Command']) -> dict:
    newDict = {}

    for command in commands:
        newDict[command.name] = command

    return newDict
    

def try_call_command(commands: list[u'Command'], name: str, *args):

    # Gets a dictionary to more easily find commands
    commandDict: dict = assemble_command_dict(commands)

    # Gets the command to run, tries running it.
    commandToCall: Command = commandDict.get(name, None)

    if commandToCall != None:
        commandToCall.try_call(*args)
    else:
        print(pad_err("Unknown command name!"))


def get_command_list_text(commands: list[u'Command']) -> str:
    outputText = ""
    for command in commands:
        outputText += command.get_pretty_description()

    return outputText