from ColouredText import *


### UTILITY FUNCTIONS ###
def ask_yes_no(question: str):

    while True:
        value = input(f"{colours.WARNING}{question}{colours.ENDC}{colours.WARNING}{colours.BOLD} [Y/n]:{colours.ENDC} ")

        if value.lower() == "yes" or value.lower() == "y" or len(value) == 0:
            return True
        elif value.lower() == "no" or value.lower() == "n":
            return False
        

def ask_for_input(question: str):

    return str(input(f"{colours.WARNING}{question}{colours.ENDC}{colours.WARNING}{colours.BOLD} [Input Text]:{colours.ENDC}"))