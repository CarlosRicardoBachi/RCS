# HOTFIX v0.3.10.2.78
# GMPR import defensive fix for missing ObjectType

try:
    from rcs.core.object_types import ObjectType
except ImportError:
    ObjectType = None

class GMPRImporter:
    def __init__(self, logger):
        self.logger = logger

    def parse_object_type(self, node_type):
        if ObjectType is not None:
            return ObjectType.from_string(node_type)
        else:
            self.logger.warning(
                f"GMPR import: ObjectType not available, using raw type '{node_type}'"
            )
            return node_type
