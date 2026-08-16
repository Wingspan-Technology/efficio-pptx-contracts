"""Public exception types for the efficio_pptx_contracts SDK."""


class EfficioComponentsError(Exception):
    """Base class for all efficio_pptx_contracts SDK errors."""


class MissingResourceError(EfficioComponentsError):
    """Raised when a generated SDK resource cannot be found in the package."""


class UnknownComponentTypeError(EfficioComponentsError):
    """Raised when a component type is not present in the component registry."""
