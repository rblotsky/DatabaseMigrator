# Schema Migrator
Schema Migrator is a tool that migrates SQL databases from one schema to another. (Note: In this case, "schema" means the database format, not the built-in "Schema" feature.)

## Using Schema Migrator
All the commands are run from the file `MigrationsAdmin.py`, via `python MigrationsAdmin.py <command_name> ...args`.

### Typical Workflow
All of these steps (save validation) must be completed whenever a schema change is made to be able to use the new schema in your project. 
1. Update the [Database Schema File](#database-schema-json-file)
2. Run `validateschema` do a basic check for any errors in your schema
3. Run `createmigration` and answer the questions according to how you changed your schema to create a new migration.
4. Run `sqlmigration` to generate SQL commands for any new migrations.


### Commands List
Go to [Implementation Details](#implementation-details) for information on how these commands are implemented.

| Name            | Arguments                                        | Functionality                                                                                                                                        |
|-----------------|--------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| validateschema  | `schema_file: string, show_context: True/False`  | Validates the database schema and prints all validation errors to console. If `show_context` is enabled, shows where each error occurred.            |
| createmigration | `schema_file: string, migrations_folder: string` | Creates a new database migration into the Migrations folder, if there are changes to the schema. Asks for confirmation for any major decisions made. |
| sqlmigration    | `migrations_folder: string`                      | Creates SQL migrations for each migration in the folder, if it doesn't have an equivalent SQL migrations file yet.                                   |
| runtests        | N/A                                              | Runs a test suite to check if the system is functioning correctly. Note, this is NOT an exhaustive test, errors can still occur.                     |

You can provide an optional argument `-v` to tell the program to provide verbose output. This will enable debug messages.

### Requirements
To use Schema Migrator, you'll need:
* A [Database Schema JSON file](#database-schema-json-file)
* A Migrations folder
* The Schema Migrator scripts (this repo)
* Python 3.11.2+

These can be located anywhere you want. Because migrations are not named per schema, do not use the same migrations folder for migrating different databases. Also, avoid naming your schema file with the phrases "Migrations_" or "SQLMigrations_" in it.

### Database Support
This is a list of what databases Schema Migrator can create migration commands for. 
* SQLite

*Note: Many SQL database engines have very similar command structure and execution format. As a result, it is **likely** that this would work with other SQL databases, but it has not been tested on any other than the list above. If a database is compatible with SQLite, you can assume it is compatible with this program too.*

## Advanced Usage
**Note: NEVER alter, delete, or rename migrations that have already been applied to your live database.**

If you want to edit migration files in any way, assume that you have to delete *every* migration that comes after it (and their associated SQLMigrations). If you think the change won't affect the proceeding migrations, think again, and either don't do it or delete them.

### Deleting Migrations
You should **NEVER** remove migrations that have already been applied to your live servers - instead, make a new migration to undo the changes.

If you made changes that have yet to be applied to a live database, and you want to delete them, follow these steps:
1. Remove the "Migration_X.json" and "SQLMigration_X.json" file associated with it (these are found in your migrations folder).
2. Go to "SQLMigration_Combined.json" and remove the list item for the migration (this has the exact same data as the SQLMigration file)
3. Repeat steps 1 and 2 for all migrations *after* the one you removed.

### Manually Editing Migrations
Make sure you know how migration files are structured before making any manual changes. If you manually edit a migration file, make sure to delete and re-generate its associated SQLMigration file.

Generally, you should be able to simply make any edits you want to the migration file, just be careful that you follow the format exactly as specified and double-check that you're inputting values correctly.

Go to [Migration JSON File](#migration-json-file) for information about the format.

*Hint: You can check this by running `createmigration`. It will tell you if it detects any changes between the existing migrations (including your edited one) and the schema file.*


## Implementation Details

- If any changes are made to the contents of an object (not its sub objects), the entire object is considered Migrated and all its data (not subobjects) will be stored in the migration.

### Adding/Removing/Editing Responsibility
- The responsibility of ADDING and REMOVING objects rests on the containing migration - Eg. a SchemaMigration will add/remove tables, and a TableMigration will add/remove columns and foreign keys
- The responsibility of EDITING objects rests on the migration for that object -  A TableMigration will edit the name of a Table


## Usage Restrictions
### Reserved names
- The table "MIGRATIONS_TRACKING_AUTOGEN" is reserved
- Tables cannot have "PRE_MIGRATION_TABLE_" in front of their name
- Tables cannot have "NEW_CREATED_TABLE_" in front of their name

### Miscellaneous
- If you want to switch the names of two completely identical tables without making other changes to them, you have to do it in two separate migrations.

## Appendix - User-Generated / System-Generated Files
### Database Schema JSON File
This is where you create your database schema. The file can be named anything you want. The file format is as follows, you can leave out items listed as optional.
- Ellipsis `...` represents that you can continue to write more items in the list. Do not place a comma after the last one.
- All filled values (table name, column name, data type, etc. etc.) must be in quotation marks `"`.
- Refer to the SQL implementation you're using for a list of valid datatypes, on_update, on_delete, and constraints.
- If writing a constraint that has spaces in it or is followed by a value, put the whole string as a single item.

####

    {
        "tables": [
            {
                "name": "table name",
                "columns": [
                    {
                        "name": "column name",
                        "type": "data type",
                        (OPTIONAL) "constraints": ["constraint", ...]
                    },
                    ...
                ],
                (OPTIONAL) "foreign_keys": [
                    {
                        "local_name": "local column",
                        "table_name": "name of the foreign table",
                        "foreign_name": "column in the foreign table",
                        (OPTIONAL) "on_update": "what to do on update",
                        (OPTIONAL) "on_delete": "what to do on delete"
                    },
                    ...
                ]
            },
            ...
        ]
    }


### Migration JSON File
This JSON file stores a list of all Tables that got updated in the migration. Each table has "sub-migrations" in the form of Column and Foreign Key migrations. 

Each migration has an "old_key" and a list of changes. Note that if **any** change is made to an object, the "new" data will store **all** values of that object (or just the name for tables, because that's the only modifiable attribute).

We detect addition and removal of objects by the presence or absence of the "old_key" and the "new" data (or name). If a "new" data is not given, it is assumed the object has been deleted. If an "old_key" is not given, it is assumed this is a new object.

Most of the time, you will not have to manually touch Migration files, unless there is very specific fine-tuning you wish to do. These are automatically generated by the `createmigration` command in Schema Migrator.

    {
        "index": index of the migration,
        "tables": [
            {
                (OPTIONAL) "old_key": "Name of table this modifies",
                (OPTIONAL) "new_name": "Name of the table after migration",
                "column_migrations": [
                    {
                        (OPTIONAL) "old_key": "Name of column this modifies",
                        (OPTIONAL) "new_data": {
                            "name": "Column name after migration",
                            "type": "Column type after migration",
                            "constraints": ["constraint1","constraint2",...] after migration
                        }
                    },
                    ...
                ],
                (OPTIONAL) "foreign_key_migrations": [
                    {
                        (OPTIONAL) "old_key": "Unique key of foreign key this modifies (format col->table.col)"
                        "new_data": {
                            "local_name": "Local name after migration",
                            "table_name": "Foreign table name after migration",
                            "foreign_name": "Foreign column name after migration",
                            "on_delete": "On delete function after migration",
                            "on_update": "On update function after migration",
                        },
                        ...
                    }
                ]
            },
            ...
        ]
    }

### SQLMigration JSON File
This file stores SQL statements to perform a migration on a database table. These are automatically generated by the `sqlmigration` command in Schema Migrator.

    {
        "migrationIndex": index of the migration,
        "sqlStatements: [
            "statement", "statement", ...
        ]
    }

### SQLMigration_Combined JSON File
This is just a file containing a list of SQLMigrations, as in the above file. They are stored in a list called `"sql_migrations"`. This file is **automatically regenerated** every time `sqlmigrations` is run, using the full list of SQL migrations that are present. It should not be used to store edits.

    {
        "sql_migrations": [
            {
                "migrationIndex": index of the migration,
                "sqlStatements: [
                    "statement", "statement", ...
                ]
            },
            ...
        ]
    }