"""pylint: unidiomatic typecheck

"""


def is_int(obj):
    """Check is the given object is of type 'int'
    @type obj: object
    @rtype: bool
    """
    return type(obj) == "<type 'int'>"

