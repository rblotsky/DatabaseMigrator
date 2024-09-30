from Schema import *
from ColouredText import *


### CONSTANTS ###
MIGRATIONS_TABLE = Table("MIGRATIONS_TRACKING_AUTOGEN", 
                         [Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT", "DEFAULT 0"]),
                          Column("Version", "VARCHAR(255)", ["NOT NULL"]),
                          Column("Name", "VARCHAR(255)", ["NULL"])],
                          []
                          )



### UTILITY FUNCTIONS ###
def colour_text_if_value_changed(text: str, colour: str, value1, value2):

    if value1 != value2:
        return f"{colour}{text}{colours.ENDC}"
    else:
        return text
    


### CLASSES ###
class Migration:

    oldKey: str

    ## Checking
    def is_add(self) -> bool:
        pass

    def is_remove(self) -> bool:
        pass

    def is_edit(self) -> bool:
        return not self.is_add() and not self.is_remove()


    ## Creating
    def create_new_migration(oldObject: IMigratable, newObject: IMigratable):
        pass


    ## Running Itself
    def run_edit_on_old_object(self, oldObject: IMigratable):
        pass



class ColumnMigration(Migration):
    newColumnData: Column
    oldObjectCopy: Column


    ## Initialization and Serialization
    def __init__(self, oldKey: str, newColumnData: Column):
        self.oldKey = oldKey
        self.newColumnData = newColumnData
        self.oldObjectCopy = None

    
    def from_dict(dictionary: dict):
        return ColumnMigration(dictionary.get("old_key", None),
                               Column.from_dict(dictionary.get("new_data", None)))


    def to_dict(self):
        returnDict = {}

        if self.oldKey != None: returnDict["old_key"] = self.oldKey
        if self.newColumnData != None: returnDict["new_data"] = self.newColumnData.to_dict()
        
        return returnDict


    ## Creating Migrations
    def create_new_migration(oldObject: Column, newObject: Column) -> u'ColumnMigration':

        newColMigration = ColumnMigration(oldObject.get_key() if oldObject != None else None, 
                                          newObject.copy() if newObject != None else None)
        
        newColMigration.oldObjectCopy = oldObject.copy() if oldObject != None else None

        return newColMigration
        
    

    ## Running Migrations
    def run_edit_on_old_object(self, oldObject: Column):
        oldObject.name = self.newColumnData.name
        oldObject.datatype = self.newColumnData.datatype
        oldObject.constraints = self.newColumnData.constraints.copy()


    ## Checks
    def is_add(self):
        return self.oldKey == None or len(self.oldKey) == 0
    
    def is_remove(self):
        return self.newColumnData == None
    
    def is_edit(self):
        return not self.is_add() and not self.is_remove()


    ## Base Functions
    def __str__(self):

        # Constructs the new column display string 
        # "Removed" in RED if the new column is None, column data in GREEN if the old column is None,
        # and modified values in YELLOW if neither are None
        newColString = ""
        if self.newColumnData == None:
            newColString += f"{colours.FAIL}Removed{colours.ENDC}"
        elif self.oldObjectCopy == None:
            newColString += f"{colours.OKGREEN}{self.newColumnData.name} {self.newColumnData.datatype} {self.newColumnData.constraints}{colours.ENDC}"
        else:

            # Constructs a warning string
            warningString = ""
            if self.oldObjectCopy != None and self.oldObjectCopy.datatype != self.newColumnData.datatype:
                warningString += f"{colours.BOLD}(WARN: Confirm datatype change is valid!){colours.ENDC}"

            # Colours each of the components if they were changed
            nameString = colour_text_if_value_changed(self.newColumnData.name, 
                                                      colours.WARNING, 
                                                      self.newColumnData.name, 
                                                      self.oldObjectCopy.name)
            
            typeString = colour_text_if_value_changed(self.newColumnData.datatype, 
                                                      colours.WARNING, 
                                                      self.newColumnData.datatype, 
                                                      self.oldObjectCopy.datatype)
            
            constraintsString = colour_text_if_value_changed(self.newColumnData.constraints, 
                                                             colours.WARNING, 
                                                             self.newColumnData.constraints, 
                                                             self.oldObjectCopy.constraints)
            
            newColString = f"{nameString} {typeString} {constraintsString} {warningString}"
        
        # Returns a string with the created substrings
        return f"COLUMN {self.oldObjectCopy} --> {newColString}"


