import sys
import re
import os
from ColouredText import *
from Schema import *
from Migrations import *
from ValidationErrors import *
from UserIO import *
import test.Tests as Tests
import CreateMigration
import Commands
import SQLMigrations
import pprint

### CONSTANTS ###
MIGRATIONS_FILE_REGEX = r'Migration_([1-9][0-9]*|0)\.json'
MIGRATIONS_SQL_FILE_REGEX = r'SQLMigration_([1-9][0-9]*|0)\.json'
SQL_MIGRATIONS_COMBINED_FILE = "SQLMigration_Combined.json"
DEBUG_ON = False


### UTILITY ###
def print_debug(content: str):
    if(DEBUG_ON):
        print(colours.BOLD, colours.WARNING, "[DEBUG]", colours.ENDC, colours.BOLD, " ", content, colours.ENDC, sep="")


def print_errors(errors: list[ValidationError], context: bool):
    for err in errors:
        if context: err.toggle_context()
        print(str(err))


def print_command_step(content: str):
    print(pad_header(content))



### FILE HANDLING ###
def create_migration_filename(migrationIndex: int) -> str:
    return f"Migration_{migrationIndex}.json"


def create_sqlmigration_filename(migrationIndex: int) -> str:
    return f"SQLMigration_{migrationIndex}.json"


def write_sqlmigration_file(folder: str, sqlMigration: SQLMigrations.SQLMigration):

    # Writes a new SQL Migration file
    newFile = open(os.path.join(folder, create_sqlmigration_filename(sqlMigration.migrationIndex)), "w")
    newFile.write(json.dumps(sqlMigration.__dict__, indent=4))
    newFile.close()


def get_all_migrations(migrationsFolder: str) -> list[SchemaMigration]:

    #NOTE: This assumes that the folder exists
    folderFiles = os.listdir(migrationsFolder)
    foundMigrations: list[SchemaMigration] = []

    for fileName in folderFiles:
        filePath = os.path.join(migrationsFolder,fileName)
        if re.match(MIGRATIONS_FILE_REGEX, fileName):
            try: 
                file = open(filePath)
                foundMigrations.append(SchemaMigration.from_dict(json.loads(file.read())))
            except IOError as err:
                print(pad_err(f"Could not open migration file: '{filePath}': {err}"))
        else:
            print_debug(f"Skipping file '{filePath}' because it is not a migration file.")

    # Before returning, sort lowest to greatest.
    foundMigrations.sort(key=lambda migration: migration.migrationIndex)
    return foundMigrations

def get_sql_migrations_as_dicts(migrationsFolder: str) -> list[dict]:

    #NOTE: This assumes that the folder exists
    folderFiles = os.listdir(migrationsFolder)
    foundMigrations: list[dict] = []

    for fileName in folderFiles:
        filePath = os.path.join(migrationsFolder,fileName)
        if re.match(MIGRATIONS_SQL_FILE_REGEX, fileName):
            try: 
                file = open(filePath)
                foundMigrations.append(json.loads(file.read()))
            except IOError as err:
                print(pad_err(f"Could not open SQL migration file: '{filePath}': {err}"))
        else:
            print_debug(f"Skipping file '{filePath}' because it is not an SQL migration file.")

    # Before returning, sort lowest to greatest.
    foundMigrations.sort(key=lambda migration: migration["migrationIndex"])
    return foundMigrations

def write_sql_migrations_combined_file(migrationsFolder: str):

    # Opens all SQLMigration files
    if not os.path.exists(migrationsFolder):
        print(pad_err(f"Migrations folder '{migrationsFolder}' does not exist!"))
        return
    
    existingSQLMigrations = get_sql_migrations_as_dicts(migrationsFolder)

    # Removes the existing combined file
    if os.path.exists(os.path.join(migrationsFolder, SQL_MIGRATIONS_COMBINED_FILE)):
        os.remove(os.path.join(migrationsFolder, SQL_MIGRATIONS_COMBINED_FILE))
    
    # Creates a new one and populates it
    combinedFile = open(os.path.join(migrationsFolder, SQL_MIGRATIONS_COMBINED_FILE), "w")
    fileContentsDict = {"sql_migrations":[]}

    for existingMigration in existingSQLMigrations:
        fileContentsDict["sql_migrations"].append(existingMigration)

    combinedFile.write(json.dumps(fileContentsDict, indent=4))
    combinedFile.close()
    


