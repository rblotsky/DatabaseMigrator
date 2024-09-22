import functools
import sqlite3
import os
from Schema import *
from Migrations import *
import SQLMigrations
from .TestGroup import *
import collections

### CONSTANTS ###
DATABASE_PATH = "testDB.db"



### UTILITY ###
def setup_database() -> sqlite3.Connection:

    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)

    return sqlite3.connect(DATABASE_PATH)


def assert_tables(dbConn: sqlite3.Connection, tables: list[Table]):

    expectedNames = [table.name for table in tables]

    # Add tables from default sqlite tables
    expectedNames.extend(["sqlite_sequence"])

    actualNames = [item[0] for item in dbConn.execute("""SELECT name FROM sqlite_master WHERE type='table';""").fetchall()]
    
    if collections.Counter(actualNames) != collections.Counter(expectedNames):
        raise Exception(f"Tables are not the same: Actual: {actualNames} VS Expected: {expectedNames}")
    

def assert_columns_in_table(dbConn: sqlite3.Connection, table: Table):

    expectedNames = [col.name for col in table.columns]

    actualNames = [item[0] for item in dbConn.execute(f"""SELECT name FROM PRAGMA_TABLE_INFO('{table.name}');""").fetchall()]

    if collections.Counter(actualNames) != collections.Counter(expectedNames):
        raise Exception(f"Columns are not the same for table {table.name}: Actual: {actualNames} VS Expected: {expectedNames}")


def assert_foreign_keys_in_table(dbConn: sqlite3.Connection, table: Table):
    expectedKeys = [fKey.get_key() for fKey in table.foreignKeys]
    
    actualKeys = [f"{item[3]}->{item[2]}.{item[4]}" for item in dbConn.execute(f"""SELECT * FROM PRAGMA_FOREIGN_KEY_LIST('{table.name}');""").fetchall()]

    if collections.Counter(actualKeys) != collections.Counter(expectedKeys):
        raise Exception(f"Foreign Keys are not the same for table {table.name}: Actual: {actualKeys} VS Expected: {expectedKeys}")


def assert_db_data_equal(expected, actual):
    expectedAsList = []
    for item in expected:
        if type(item) is tuple:
            for val in item:
                expectedAsList.append(val)
        else:
            expectedAsList.append(item)

    actualAsList = []
    for item in actual:
        if type(item) is tuple: 
            for val in item:
                actualAsList.append(val)
        else:
            actualAsList.append(item)

    if collections.Counter(expectedAsList) != collections.Counter(actualAsList):
        raise Exception(f"Data has changed after migration: Expected: {str(expectedAsList)} VS Actual: {str(actualAsList)}")


### DECORATORS ###
def db_test_case(func):
    @functools.wraps(func)
    def wrapper_db_test_case(*args, **kwargs):
        dbConn = setup_database()
        try:
            func(dbConn, *args, **kwargs)
        except Exception as e:
            dbConn.close()
            raise e
        
        dbConn.close()
    
    return wrapper_db_test_case
            


