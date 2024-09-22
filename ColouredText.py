from enum import Enum

class colours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def pad_err(content: str) -> str:
    return colours.FAIL + content + colours.ENDC

def pad_ok(content: str) -> str:
    return colours.OKCYAN + content + colours.ENDC

def pad_success(content: str) -> str:
    return colours.BOLD + colours.OKGREEN + content + colours.ENDC

def pad_pass(content: str) -> str:
    return colours.OKGREEN + content + colours.ENDC

def pad_warning(content: str) -> str:
    return colours.WARNING + content + colours.ENDC

def pad_header(content: str) -> str:
    return colours.BOLD + colours.HEADER + content + colours.ENDC