import sys
import re
import os
from io import IOBase
from pathlib import Path
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
MIGRATIONS_FILE_REGEX = r"Migration_([1-9][0-9]*|0)(_\w+)?\.json"
MIGRATIONS_SQL_FILE_REGEX = r"SQLMigration_([1-9][0-9]*|0)(_\w+)?\.json"
SQL_MIGRATIONS_COMBINED_FILE = "SQLMigration_Combined.json"
DEBUG_ON = False


### UTILITY ###
def print_debug(content: str):
    if DEBUG_ON:
        print(
            colours.BOLD,
            colours.WARNING,
            "[DEBUG]",
            colours.ENDC,
            colours.BOLD,
            " ",
            content,
            colours.ENDC,
            sep="",
        )


def print_errors(errors: list[ValidationError], context: bool):
    for err in errors:
        if context:
            err.toggle_context()
        print(str(err))


def print_command_step(content: str):
    print(pad_header(content))


def get_missing_migration_indices(highest_index: int, indices: list[int]) -> list[int]:
    missing_indices = []
    for i in range(highest_index + 1):
        if i not in indices:
            missing_indices.append(i)
    return missing_indices


### FILE HANDLING ###
def create_migration_filename(migration: SchemaMigration) -> str:
    if migration.migrationName == None:
        return f"Migration_{migration.migrationIndex}.json"

    return f"Migration_{migration.migrationIndex}_{migration.migrationName}.json"


def create_sqlmigration_filename(sql_migration: SQLMigrations.SQLMigration) -> str:
    if sql_migration.migrationName == None:
        return f"SQLMigration_{sql_migration.migrationIndex}.json"

    return f"SQLMigration_{sql_migration.migrationIndex}_{sql_migration.migrationName}.json"


def open_schema_migration_files_from_folder(folder: Path) -> list[IOBase]:

    found_files = []
    for filePath in folder.glob("*.json"):
        if re.match(MIGRATIONS_FILE_REGEX, filePath.name):
            if filePath.is_file():
                found_files.append(open(filePath))

    return found_files


def extract_schema_migrations_from_files(
    migration_files: list[IOBase],
) -> list[SchemaMigration]:

    foundMigrations: list[SchemaMigration] = []

    for file in migration_files:
        foundMigrations.append(SchemaMigration.from_dict(json.loads(file.read())))
        file.close()

    # Before returning, sort lowest to greatest
    foundMigrations.sort(key=lambda migration: migration.migrationIndex)

    return foundMigrations


def open_sql_migration_files_from_folder(folder: Path) -> list[IOBase]:

    found_files = []
    for filePath in folder.glob("*.json"):
        if re.match(MIGRATIONS_SQL_FILE_REGEX, filePath.name):
            if filePath.is_file():
                found_files.append(open(filePath))
    return found_files


def get_sql_migrations_as_dicts(opened_files: list[IOBase]) -> list[dict]:

    foundMigrations: list[dict] = []

    for file in opened_files:
        foundMigrations.append(json.loads(file.read()))
        file.close()

    # Before returning, sort lowest to greatest
    foundMigrations.sort(key=lambda migration: migration["migrationIndex"])

    return foundMigrations


### FUNCTIONALITY ###
def create_new_migration(
    db_schema_file: IOBase, existing_migrations_files: list[IOBase]
) -> SchemaMigration:

    # Gets the new schema - adds the migrations table to it
    newSchema: DatabaseSchema = DatabaseSchema.from_json(db_schema_file.read())
    newSchema.add_table(MIGRATIONS_TABLE.copy())

    # Validates the new schema
    print_command_step("Validating New Schema")

    schemaErrors = newSchema.validate_self()

    if len(schemaErrors) > 0:
        print_errors(schemaErrors, False)
        print(pad_err("Failed to validate new schema. Fix the errors and try again."))
        return None
    else:
        print(pad_ok("New schema validated!"))

    # Assembles the existing schema and validates each migration as it goes along
    print_command_step("Assembling and Validating Existing Schema")

    existing_migrations = extract_schema_migrations_from_files(
        existing_migrations_files
    )
    migration_indices = [migration.migrationIndex for migration in existing_migrations]
    missing_indices = get_missing_migration_indices(
        migration_indices[-1], migration_indices
    )
    if missing_indices != []:
        raise ValueError(f"There are missing migrations: {missing_indices}")

    previousSchema = DatabaseSchema([])
    for migration in existing_migrations:
        migrationErrors = migration.migrate_schema(previousSchema)

        if len(migrationErrors) > 0:
            print_errors(migrationErrors, True)
            print(
                pad_err(
                    f"Failed to validate migration #{migration.migrationIndex}. Fix the errors and try again."
                )
            )
            return None
        else:
            print(pad_ok(f"Validated migration #{migration.migrationIndex}"))

    # Prints the previous schema
    print_command_step("Showing Previous Schema:")
    print(str(previousSchema))

    # Starts constructing the new migration
    print_command_step("Finding changes and creating the new migration")

    newIndex = (
        existing_migrations[-1].migrationIndex + 1
        if len(existing_migrations) > 0
        else 0
    )
    newMigration = SchemaMigration(
        newIndex,
        CreateMigration.create_migrations_for_objects(
            previousSchema.tables, newSchema.tables, Table
        ),
    )

    # Prints the finalized migration to the user
    print_command_step("Confirming migration")

    if len(newMigration.tableMigrations) == 0:
        print(pad_err("There are no changes to be made."))
        return None
    else:
        print(newMigration)
        return newMigration


