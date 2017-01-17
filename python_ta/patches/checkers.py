"""Patch pylint checker behaviour.
"""
import astroid
from astroid.bases import BUILTINS
from pylint.checkers.base import NameChecker
from pylint.checkers.classes import ClassChecker
from pylint.checkers.utils import node_frame_class
from python_ta.checkers.global_variables_checker import is_in_main


def patch_checkers():
    """Run patches to modify built-in pylint checker behaviour."""
    _override_check_protected_attribute_access()
    _override_check_invalid_name_in_main()
    _override_attribute_defined_outside_init()


def _override_check_protected_attribute_access():
    """Override protected-member-access check.

    We find pylint's default protected-member-access check too restrictive in
    method bodies; it only allows protected attribute access on the 'self'
    parameter (and from the class itself).

    We change this behaviour to allow access to any protected attribute that is
    defined for this class. (This leads to false negatives unless we combine
    this with type inference, but we're okay with that.)
    """
    old_check_protected_attribute_access =\
        ClassChecker._check_protected_attribute_access

    def _check(self, node):
        attrname = node.attrname
        klass = node_frame_class(node)
        if klass is None or (
                    attrname not in klass.instance_attrs and
                    attrname not in klass.locals):
            old_check_protected_attribute_access(self, node)

    ClassChecker._check_protected_attribute_access = _check


def _override_check_invalid_name_in_main():
    """Override invalid-name check for variables in main block.

    pylint normally complains about variable names in the main block
    that aren't in ALL_CAPS -- in other words, it assumes that all such
    variables should be constants. We disable this check here so that
    non-constant variable names are permitted (encourages experimentation
    in the main block).
    """
    old_visit_assignname = NameChecker.visit_assignname

    def patched_visit_assignname(self, node):
        if is_in_main(node):
            self._check_name('variable', node.name, node)
        else:
            old_visit_assignname(self, node)

    NameChecker.visit_assignname = patched_visit_assignname


def _override_attribute_defined_outside_init():
    """Eliminate attribute-defined-outside-init error when using properties.

    Checks for properties using the "a = property(_get_a, _set_a)" approach
    (no decorator support yet), and allows for a member to be set in the setter
    as long as the setter is called (implicitly) in __init__.
    """
    old_leave_classdef = ClassChecker.leave_classdef

    def new_leave_classdef(self, cnode):
        for attr, nodes in cnode.instance_attrs.items():
            setter = _get_attribute_property_setter(attr, cnode)
            if setter is not None:
                self.config.defining_attr_methods = self.config.defining_attr_methods + (setter, )

        old_leave_classdef(self, cnode)

    ClassChecker.leave_classdef = new_leave_classdef


def _get_attribute_property_setter(name, klass):
    """Return the name of a setter for name in klass, if name is a property."""
    try:
        attributes = klass.getattr(name)
    except astroid.NotFoundError:
        return None

    property_name = "{0}.property".format(BUILTINS)
    for attr in attributes:
        try:
            infered = next(attr.infer())
        except astroid.InferenceError:
            continue
        if infered.pytype() == property_name:
            try:
                # In this case, attr is in a statement of the form
                # <attr> = property(<fget>, <fset>); return the name of <fset>,
                # assuming it is an identifier (and not a more complex expression).
                return attr.parent.value.args[1].name
            except Exception:
                return None