### COMMANDS ###
def create_new_migration(dbSchemaFilePath: str, migrationsFolder: str):
    
    # Checks if necessary files exist
    try:
        file = open(dbSchemaFilePath)
    except IOError as err:
        print(pad_err(f"Failed to open file '{dbSchemaFilePath}': {err}"))
        return

    if not os.path.exists(migrationsFolder):
        print(pad_err(f"Migrations folder '{migrationsFolder}' does not exist!"))
        return

    # Gets the new schema - adds the migrations table to it
    newSchema: DatabaseSchema = DatabaseSchema.from_json(file.read())
    newSchema.add_table(MIGRATIONS_TABLE.copy())

    # Validates the new schema
    print_command_step("Validating New Schema")

    schemaErrors = newSchema.validate_self()
    
    if len(schemaErrors) > 0:
        print_errors(schemaErrors, False)
        print(pad_err("Failed to validate new schema. Fix the errors and try again."))
        return
    else:
        print(pad_ok("New schema validated!"))
        

    # Assembles the existing schema and validates each migration as it goes along
    print_command_step("Assembling and Validating Existing Schema")

    existingMigrations = get_all_migrations(migrationsFolder)
    previousSchema = DatabaseSchema([])
    for migration in existingMigrations:
        migrationErrors = migration.migrate_schema(previousSchema)
    
        if len(migrationErrors) > 0:
            print_errors(migrationErrors, True)
            print(pad_err(f"Failed to validate migration #{migration.migrationIndex}. Fix the errors and try again."))
            return
        else:
            print(pad_ok(f"Validated migration #{migration.migrationIndex}"))

    # Prints the previous schema
    print_command_step("Showing Previous Schema:")
    print(str(previousSchema))

    # Starts constructing the new migration
    print_command_step("Finding changes and creating the new migration")

    newIndex = existingMigrations[-1].migrationIndex+1 if len(existingMigrations) > 0 else 0
    newMigration = SchemaMigration(newIndex, CreateMigration.create_migrations_for_objects(previousSchema.tables, newSchema.tables, Table))

    # Prints the finalized migration to the user
    print_command_step("Confirming migration")

    if len(newMigration.tableMigrations) == 0:
        print(pad_err("There are no changes to be made."))
    
    else:
        print(newMigration)
        if ask_yes_no("Save this migration?"):
            
            newFile = open(os.path.join(migrationsFolder, create_migration_filename(newMigration.migrationIndex)),  "w")
            newFile.write(json.dumps(newMigration.to_dict(), indent=4))
            newFile.close()

        else:
            print(pad_err("Cancelled.")) 


def validate_schema(dbSchemaFilePath: str, showContextString: str):

    try:
        file = open(dbSchemaFilePath)
    except IOError as err:
        print(pad_err(f"Failed to open file '{dbSchemaFilePath}': {err}"))
        return
    
    # Gets whether to show context
    showContext = True if showContextString.lower() == 'true' else False
    
    # Reads in the schema, returns if error
    print_command_step("Getting schema...")
    try:
        dbSchema: DatabaseSchema = DatabaseSchema.from_json(file.read())
        dbSchema.add_table(MIGRATIONS_TABLE.copy())
    except json.JSONDecodeError as e:
        print(pad_err(f"Error reading JSON file: {str(e)}"))
        return
    
    # Validates the schema itself, prints all the errors
    print(pad_ok("JSON file is valid."))
    print_command_step("Validating schema...")
    errors: list[ValidationError] = dbSchema.validate_self()

    if len(errors) > 0:
        for err in errors:
            if showContext: err.toggle_context()
            print(err)
    else:
        print(pad_success("No errors found!"))

    print_command_step("Parsed Schema:")
    print(dbSchema)