def validate_schema(db_schema_file: IOBase, show_context: bool) -> DatabaseSchema:

    # Reads in the schema, returns if error
    print_command_step("Getting schema...")
    try:
        db_schema: DatabaseSchema = DatabaseSchema.from_json(db_schema_file.read())
        db_schema.add_table(MIGRATIONS_TABLE.copy())
    except json.JSONDecodeError as e:
        raise e

    # Validates the schema itself, prints all the errors
    print(pad_ok("JSON file is valid."))
    print_command_step("Validating schema...")
    errors: list[ValidationError] = db_schema.validate_self()

    if len(errors) > 0:
        for err in errors:
            if show_context:
                err.toggle_context()
            print(err)
    else:
        print(pad_success("No errors found!"))

    print_command_step("Parsed Schema:")
    print(db_schema)
    return db_schema


def create_sql_migrations(
    existing_migrations: list[SchemaMigration], existing_sql_migrations: list[dict]
) -> list[dict]:

    # Checks which migrations which have equivalent SQL migrations
    runningSchema = DatabaseSchema([])
    sql_migration_indices = [
        migration["migrationIndex"] for migration in existing_sql_migrations
    ]
    new_sql_migrations = []

    for migration in existing_migrations:

        if migration.migrationIndex not in sql_migration_indices:
            print(
                pad_ok(
                    f"Writing SQL Migration for Migration #{migration.migrationIndex}."
                )
            )
            created_sql_migration = SQLMigrations.create_sql_for_schema_migration(
                migration, runningSchema
            )
            print(created_sql_migration)
            new_sql_migrations.append(created_sql_migration)

        else:
            print(
                pad_ok(
                    f"SQL Migration exists for Migration #{migration.migrationIndex}"
                )
            )

        migration.migrate_schema(runningSchema)  # NOTE: We assume no validation errors

    # Writes the combined file - this is REGENERATED each time.
    print(pad_success("Created SQL Migrations!"))
    return new_sql_migrations


def run_tests():

    print_command_step("Starting tests...")
    Tests.run_all_tests()


### COMMANDS ###
def validate_schema_command(schema_file_path: str, show_context_text: str):
    try:
        db_schema_file = open(Path(schema_file_path))
    except IOError as err:
        print(pad_err(str(err)))
        return

    show_context = True if show_context_text.lower() == "true" else False

    validate_schema(db_schema_file, show_context)


def create_migration_command(db_schema_path: str, migrations_folder_path: str):

    try:
        db_schema_file = open(Path(db_schema_path))
        migrations_folder = Path(migrations_folder_path)

        migrations_folder_contents = open_schema_migration_files_from_folder(
            migrations_folder
        )
    except IOError as err:
        print(pad_err(str(err)))
        return

    new_migration = create_new_migration(db_schema_file, migrations_folder_contents)
    if new_migration is not None:
        if ask_yes_no("Save this migration?"):
            if ask_yes_no(
                "Give this migration a name? Use this if you're using a branched repository."
            ):
                newMigrationName = ask_for_input(
                    "Write a unique name here (alphanumeric chars only, no spaces. Underscore allowed.)"
                )
                new_migration.migrationName = newMigrationName

            newFile = open(
                os.path.join(
                    migrations_folder, create_migration_filename(new_migration)
                ),
                "w",
            )
            newFile.write(json.dumps(new_migration.to_dict(), indent=4))
            newFile.close()

        else:
            print(pad_err("Cancelled."))


def create_sql_migrations_command(migrations_folder_path: str):
    try:
        migrations_folder = Path(migrations_folder_path)

        schema_migration_files = open_schema_migration_files_from_folder(
            migrations_folder
        )
        sql_migration_files = open_sql_migration_files_from_folder(migrations_folder)
    except IOError as err:
        print(pad_err(str(err)))
        return

    sql_migrations = create_sql_migrations(
        extract_schema_migrations_from_files(schema_migration_files),
        get_sql_migrations_as_dicts(sql_migration_files),
    )

    for migration in sql_migrations:
        newFile = open(
            os.path.join(migrations_folder, create_sqlmigration_filename(migration)),
            "w",
        )
        newFile.write(str(migration))
        newFile.close()


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
        Commands.Command(
            "createmigration",
            "Creates a new migration, given a list of previous migrations and a new schema.",
            create_migration_command,
            [
                "schema_file: The updated schema.",
                "folder_with_migrations: A folder containing all existing migrations for this schema.",
            ],
        ),
        Commands.Command(
            "validateschema",
            "Confirms that a DB schema is valid and has no major errors. This is NOT a thorough check. Any datatype or constraint is considered valid.",
            validate_schema_command,
            [
                "schema_file: The updated schema.",
                "show_context: True/False, whether or not to show the context of errors. Enabling it can be messy if you have a lot of errors.",
            ],
        ),
        Commands.Command(
            "sqlmigration",
            "Creates SQL migrations for all existing migrations that don't have SQL yet. Note: This is written for SQLite only, other DBs might not work.",
            create_sql_migrations_command,
            [
                "folder_with_migrations: The migration folder to use.",
            ],
        ),
        Commands.Command(
            "runtests", "Runs a suite of test cases on the migrations.", run_tests, []
        ),
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
