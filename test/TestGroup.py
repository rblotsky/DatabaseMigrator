### CLASSES ###
class TestGroup:
    name: str
    funcs: list

    def __init__(self, name: str, funcs: list):
        self.name = name
        self.funcs = funcs


    def add_func(self, func):
        self.funcs.append(func)

### DECORATORS ###
def group_test(groups: dict, name: str, active: bool):

    def decorator_group_test(func):

        # Registers the test into a group
        if active:
            if name in groups:
                groupUsed: TestGroup = groups[name]
                groupUsed.add_func(func)

            else:
                groupUsed = TestGroup(name, [func])
                groups[name] = groupUsed

        return func
    
    return decorator_group_test


### ALL TEST GROUPS ###
allTestGroups = {}