def test_migrations(migrationsFolder: str):

    if not os.path.exists(migrationsFolder):
        print(pad_err(f"Migrations folder '{migrationsFolder}' does not exist!"))
        return

    # Assembles a schema using the found migrations
    print_command_step("Finding Migrations")
    existingMigrations = get_all_migrations(migrationsFolder)
    print(pad_ok(f"Found migrations! Highest index: {existingMigrations[-1].migrationIndex}"))

    schema = DatabaseSchema([])
    for migration in existingMigrations:
        print(pad_ok(f"Running migration #{migration.migrationIndex}!"))
        errors = migration.migrate_schema(schema)
        print_errors(errors, False)


    print_command_step("Finished creating end schema:")
    print(str(schema))

    print_command_step("Creating SQL Migrations")
    

def create_sql_migrations(migrationsFolder: str): 

    # Checks if the migrations folder exists
    if not os.path.exists(migrationsFolder):
        print(pad_err(f"Migrations folder '{migrationsFolder}' does not exist!"))
        return
    
    # Gets all migrations, then checks which have equivalent SQL migrations
    print_command_step("Finding migrations without equivalent SQL migration")
    foundMigrations = get_all_migrations(migrationsFolder)
    runningSchema = DatabaseSchema([])

    for migration in foundMigrations:
        
        if not os.path.exists(os.path.join(migrationsFolder, create_sqlmigration_filename(migration.migrationIndex))):
            print(pad_ok(f"Writing SQL Migration for Migration #{migration.migrationIndex}."))
            createdSqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, runningSchema)
            print(createdSqlMigration)
            write_sqlmigration_file(migrationsFolder, createdSqlMigration)

        else:
            print(pad_ok(f"SQL Migration exists for Migration #{migration.migrationIndex}"))

        migration.migrate_schema(runningSchema) #NOTE: We assume no validation errors

    # Writes the combined file - this is REGENERATED each time.
    print(pad_header("Writing new Combined SQL Migrations file"))
    write_sql_migrations_combined_file(migrationsFolder)

    print(pad_success("Created SQL Migrations!"))


def run_tests():

    print_command_step("Starting tests...")
    Tests.run_all_tests()


### MAIN ###
def main(args: list[str]):

    # Using global variables (eg. debug)
    global DEBUG_ON

    # Enables colour
    os.system("color")

    # Sets some default variables
    if "-v" in args:
        DEBUG_ON = True
        args.remove("-v")
    else:
        DEBUG_ON = False

    # Creates commands
    commands = [
        Commands.Command("createmigration", 
                "Creates a new migration, given a list of previous migrations and a new schema.",
                create_new_migration,
                [
                    "schema_file: The updated schema.",
                    "folder_with_migrations: A folder containing all existing migrations for this schema."
                ]),
        Commands.Command("validateschema", 
                "Confirms that a DB schema is valid and has no major errors. This is NOT a thorough check. Any datatype or constraint is considered valid.",
                validate_schema,
                [
                    "schema_file: The updated schema.",
                    "show_context: True/False, whether or not to show the context of errors. Enabling it can be messy if you have a lot of errors."
                ]),
        Commands.Command("sqlmigration", 
                "Creates SQL migrations for all existing migrations that don't have SQL yet. Note: This is written for SQLite only, other DBs might not work.",
                create_sql_migrations,
                [
                    "folder_with_migrations: The migration folder to use.",
                ]),
        Commands.Command("runtests", 
                "Runs a suite of test cases on the migrations.",
                run_tests,
                []),
    ]

    # Errors out if invalid args
    if len(args) == 0:
        print("""Expected format: <command> [...args] [-v]""")
        print(pad_warning(Commands.get_command_list_text(commands)))
        print(pad_warning("-v: Print debug text (ie. be more verbose)"))
        return
    
    # Chooses command to run
    commandName = args[0].lower()
    commandArgs = args[1:]
    Commands.try_call_command(commands, commandName, *commandArgs)
        

if __name__ == "__main__":
    main(sys.argv[1:])