class FKeyMigration(Migration):
    newFKey: ForeignKey
    oldObjectCopy: ForeignKey

    ## Initialization
    def __init__(self, oldKey: str, new: ForeignKey):
        self.oldKey = oldKey
        self.newFKey = new
        self.oldObjectCopy = None

    def from_dict(dictionary: dict):
        return FKeyMigration(dictionary.get("old_key", None),
                             ForeignKey.from_dict(dictionary.get("new_data", None)))

    def to_dict(self):
        returnDict = {}

        if self.oldKey != None: returnDict["old_key"] = self.oldKey
        if self.newFKey != None: returnDict["new_data"] = self.newFKey.to_dict()

        return returnDict


    ## Creating Migrations
    def create_new_migration(oldObject: ForeignKey, newObject: ForeignKey) -> u'FKeyMigration':
        newMigration =  FKeyMigration(oldObject.get_key() if oldObject != None else None, 
                                      newObject.copy() if newObject != None else None)
        
        newMigration.oldObjectCopy = oldObject.copy() if oldObject != None else None

        return newMigration
        

    ## Running Migrations
    def run_edit_on_old_object(self, oldObject: ForeignKey):
        oldObject.localName = self.newFKey.localName
        oldObject.tableName = self.newFKey.tableName
        oldObject.externalName = self.newFKey.externalName
        oldObject.onUpdate = self.newFKey.onUpdate
        oldObject.onDelete = self.newFKey.onDelete
    

    ## Checks
    def is_add(self):
        return self.oldKey == None
    
    def is_remove(self):
        return self.newFKey == None
        

    ## Base Functions
    def __str__(self):
        # Constructs the new column display string 
        # "Removed" in RED if the new column is None, column data in GREEN if the old column is None,
        # and modified values in YELLOW if neither are None
        newColString = ""
        if self.newFKey == None:
            newColString += f"{colours.FAIL}Removed{colours.ENDC}"
        elif self.oldObjectCopy == None:
            newColString += f"{colours.OKGREEN}{self.newFKey.get_key()} Update: {self.newFKey.onUpdate} Delete: {self.newFKey.onDelete}{colours.ENDC}"
        else:

            # Colours each of the components if they were changed
            nameString = colour_text_if_value_changed(self.newFKey.get_key(), 
                                                      colours.WARNING, 
                                                      self.newFKey.get_key(), 
                                                      self.oldObjectCopy.get_key())
            
            typeString = colour_text_if_value_changed(f"Update: {self.newFKey.onUpdate}", 
                                                      colours.WARNING, 
                                                      self.newFKey.onUpdate, 
                                                      self.oldObjectCopy.onUpdate)
            
            constraintsString = colour_text_if_value_changed(f"Delete: {self.newFKey.onDelete}", 
                                                             colours.WARNING, 
                                                             self.newFKey.onDelete, 
                                                             self.oldObjectCopy.onDelete)
            
            newColString = f"{nameString} {typeString} {constraintsString}"
        
        # Returns a string with the created substrings
        return f"FOREIGN KEY {self.oldObjectCopy} --> {newColString}"


