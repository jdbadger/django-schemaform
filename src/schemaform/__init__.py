from importlib.metadata import PackageNotFoundError, version

from .forms import SchemaForm
from .types import FileUpload, ImageUpload, UploadedFileWrapper

try:
    __version__ = version("django-schemaform")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "SchemaForm",
    "FileUpload",
    "ImageUpload",
    "UploadedFileWrapper",
    "__version__",
]
