import json
from enum import Enum
from ColouredText import colours
from ValidationErrors import *
from Interfaces import *
import DataValidation


class ForeignKey(IMigratable):
    localRef: u'Column'
    tableRef: u'Table'
    externalRef: u'Column'
    localName: str
    externalName: str
    tableName: str
    onDelete: str
    onUpdate: str

    ## Initialization Functions
    def __init__(self, newLocalName: str, newTableName: str, newExternalName: str, newOnDelete: str, newOnUpdate: str):
        self.localRef = None
        self.tableRef = None
        self.externalRef = None
        self.localName = newLocalName
        self.externalName = newExternalName
        self.tableName = newTableName
        self.onDelete = newOnDelete
        self.onUpdate = newOnUpdate


    def from_dict(dictionary: dict):

        if dictionary == None:
            return None
        
        localName = dictionary.get("local_name", None)
        tableName = dictionary.get("table_name", None)
        externalName = dictionary.get("foreign_name", None)
        
        return ForeignKey(localName, tableName, externalName,
                          dictionary.get("on_delete", None),
                          dictionary.get("on_update", None))
    

    def to_dict(self):
        returnDict = {}
        if self.localName != None: returnDict["local_name"] = self.localName
        if self.tableName != None: returnDict["table_name"] = self.tableName
        if self.externalName != None: returnDict["foreign_name"] = self.externalName
        if self.onDelete != None: returnDict["on_delete"] = self.onDelete
        if self.onUpdate != None: returnDict["on_update"] = self.onUpdate

        return returnDict


    def copy(self) -> u'ForeignKey':
        copiedFKey = ForeignKey(self.localName, self.tableName, self.externalName, self.onDelete, self.onUpdate)
        return copiedFKey
    

    def setup_references(self, ownTable: u'Table', allTables: list[u'Table']):

        # Extracts references to structures by their names
        for col in ownTable.columns:
            if col.name == self.localName:
                self.localRef = col
                break
            
        table = None
        for currTable in allTables:
            if currTable.name == self.tableName:
                table = currTable
                self.tableRef = currTable
                break

        if table != None:
            for external in table.columns:
                if external.name == self.externalName:
                    self.externalRef = external
                    break


    ## Usage Functions
    def get_key(self) -> str:
        return (f"{self.localName}->{self.tableName}.{self.externalName}")


    def compare_contents(self, other: u'ForeignKey') -> bool:
        return (self.onDelete == other.onDelete
                and self.onUpdate == other.onUpdate)


    def validate_self(self, tableUsed: u'Table') -> list[ValidationError]:
        errors = []

        # Validates that all values are present
        if self.localName == None or len(self.localName) == 0:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          "Foreign Key is missing a local column name!", 
                                          tableUsed.str_with_line_indicated(foreignKey=self)))
            
        if self.tableName == None or len(self.tableName) == 0:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          "Foreign Key is missing a foreign table name!", 
                                          tableUsed.str_with_line_indicated(foreignKey=self)))
            
        if self.externalName == None or len(self.externalName) == 0:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          "Foreign Key is missing a foreign column name!", 
                                          tableUsed.str_with_line_indicated(foreignKey=self)))
        
        # Validates constraint validity
        if self.onUpdate != None and not DataValidation.validate_fkey_constraint(self.onUpdate):
            errors.append(ValidationError(ErrorType.INVALID_VALUE, 
                                                f"OnUpdate is invalid: '{self.onUpdate}'!", 
                                                tableUsed.str_with_line_indicated(foreignKey=self)))
        
        if self.onDelete != None and not DataValidation.validate_fkey_constraint(self.onDelete):
            errors.append(ValidationError(ErrorType.INVALID_VALUE, 
                                                f"OnDelete is invalid: '{self.onDelete}'!", 
                                                tableUsed.str_with_line_indicated(foreignKey=self)))
            
        # Validates that all values reference valid locations
        if self.localRef == None:
            errors.append(ValidationError(ErrorType.UNKNOWN_NAME_REFERENCED, 
                                          "Foreign Key is referencing a nonexistent local column!", 
                                          tableUsed.str_with_line_indicated(foreignKey=self)))
            
        if self.tableRef == None:
            errors.append(ValidationError(ErrorType.UNKNOWN_NAME_REFERENCED, 
                                          "Foreign Key is referencing a nonexistent table!", 
                                          tableUsed.str_with_line_indicated(foreignKey=self)))
        
        if self.externalRef == None:
            errors.append(ValidationError(ErrorType.UNKNOWN_NAME_REFERENCED, 
                                          "Foreign Key is referencing a nonexistent column in the foreign table!", 
                                          tableUsed.str_with_line_indicated(foreignKey=self)))
        
        return errors
    
    ## Base Functions
    def __str__(self):
        return f"{self.get_key()} Update: {self.onUpdate} Delete: {self.onDelete}"



