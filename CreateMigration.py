from ColouredText import *
from Migrations import *
from Schema import *
from UserIO import *


### MAIN FUNCTIONS ###
def create_object_migration(oldObject: IMigratable, newObject: IMigratable, objectType: type) -> Migration:

    migration = None

    if objectType == Table:
        migration: TableMigration = TableMigration.create_new_migration(oldObject, newObject)
        migration.add_col_migrations(create_migrations_for_objects(oldObject.columns if oldObject != None else [], 
                                                                   newObject.columns if newObject != None else [], 
                                                                   Column))
        migration.add_fkey_migrations(create_migrations_for_objects(oldObject.foreignKeys if oldObject != None else [], 
                                                                    newObject.foreignKeys if newObject != None else [], 
                                                                    ForeignKey))
    
    elif objectType == Column:
        migration: ColumnMigration = ColumnMigration.create_new_migration(oldObject, newObject)

    elif objectType == ForeignKey:
        migration: FKeyMigration = FKeyMigration.create_new_migration(oldObject, newObject)

    else:
        print(pad_err(f"ERROR: create_single_migration() given invalid objectType: {objectType}"))

    return migration


def get_remove_migrations(oldObjects: list[IMigratable], newObjDict: dict, migrations: list[Migration], objectType: type) -> list[Migration]:
    
    # Adds a removal migration if for old objects whose keys aren't in the new objects, 
    # and there are no  existing migrations that migrate their key (eg. renames)

    removeMigrations: list[Migration] = []
    for old in oldObjects:

        if old.get_key() not in newObjDict and old.get_key() not in [migration.oldKey for migration in migrations]:
            removeMigrations.append(create_object_migration(old, None, objectType))

    return removeMigrations


def get_change_migrations(oldDict: dict, newObjects: list[IMigratable], objectType: type) -> list[Migration]:

    # Gets all non-removal migrations by iterating through new objects and comparing them to old ones
    createdMigrations: list[Migration] = [] 
    for new in newObjects:
            
        # If there are no old objects, just mark this as new
        if len(oldDict.keys()) == 0:

            print(pad_ok(f"Assuming {objectType.__name__} '{new.get_key()}' is a NEW {objectType.__name__}."))
            createdMigrations.append(create_object_migration(None, new, objectType))
            
        # If there is an identical version, ignore the object
        elif new.get_key() in oldDict and new.compare_equivalence(oldDict[new.get_key()]):
            pass
        
        # If contents differ with the old version of this name
        elif new.get_key() in oldDict and not new.compare_equivalence(oldDict[new.get_key()]):
                
            # Alteration to old object
            if ask_yes_no(f"Is the {objectType.__name__} '{new.get_key()}' ALTERING '{new.get_key()}'?"):
                createdMigrations.append(create_object_migration(oldDict[new.get_key()], new, objectType))

            # Rename of another old object
            # Does not run for Foreign Keys, because they can't be renamed
            elif objectType != ForeignKey and len(oldDict.values) > 1 and ask_yes_no(f"Is the {objectType.__name__} '{new.get_key()}' RENAMING a {objectType.__name__}?"):
                
                givenName = None
                while not givenName in oldDict:
                    givenName = ask_for_input(f"What is the name of the {objectType.__name__} being renamed?")

                createdMigrations.append(create_object_migration(oldDict[givenName], new, objectType))

            # Assuming it's a new object
            else:
                print(pad_ok(f"Assuming {objectType.__name__} '{new.get_key()}' is a NEW {objectType.__name__}."))
                createdMigrations.append(create_object_migration(None, new, objectType))
            
        # If no old names match this name, check if it's a rename or new table
        else:

            # Checks for old objects that have the same contents
            foundIdenticalOld = False
            for old in oldDict.values():
                if new.compare_contents(old):

                    if ask_yes_no(f"Is the {objectType.__name__} '{new.get_key()}' RENAMING {objectType.__name__} '{old.get_key()}'?"):
                        createdMigrations.append(create_object_migration(old, new, objectType))
                        foundIdenticalOld = True
            
            # If nothing that has same contents
            if not foundIdenticalOld:

                # If rename of an old item - might not even exist.
                if len(oldDict.values()) > 0 and ask_yes_no(f"Is the {objectType.__name__} '{new.get_key()}' RENAMING a {objectType.__name__}?"):

                    givenName = None
                    while not givenName in oldDict:
                        givenName = ask_for_input(f"What is the name of the {objectType.__name__} being renamed?")

                    createdMigrations.append(create_object_migration(oldDict[givenName], new, objectType))

                # If not renaming an old object, assume it's NEW
                else:
                    print(pad_ok(f"Assuming {objectType.__name__} '{new.get_key()}' is a NEW {objectType.__name__}."))
                    createdMigrations.append(create_object_migration(None, new, objectType))

    return createdMigrations


def create_migrations_for_objects(oldObjects: list[IMigratable], newObjects: list[IMigratable], objectType: type) -> list[Migration]:
    
    # Creates dictionaries to quickly access the objects
    oldDict = IMigratable.create_object_dict(oldObjects)
    newDict = IMigratable.create_object_dict(newObjects)

    # Creates all non-removal migrations
    createdMigrations: list[Migration] = get_change_migrations(oldDict, newObjects, objectType)    

    # Creates all remove migrations
    createdMigrations.extend(get_remove_migrations(oldObjects, newDict, createdMigrations, objectType))

    return createdMigrations
