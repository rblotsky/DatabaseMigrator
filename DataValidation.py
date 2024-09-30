import re


### CONSTANTS ###
VALID_DATATYPES = {
    r".*INT": "INTEGER",
    r"CHARACTER(\(\d+\))?": "TEXT",
    r"VARCHAR(\(\d+\))?": "TEXT",
    r"VARYING": "TEXT",
    r"NCHAR(\(\d+\))?": "TEXT",
    r"NATIVE CHARACTER(\(\d+\))?": "TEXT",
    r"NVARCHAR(\(\d+\))?": "TEXT",
    r"TEXT": "TEXT",
    r"CLOB": "TEXT",
    r"BLOB": "BLOB",
    r"REAL": "REAL",
    r"DOUBLE": "REAL",
    r"DOUBLE PRECISION": "REAL",
    r"FLOAT": "REAL",
    r"NUMERIC": "NUMERIC",
    r"DECIMAL(\(\d+,\d+\))?": "NUMERIC",
    r"BOOLEAN": "NUMERIC",
    r"DATE": "NUMERIC",
    r"DATETIME": "NUMERIC",
}


VALID_CONSTRAINTS = [
    r"PRIMARY KEY(\s+.*)?",
    r"(?:NOT)?\s*NULL",
    r"DEFAULT\s+.*",
    r"UNIQUE",
    r"CHECK\s+.*",
    r"COLLATE(\s+.*)?",
    r"GENERATED ALWAYS AS\s+.*"
]

VALID_FKEY_CONSTRAINTS = [
    r"SET\s+(NULL|DEFAULT)",
    r"CASCADE",
    r"RESTRICT",
    r"NO\s+ACTION"
]


### FUNCTIONS ###
def validate_datatype(datatype: str) -> bool:
    for validType in VALID_DATATYPES.keys():
        if re.match(validType, datatype.upper()): return True

    return False


def validate_constraint(constraint: str) -> bool:
    for validConstraint in VALID_CONSTRAINTS:
        if re.match(validConstraint, constraint.upper()): return True
        
    return False


def validate_fkey_constraint(constraint: str) -> bool:
    for validConstraint in VALID_FKEY_CONSTRAINTS:
        if re.match(validConstraint, constraint.upper()): return True

    return False


def validate_datatype_cast(type1: str, type2: str) -> bool:
    # TODO
    return False