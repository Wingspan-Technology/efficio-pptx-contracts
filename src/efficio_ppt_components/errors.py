"""Public exception types for the efficio_ppt_components SDK."""


class EfficioComponentsError(Exception):
    """Base class for all efficio_ppt_components SDK errors."""


class MissingResourceError(EfficioComponentsError):
    """Raised when a generated SDK resource cannot be found in the package."""


class UnknownComponentTypeError(EfficioComponentsError):
    """Raised when a component type is not present in the component registry."""
