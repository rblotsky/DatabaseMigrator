from Schema import *
from .TestGroup import *

### CONSTANTS ###



### TEST CASES ###
@group_test(allTestGroups, "Schema Dict Serialization", True)
def test_table_serialiation_equivalence():
    dbTable = Table("NewTable", [
            Column("NewCol", "Type2", ["Constraint", "Constraint2"]),
            Column("SecondCol", "Type", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "UPDATE")
        ])
    
    tableDict = dbTable.to_dict()
    parsedTable = Table.from_dict(tableDict)
    equivalent = parsedTable.compare_equivalence(dbTable)

    if not equivalent:
        raise Exception("Comparison of old and parsed tables failed.")
    

@group_test(allTestGroups, "Schema Dict Serialization", True)
def test_column_serialiation_equivalence():
    dbColumn = Column("NewCol", "Type2", ["Constraint", "Constraint2"])
    
    colDict = dbColumn.to_dict()
    parsedCol = Column.from_dict(colDict)
    equivalent = parsedCol.compare_equivalence(dbColumn)

    if not equivalent:
        raise Exception("Comparison of old and parsed columns failed.")
    

@group_test(allTestGroups, "Schema Dict Serialization", True)
def test_foreign_key_serialiation_equivalence():
    fKey = ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "UPDATE")
    
    fKeyDict = fKey.to_dict()
    parsedFKey = ForeignKey.from_dict(fKeyDict)
    equivalent = parsedFKey.compare_equivalence(fKey)

    if not equivalent:
        raise Exception("Comparison of old and parsed foreign keys failed.")
    

@group_test(allTestGroups, "Schema Dict Serialization", True)
def test_db_schema_serialization_equivalence():

    dbTables = [
        Table("NewTable", [
            Column("NewCol", "Type2", ["Constraint", "Constraint2"]),
            Column("SecondCol", "Type", [])
        ],[
            ForeignKey("NewCol", "SecondTable", "ID", "CASCADE", "UPDATE")
        ]),
        Table("SecondTable", [
            Column("ID", "Type2", ["Test"])
        ], [])
    ]

    dbSchema = DatabaseSchema(dbTables)
    dbSchemaJSON = json.dumps(dbSchema.to_dict())
    parsedSchema = DatabaseSchema.from_json(dbSchemaJSON)
    equivalent = parsedSchema.compare_equivalence(dbSchema)
    
    if not equivalent:
        raise Exception("Comparison of old and parsed schemas failed.")
