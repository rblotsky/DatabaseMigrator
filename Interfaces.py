class IJsonSerializable:
    
    ## Interface Functions
    def to_dict(self):
        pass

    def from_dict(dictionary: dict):
        pass


class IMigratable(IJsonSerializable):

    ## Interface Functions
    def get_key(self) -> str:
        pass

    def compare_contents(self, other: u'IMigratable') -> bool:
        pass

    def compare_equivalence(self, other: u'IMigratable') -> bool:
        return self.compare_contents(other) and self.get_key() == other.get_key()
    
    def create_object_dict(objects: list[u'IMigratable']) -> dict:
        dictionary = {}
        for obj in objects:
            dictionary[obj.get_key()] = obj
        return dictionary
    
    def copy(self) -> u'IMigratable':
        pass