class Column(IMigratable):
    name: str
    datatype: str
    constraints: list[str]


    ## Initialization/Serialization Functions
    def __init__(self, 
                 newName: str, 
                 newType: str, 
                 newConstraints: list[str], 
                 ):
        
        self.name = newName
        self.datatype = newType
        self.constraints = newConstraints
        

    def from_dict(dictionary: dict):
        if dictionary == None:
            return None
        
        return Column(dictionary.get("name", None), 
                           dictionary.get("type", None), 
                           dictionary.get("constraints", []))
    

    def to_dict(self):

        returnDict = {}
        if self.name != None: returnDict["name"] = self.name
        if self.datatype != None: returnDict["type"] = self.datatype
        if self.constraints != None: returnDict["constraints"] = self.constraints
        return returnDict


    def copy(self) -> u'Column':
        return Column(self.name, self.datatype, self.constraints.copy() if self.constraints != None else None)


    ## Usage Functions
    def validate_self(self, tableUsed: u'Table') -> list[ValidationError]:
        errors = []

        # Validates for having values in most fields
        if self.name == None or len(self.name) == 0:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          "Column is missing a name!", 
                                          tableUsed.str_with_line_indicated(column=self)))
        
        if self.datatype == None or len(self.datatype) == 0:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          "Column is missing a datatype!", 
                                          tableUsed.str_with_line_indicated(column=self)))

        if self.datatype != None and not DataValidation.validate_datatype(self.datatype):
            errors.append(ValidationError(ErrorType.INVALID_VALUE, 
                                          f"Datatype is invalid: '{self.datatype}'!", 
                                          tableUsed.str_with_line_indicated(column=self)))
            
        # Validates constraints - duplication and validity
        if self.constraints != None:
            for constraint in self.constraints:
                if self.constraints.count(constraint) > 1:
                    errors.append(ValidationError(ErrorType.DUPLICATE,
                                                  f"Duplicate constraint: '{constraint}'",
                                                  tableUsed.str_with_line_indicated(column=self)))
                    
                if not DataValidation.validate_constraint(constraint):
                    errors.append(ValidationError(ErrorType.INVALID_VALUE, 
                                                f"Constraint is invalid: '{constraint}'!", 
                                                tableUsed.str_with_line_indicated(column=self)))
         
        return errors


    def compare_contents(self, other: u'Column') -> bool:

        # Returns False early if anything fails, otherwise defaults to True
        if self.datatype != other.datatype: return False
        if self.constraints != other.constraints: return False

        return True
    
    def get_key(self) -> str:
        return self.name



    ## Base Functions
    def __str__(self):
        return f"{self.name} {self.datatype} {str(self.constraints)}"



