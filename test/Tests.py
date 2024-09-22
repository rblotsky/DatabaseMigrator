from Migrations import *
from Schema import *
from ColouredText import *
from .TestGroup import TestGroup, allTestGroups
from . import SchemaTests
from . import SQLMigrationTests


def run_all_tests():

    for testGroup in allTestGroups.values():
        run_test_group(testGroup)


def run_test_group(testGroup: TestGroup):
    print(pad_header(f"Testing: {testGroup.name}"))

    totalTests = len(testGroup.funcs)
    failedTests = 0

    for testCase in testGroup.funcs:
        try:
            print(pad_ok(f"TESTING: {testCase.__name__}"))
            testCase()
            print(pad_pass("PASSED."))
        except Exception as e:
            print(pad_err(f"FAILED: {str(e)}"))
            failedTests += 1

    print(pad_header(f"Results:"))
    if failedTests != 0:
        print(pad_err(f"Failed {failedTests}/{totalTests} tests."))

    else:
        print(pad_success(f"No errors! Passed all {totalTests} tests!"))

    print("")

    