### TEST CASES ###
@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_create_empty_start(dbConn: sqlite3.Connection):

    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Create a migration for creating some tables
    newSchema = DatabaseSchema([firstTable, secondTable])
    migration = SchemaMigration(0, [
        TableMigration(None, "FirstTable", [
            ColumnMigration(None, Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"])),
            ColumnMigration(None, Column("SecondCol", "INTEGER", []))
        ],[
            FKeyMigration(None, ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE"))
        ]),
        TableMigration(None, "SecondTable", [
            ColumnMigration(None, Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]))
        ],[])
    ])

    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, DatabaseSchema([]))
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, newSchema.tables)

    for table in newSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_create_with_existing_tables(dbConn: sqlite3.Connection):

    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])
    
    initialTable = Table("InitialTable", [
        Column("TableID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"])
    ], [])

    initialTableCommand = "CREATE TABLE InitialTable (TableID INTEGER PRIMARY KEY AUTOINCREMENT);"

    # Create a migration for creating some tables
    endSchema = DatabaseSchema([firstTable, secondTable, initialTable])
    migration = SchemaMigration(0, [
        TableMigration(None, "FirstTable", [
            ColumnMigration(None, Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"])),
            ColumnMigration(None, Column("SecondCol", "INTEGER", []))
        ],[
            FKeyMigration(None, ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE"))
        ]),
        TableMigration(None, "SecondTable", [
            ColumnMigration(None, Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]))
        ],[])
    ])

    dbConn.execute(initialTableCommand)
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, DatabaseSchema([initialTable]))
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_remove_no_data(dbConn: sqlite3.Connection):

    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (NewCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);"
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", None, [], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_remove_with_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (NewCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
        "INSERT INTO FirstTable VALUES (5,6);"
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", None, [], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_rename_no_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    renamedFirstTable = Table("REALFirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (NewCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);"
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "REALFirstTable", [], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([renamedFirstTable, secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_rename_with_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    renamedFirstTable = Table("REALFirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (NewCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
        "INSERT INTO FirstTable VALUES (5,6);"
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "REALFirstTable", [], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([renamedFirstTable, secondTable])

    # Extracts the initial data
    initialData = dbConn.execute("SELECT * FROM FirstTable").fetchall()

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Gets the new data
    newData = dbConn.execute("SELECT * FROM REALFirstTable").fetchall()

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)

    assert_db_data_equal(initialData, newData)
    

@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_add_column_no_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    newColumnFirstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", []),
            Column("ThirdColumn", "VARCHAR(255)", ["NOT NULL", "DEFAULT 'TestValue'"])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (NewCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "FirstTable", [
            ColumnMigration(None, Column("ThirdColumn", "VARCHAR(255)", ["NOT NULL", "DEFAULT 'TestValue'"]))
        ], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([newColumnFirstTable, secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_add_column_with_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    newColumnFirstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", []),
            Column("ThirdColumn", "VARCHAR(255)", ["NOT NULL", "DEFAULT 'TestValue'"])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (NewCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
        "INSERT INTO FirstTable VALUES (125, 251);"
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "FirstTable", [
            ColumnMigration(None, Column("ThirdColumn", "VARCHAR(255)", []))
        ], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([newColumnFirstTable, secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Gets data from the migrated DB
    newData = dbConn.execute("SELECT * FROM FirstTable;").fetchall()

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)

    assert_db_data_equal([125,251, None], newData)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_remove_column_no_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    removedColumnFirstTable = Table("FirstTable", [
            Column("SecondCol", "INTEGER", []),
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (SecondCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "FirstTable", [
            ColumnMigration("NewCol", None)
        ], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([removedColumnFirstTable, secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_remove_column_with_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    removedColumnFirstTable = Table("FirstTable", [
            Column("SecondCol", "INTEGER", []),
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (SecondCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
        "INSERT INTO FirstTable VALUES (125, 251);"
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "FirstTable", [
            ColumnMigration("NewCol", None)
        ], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([removedColumnFirstTable, secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Gets data from the table
    newData = dbConn.execute("SELECT * FROM FirstTable;").fetchall()

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)

    assert_db_data_equal([251], newData)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_alter_column_no_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    alteredColumnFirstTable = Table("FirstTable", [
            Column("ChangedNameCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (SecondCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "FirstTable", [
            ColumnMigration("NewCol", Column("ChangedNameCol", "BIGINT", ["NOT NULL", "DEFAULT 1000"]))
        ], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([alteredColumnFirstTable, secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)


@group_test(allTestGroups, "SQL Migration Tests", True)
@db_test_case
def test_sql_migration_alter_column_with_data(dbConn: sqlite3.Connection):
    # Sets up the tables we'll be using
    firstTable = Table("FirstTable", [
            Column("NewCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    alteredColumnFirstTable = Table("FirstTable", [
            Column("ChangedNameCol", "INTEGER", ["NOT NULL", "DEFAULT 1"]),
            Column("SecondCol", "INTEGER", [])
        ],[
            ForeignKey("SecondCol", "SecondTable", "ID", "CASCADE", "CASCADE")
        ])
    secondTable = Table("SecondTable", [
            Column("ID", "INTEGER", ["PRIMARY KEY AUTOINCREMENT"]),
        ],
        [])

    # Creates the setup commands and executes them
    setupCommands = [
        "CREATE TABLE FirstTable (NewCol INTEGER NOT NULL DEFAULT 1, SecondCol INTEGER, FOREIGN KEY (SecondCol) REFERENCES SecondTable(ID) ON UPDATE CASCADE ON DELETE CASCADE);",
        "CREATE TABLE SecondTable (ID INTEGER PRIMARY KEY AUTOINCREMENT);",
        "INSERT INTO FirstTable VALUES (123, 456);"
    ]

    for command in setupCommands:
        dbConn.execute(command)

    # Creates the migration to run
    migration = SchemaMigration(0, [
        TableMigration("FirstTable", "FirstTable", [
            ColumnMigration("NewCol", Column("ChangedNameCol", "BIGINT", ["NOT NULL", "DEFAULT 1000"]))
        ], []),
    ])

    # Sets up the start and end schemas
    initialSchema = DatabaseSchema([firstTable, secondTable])
    endSchema = DatabaseSchema([alteredColumnFirstTable, secondTable])

    # Runs the migration
    sqlMigration = SQLMigrations.create_sql_for_schema_migration(migration, initialSchema)
    
    for sql in sqlMigration.sqlStatements:
        dbConn.execute(sql)

    # Gets the data from the table
    newData = dbConn.execute("SELECT * FROM FirstTable;").fetchall()

    # Performs assertions
    assert_tables(dbConn, endSchema.tables)

    for table in endSchema.tables:
        assert_columns_in_table(dbConn, table)
        assert_foreign_keys_in_table(dbConn, table)

    assert_db_data_equal([123, 456], newData)