class Table(IMigratable):
    name: str
    columns: list[Column]
    foreignKeys: list[ForeignKey]

    ## Initialization Functions
    def __init__(self, newName: str, newColumns: list[Column], newForeignKeys: list[ForeignKey]):
        self.name = newName
        self.columns = newColumns
        self.foreignKeys = newForeignKeys


    def from_dict(dictionary: dict):
        if dictionary == None:
            return None
        
        return Table(dictionary.get("name", None), 
                     [Column.from_dict(item) for item in dictionary.get("columns", [])],
                     [ForeignKey.from_dict(item) for item in dictionary.get("foreign_keys", [])])
    
    def to_dict(self):
        returnDict = {}

        returnDict["name"] = self.name
        returnDict["columns"] = [col.to_dict() for col in self.columns]
        returnDict["foreign_keys"] = [fKey.to_dict() for fKey in self.foreignKeys]

        return returnDict


    def setup_foreign_key_refs(self, allTables: list[u'Table']):
        
        if self.foreignKeys != None:
            for fKey in self.foreignKeys:
                fKey.setup_references(self, allTables)


    ## Usage Functions
    def validate_self(self) -> list[ValidationError]:
        errors = []

        # Validates self
        if self.name == None:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          f"Table is missing a name!", 
                                          self.str_with_line_indicated(indicateSelf=True)))
        
        if len(self.columns) == 0:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          f"Table has no columns!", 
                                          self.str_with_line_indicated(indicateSelf=True)))
        
        # Validates each column and checks for name duplication
        for col in self.columns:
            if [otherCol.name for otherCol in self.columns].count(col.name) > 1:
                errors.append(ValidationError(ErrorType.DUPLICATE, 
                                            f"Column name '{col.name}' is used by another column!", 
                                            self.str_with_line_indicated(column=col)))
        
            errors.extend(col.validate_self(self))

        # Validates each foreign key and checks for identical ones
        for fKey in self.foreignKeys:
            for otherFKey in self.foreignKeys:
                if otherFKey != fKey and fKey.get_key() == otherFKey.get_key():
                    errors.append(ValidationError(ErrorType.DUPLICATE,
                                                "Duplicate Foreign Key!",
                                                self.str_with_line_indicated(foreignKey=fKey)))

            errors.extend(fKey.validate_self(self))

        return errors
    

    def compare_table_members(ownMembers: list[IMigratable], otherMembers: list[IMigratable]) -> bool:

        # Short-circuit return if lists are differing lengths
        if len(ownMembers) != len(otherMembers): return False

        # Creates sorted arrays to search through. We will compare each index against the
        # same index.
        # We use the get_key() function to order them, as it should always place them in the same order.

        own: list[ForeignKey] = ownMembers.copy()
        own.sort(key=lambda item: item.get_key())

        other: list[ForeignKey] = otherMembers.copy()
        other.sort(key=lambda item: item.get_key())

        for i in range(len(own)):
            if not own[i].compare_equivalence(other[i]): return False

        return True


    def compare_contents(self, other: u'Table') -> bool:
        return (Table.compare_table_members(self.columns, other.columns) 
                and Table.compare_table_members(self.foreignKeys, other.foreignKeys))
    

    def get_key(self) -> str:
        return self.name
        

    def add_column(self, newCol: Column):
        self.columns.append(newCol)


    def add_foreign_key(self, newFKey: ForeignKey):
        self.foreignKeys.append(newFKey)


    def remove_column(self, colToRemove: Column):
        self.columns.remove(colToRemove)

    
    def remove_foreign_key(self, fKeyToRemove: ForeignKey):
        self.foreignKeys.remove(fKeyToRemove)

    
    def copy(self) -> u'Table':

        copiedColumns = [col.copy() for col in self.columns] if self.columns != None else []
        copiedFKeys = [fKey.copy() for fKey in self.foreignKeys] if self.foreignKeys != None else []
        return Table(self.name, copiedColumns, copiedFKeys)
    

    ## Display Functions
    def __str__(self):
        output = f"TABLE {self.name}\n"
        for col in self.columns:
            output += f"\t{str(col)}\n"

        for fKey in self.foreignKeys:
            output += f"\t{str(fKey)}\n"

        return output
    

    def str_with_line_indicated(self, column: Column = None, foreignKey: ForeignKey = None, indicateSelf: bool = False):

        indicatorLine = f"{colours.WARNING}^^^^^^^^^^^\n{colours.ENDC}"
        output = f"TABLE {self.name}\n"

        if indicateSelf:
            output += indicatorLine

        for col in self.columns:
            output += f"\t{str(col)}\n"

            if col == column:
                output += f"\t{indicatorLine}"

        for fKey in self.foreignKeys:
            output += f"\t{str(fKey)}\n"

            if fKey == foreignKey:
                output += f"\t{indicatorLine}"

        return output



class DatabaseSchema:
    tables: list[Table]

    ## Initialization and Serialization
    def __init__(self, newTables: list[Table]):
        self.tables = newTables


    def from_json(jsonString: str):

        # Loads a given JSON string into a new database schema, by loading each table
        # and assigning each an index according to its position in the JSON.
        jsonDict: dict = json.loads(jsonString)
        jsonTables = jsonDict.get("tables", [])

        tables: list[Table] = [Table.from_dict(jsonTable) for jsonTable in jsonTables]

        # After creating the tables, sets up foreign key refs
        for table in tables:
            table.setup_foreign_key_refs(tables)
        
        # Creates and returns a schema
        return DatabaseSchema(tables)

    
    def to_dict(self):
        return {
            "tables": [table.to_dict() for table in self.tables]
        }
    

    ## Usage Functions
    def validate_self(self) -> list[ValidationError]:
        errors = []

        # Validates self
        if self.tables == None or len(self.tables) == 0:
            errors.append(ValidationError(ErrorType.MISSING_REQUIRED_VALUE, 
                                          "There are no tables in the database!", 
                                          ""))

        # Checks for duplicate table names and validates each table
        for table in self.tables:
            if [otherTable.name for otherTable in self.tables].count(table.name) > 1:
                errors.append(ValidationError(ErrorType.DUPLICATE, 
                                              f"Table name '{table.name}' is used by another table!", 
                                              table.str_with_line_indicated(indicateSelf=True)))

            errors.extend(table.validate_self())

        return errors


    def add_table(self, newTable: Table):
        self.tables.append(newTable)


    def remove_table(self, table: Table):
        self.tables.remove(table)


    def compare_equivalence(self, other: u'DatabaseSchema'):
        if len(self.tables) != len(other.tables):
            return False
        
        ownTables = self.tables.copy()
        otherTables = other.tables.copy()

        ownTables.sort(key=lambda item: item.get_key())
        otherTables.sort(key=lambda item: item.get_key())

        for i in range(len(self.tables)):
            if not ownTables[i].compare_equivalence(otherTables[i]):
                return False
            
        return True


    ## Base Functions
    def __str__(self):
        output = ""
        for table in self.tables:
            output += f"{str(table)}\n"
        
        return output