class TableMigration(Migration):
    newName: str
    colMigrations: list[ColumnMigration]
    fKeyMigrations: list[FKeyMigration]

    
    ## Initialization and Serialization
    def __init__(self, oldKey: str, newName: str, colMigrations: list[ColumnMigration], fKeyMigrations: list[FKeyMigration]):
        self.oldKey = oldKey
        self.newName = newName
        self.colMigrations = colMigrations
        self.fKeyMigrations = fKeyMigrations


    def from_dict(dictionary: dict):
        return TableMigration(dictionary.get("old_key", None),
                              dictionary.get("new_name", None),
                              [ColumnMigration.from_dict(colDict) for colDict in dictionary.get("column_migrations", [])],
                              [FKeyMigration.from_dict(colDict) for colDict in dictionary.get("foreign_key_migrations", [])])
    

    def to_dict(self):
        returnDict = {}

        if self.oldKey != None: returnDict["old_key"] = self.oldKey
        if self.newName != None: returnDict["new_name"] = self.newName
        if self.colMigrations != None: returnDict["column_migrations"] = [col.to_dict() for col in self.colMigrations]
        if self.fKeyMigrations != None: returnDict["foreign_key_migrations"] = [fKey.to_dict() for fKey in self.fKeyMigrations]

        return returnDict


    def add_col_migrations(self, newColMigrations: list[ColumnMigration]):
        self.colMigrations.extend(newColMigrations)

    
    def add_fkey_migrations(self, newFKeyMigrations: list[FKeyMigration]):
        self.fKeyMigrations.extend(newFKeyMigrations)


    ## Creating Migrations
    def create_new_migration(oldObject: Table, newObject: Table) -> u'TableMigration':
        return TableMigration(oldObject.get_key() if oldObject != None else None,
                              newObject.get_key() if newObject != None else None,
                              [],
                              [])
    

    ## Running Self
    def run_edit_on_old_object(self, oldObject: Table):
        oldObject.name = self.newName
    

    def migrate_table(self, table: Table):

        # Performs all necessary column migrations
        # Gets a dictionary of old tables, so we have a way to reference all old tables before we modify any of them
        oldColsDict = IMigratable.create_object_dict(table.columns)

        for colMigration in self.colMigrations:

            usedColumn: Column = oldColsDict.get(colMigration.oldKey, None)
            if colMigration.is_add():
                usedColumn = colMigration.newColumnData.copy()
                table.add_column(usedColumn)

            elif colMigration.is_remove():
                table.remove_column(usedColumn)
                
            elif colMigration.is_edit():
                colMigration.run_edit_on_old_object(usedColumn)
                

        # Creates dictionary of fKeys
        oldFkeysDict = IMigratable.create_object_dict(table.foreignKeys)

        # Performs all necessary foreign key migrations
        for fKeyMigration in self.fKeyMigrations:

            usedFKey: ForeignKey = oldFkeysDict.get(fKeyMigration.oldKey, None)
            
            if fKeyMigration.is_add():
                usedFKey = fKeyMigration.newFKey.copy()
                table.add_foreign_key(usedFKey)
            
            elif fKeyMigration.is_remove():
                table.remove_foreign_key(usedFKey)

            elif fKeyMigration.is_edit():
                fKeyMigration.run_edit_on_old_object(usedFKey)


    ## Checking types of changes
    def is_add(self):
        return self.oldKey == None
    
    def is_remove(self):
        return self.newName == None
    

    ## Base Functions
    def __str__(self):
        nameText = ""

        if self.oldKey == None:
            nameText = f"{self.oldKey} --> {colours.OKGREEN}{self.newName}{colours.ENDC}"
        elif self.newName == None:
            nameText = f"{self.oldKey} --> {colours.FAIL}{self.newName}{colours.ENDC}"
        else:
            nameText = f"{self.oldKey} --> {colours.WARNING}{self.newName}{colours.ENDC}"


        output = f"TABLE {nameText}\n"

        for col in self.colMigrations:
            output += f"\t{str(col)}\n"

        for fKey in self.fKeyMigrations:
            output += f"\t{str(fKey)}\n"

        return output


class SchemaMigration:
    migrationIndex: int
    migrationName: str
    tableMigrations: list[TableMigration]

    ## Initialization and Serialization
    def __init__(self, newIndex: int, tables: list[TableMigration], newName: str = None  ):
        self.migrationIndex = newIndex
        self.tableMigrations = tables
        self.migrationName = newName


    def from_dict(dictionary: dict):
        return SchemaMigration(dictionary.get("index", -1),
                               [TableMigration.from_dict(table) for table in dictionary.get("tables", [])],
                               dictionary.get("name", None))
    

    def to_dict(self):
        returnDict = {}

        if self.migrationIndex != None: returnDict["index"] = self.migrationIndex
        if self.tableMigrations != None: returnDict["tables"] = [table.to_dict() for table in self.tableMigrations]
        if self.migrationName != None: returnDict["name"] = self.migrationName

        return returnDict    


    ## Usage
    def add_new_table_migration(self, tableMigration: TableMigration):
        self.tableMigrations.append(tableMigration)

        
    def migrate_schema(self, schema: DatabaseSchema) -> list[ValidationError]:
        
        # Gets a dictionary of old tables, so we have a way to reference all old tables before we modify any of them
        oldTablesDict = IMigratable.create_object_dict(schema.tables)

        for tableMigration in self.tableMigrations:
            
            usedTable: Table = oldTablesDict.get(tableMigration.oldKey, None)
                
            # Decides how to migrate the table
            if tableMigration.is_add():
                usedTable = Table(tableMigration.newName, [], [])
                schema.add_table(usedTable)

            elif tableMigration.is_remove():
                try:
                    schema.remove_table(usedTable)
                except Exception as e:
                    print(pad_err(f"[Err] Tried removing a nonexistent table: {tableMigration.oldKey}"))
            
            elif tableMigration.is_edit():
                tableMigration.run_edit_on_old_object(usedTable)

            # Migrates all the columns and fKeys
            if not tableMigration.is_remove():
                tableMigration.migrate_table(usedTable)

        # Reconnects all foreign keys with references
        for table in schema.tables:
            table.setup_foreign_key_refs(schema.tables)

        # Validates the newly migrated database
        schemaErrors = schema.validate_self()
        return schemaErrors
    

    ## Base Functions
    def __str__(self):
        output = f"MIGRATION #{self.migrationIndex}:\n"
        
        for tableMigration in self.tableMigrations:
            output += f"{str(tableMigration)}\n"

        return output