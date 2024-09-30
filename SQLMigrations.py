from Migrations import *
from Schema import *


### CONSTANTS ###
OLD_TABLE_PREFIX = "PRE_MIGRATION_TABLE_"
NEW_TABLE_PREFIX = "NEW_CREATED_TABLE_"



### CLASSES ###
class SQLMigration:
    migrationIndex: int
    migrationName: str
    sqlStatements: list[str]


    def __init__(self, index, sql, name=None):
        self.migrationIndex = index
        self.sqlStatements = sql
        self.migrationName = name


    def __str__(self):

        outputText = ""
        if self.migrationName == None:
            outputText = f"SQL Migration #{self.migrationIndex}:"
        else:
            outputText = f"SQL Migration #{self.migrationIndex} ('{self.migrationName}'):"

        for sql in self.sqlStatements:
            outputText += f"\n{sql}"

        outputText += "\n"
        return outputText



### FUNCTIONS ###
def assemble_table_from_migration(oldTable: Table, migration: TableMigration) -> Table:
    
    # Doesn't assemble anything if it's a remove migration
    if migration.is_remove():
        return None
    
    # Makes a copy of the old table, then migrates it using the migration
    newTable = oldTable.copy() if oldTable != None else Table(migration.newName, [], [])
    migration.run_edit_on_old_object(newTable)
    migration.migrate_table(newTable)
    
    # Returns the created table
    return newTable


def write_sql_create_table(table: Table) -> str:
    contentsText = ""

    # Inserts the columns - they start without a comma, and end without one
    for i in range(len(table.columns)):
        
        colData = table.columns[i]

        colText = f"\n\t{colData.name} {colData.datatype}"

        if colData.constraints != None:
            for constraint in colData.constraints:
                colText += f" {constraint}"
        
        # Adds a comma at the start if it's not the first element
        if i != 0:
            colText = "," + colText

        contentsText += colText

    # Inserts the foreign keys - they start with a comma, and end without one
    for i in range(len(table.foreignKeys)):
        
        fKeyData = table.foreignKeys[i]

        fKeyText = f",\n\tFOREIGN KEY ({fKeyData.localName}) REFERENCES {fKeyData.tableName}({fKeyData.externalName})"
        
        if fKeyData.onUpdate != None and len(fKeyData.onUpdate) != 0:
            fKeyText += f" ON UPDATE {fKeyData.onUpdate}"

        if fKeyData.onDelete != None and len(fKeyData.onDelete) != 0:
            fKeyText += f" ON DELETE {fKeyData.onDelete}"

        contentsText += fKeyText

    return f"CREATE TABLE {table.name} ({contentsText});"


def write_sql_remove_table(oldName: str) -> str:
    return f"DROP TABLE {oldName};"


def write_sql_rename_table(oldName: str, newName: str) -> str:
    return f"ALTER TABLE {oldName} RENAME TO {newName};"

def get_transferrable_columns_for_complex_migration(oldTable: Table, colMigrations: list[ColumnMigration]) -> list[tuple]:

    # Transferrable columns are any EDITED or UNCHANGED columns. 

    # First, we find the EDITED columns in the table migration and track them. Also
    # track all migrations' old keys to help find unchanged columns after.
    editMigrations: list[ColumnMigration] = []
    keyedColMigrations = {}

    for colMigration in colMigrations:
        if colMigration.is_edit():
            editMigrations.append(colMigration)
        
        keyedColMigrations[colMigration.oldKey] = colMigration

    # Now, we get all unchanged columns (those whose key isn't present in the migrations dict)
    unchangedColumns: list[Column] = []

    for col in oldTable.columns:
        if col.get_key() not in keyedColMigrations:
            unchangedColumns.append(col)

    # Assemble a list of tuples with their old and new names
    transferrableColumns = []
    for editMigration in editMigrations:
        transferrableColumns.append((editMigration.oldKey, editMigration.newColumnData.name))

    for unchangedColumn in unchangedColumns:
        transferrableColumns.append((unchangedColumn.name, unchangedColumn.name))

    # Returns what we found
    return transferrableColumns


def create_sql_for_complex_migration(oldTable: Table, tableMigration: TableMigration) -> list[str]:
    # NOTE: The order of operations is important here. Do not move things around without reason.
    # This is because renaming the old table will break foreign key references to it.
    # (by renaming it, all foreign keys are also renamed - when we then delete it, there are no longer
    # foreign keys referencing the new table)

    # 1. Create the new table with a name prefix
    # 2. Copy all maintained columns from the old table
    # 3. Drop the old table
    # 4. Rename the new table 

    # Creates the new table with a prefix
    sqlCommands = []
    newTable = assemble_table_from_migration(oldTable, tableMigration)
    newTable.name = NEW_TABLE_PREFIX + newTable.name
    sqlCommands.append(write_sql_create_table(newTable))

    # Gets all columns that can be copied into the new table, and creates an INSERT INTO
    # SQL statement to perform the copy
    transferrableColumns = get_transferrable_columns_for_complex_migration(oldTable, tableMigration.colMigrations)
    
    # Skips the insert statement if there are no transferrable columns
    if len(transferrableColumns) > 0:

        insertColumns = ""
        selectColumns = ""

        for i in range(len(transferrableColumns)):
            
            oldName = transferrableColumns[i][0]
            newName = transferrableColumns[i][1]
            if i != 0:
                oldName = "," + oldName
                newName = "," + newName

            insertColumns += newName
            selectColumns += oldName

        insertStatement = f"INSERT INTO {newTable.name} ({insertColumns}) SELECT {selectColumns} FROM {oldTable.name};"
        sqlCommands.append(insertStatement)

    # Drops the old table
    sqlCommands.append(write_sql_remove_table(oldTable.name))

    # Renames the new table
    # NOTE: This seems like its using the wrong order but it's right - we're 
    # renaming the new, prefixed table, to the old, properly named table
    sqlCommands.append(write_sql_rename_table(newTable.name, oldTable.name)) 

    return sqlCommands


def group_table_migrations(migration: SchemaMigration) -> tuple:
    addMigrations: list[TableMigration] = []
    removeMigrations: list[TableMigration] = []
    pureRenameMigrations: list[TableMigration] = []
    complexMigrations: list[TableMigration] = []

    # Goes through each table migration and assigns it to a type
    for tableMigration in migration.tableMigrations:
        if tableMigration.is_add():
            addMigrations.append(tableMigration)
        elif tableMigration.is_remove():
            removeMigrations.append(tableMigration)
        elif tableMigration.is_edit():
            if len(tableMigration.colMigrations) == 0:
                pureRenameMigrations.append(tableMigration)
            else:
                complexMigrations.append(tableMigration)

    # Returns a tuple of the lists
    return (addMigrations, removeMigrations, pureRenameMigrations, complexMigrations)


def create_sql_for_schema_migration(migration: SchemaMigration, oldSchema: DatabaseSchema) -> SQLMigration:

    # Splits migrations into groups
    groupedMigrations: tuple = group_table_migrations(migration)
    addMigrations: list[TableMigration] = groupedMigrations[0]
    removeMigrations: list[TableMigration] = groupedMigrations[1]
    pureRenameMigrations: list[TableMigration] = groupedMigrations[2]
    complexMigrations: list[TableMigration] = groupedMigrations[3]

    # Prepares by creating lists for output and dictionaries for faster
    # accessing
    sqlMigrations: list[str] = []
    oldTablesDict = Table.create_object_dict(oldSchema.tables)
        
    # NOTE: DO NOT change the order of the following operations. They must happen in this order
    # to avoid name conflicts at any stage of the migration.

    # 1. Goes through PURE RENAME migrations, creates SQL to add prefixes to their old names
    # This is to prevent name conflicts if a renamed or new table references a name previous used by 
    # a table that gets renamed later.
    for tableMigration in pureRenameMigrations:
        sqlMigrations.append(write_sql_rename_table(tableMigration.oldKey, OLD_TABLE_PREFIX+tableMigration.oldKey))

    # 2. Goes through REMOVE migrations, adds SQL to remove them
    for tableMigration in removeMigrations:
        sqlMigrations.append(write_sql_remove_table(tableMigration.oldKey))

    # 3. Goes through PURE RENAME migrations, adds SQL to rename them
    for tableMigration in pureRenameMigrations:
        sqlMigrations.append(write_sql_rename_table(OLD_TABLE_PREFIX+tableMigration.oldKey, tableMigration.newName))

    # 4. Goes through COMPLEX migrations, extends migrations with extra migrations for them
    for tableMigration in complexMigrations:
        sqlMigrations.extend(create_sql_for_complex_migration(oldTablesDict[tableMigration.oldKey], tableMigration))
    
    # 5. Goes through ADD migrations, adds SQL to create them - this must happen at the end so all
    # renames and complex migrations can happen first
    for tableMigration in addMigrations:
        sqlMigrations.append(write_sql_create_table(assemble_table_from_migration(None, tableMigration)))

    return SQLMigration(migration.migrationIndex, sqlMigrations, migration.migrationName)
            


        
    




