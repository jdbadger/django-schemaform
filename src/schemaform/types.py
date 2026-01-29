"""
Type annotations for use in Pydantic models with SchemaForm.

These types provide markers that SchemaForm recognizes to generate
the appropriate Django form fields.

Usage:
    from schemaform import FileUpload, ImageUpload
    from pydantic import BaseModel, field_validator

    class MyModel(BaseModel):
        document: FileUpload
        avatar: ImageUpload | None = None

        @field_validator("document")
        @classmethod
        def validate_document_size(cls, v):
            # v is an UploadedFileWrapper with .name, .size, .content_type
            if v and v.size > 5 * 1024 * 1024:
                raise ValueError("Document must be under 5MB")
            return v

File Validation:
    Django handles mechanical file validation (upload parsing, MIME detection).
    Pydantic handles business logic validation via @field_validator or @model_validator.

    In validators, file fields receive an UploadedFileWrapper instance with:
        - name: str - Original filename
        - size: int - File size in bytes
        - content_type: str - MIME type (e.g., "application/pdf")
        - file: file-like object - The underlying file for reading
        - wrapped: UploadedFile - The original Django UploadedFile object
"""

from typing import Annotated, Any, Protocol, runtime_checkable

from pydantic import Field


@runtime_checkable
class UploadedFileProtocol(Protocol):
    """Protocol for Django's UploadedFile to avoid direct import dependency."""

    name: str
    size: int
    content_type: str

    def read(self, num_bytes: int | None = None) -> bytes: ...
    def seek(self, position: int) -> int: ...


class UploadedFileWrapper:
    """
    Wrapper around Django's UploadedFile for use in Pydantic validators.

    Provides a consistent interface for accessing file metadata in
    @field_validator and @model_validator methods.

    Attributes:
        name: Original filename (e.g., "resume.pdf")
        size: File size in bytes
        content_type: MIME type (e.g., "application/pdf", "image/jpeg")
        file: The underlying file-like object for reading content
        wrapped: The original Django UploadedFile object
    """

    __slots__ = ("_wrapped",)

    def __init__(self, uploaded_file: UploadedFileProtocol) -> None:
        self._wrapped = uploaded_file

    @property
    def name(self) -> str:
        """Original filename."""
        return self._wrapped.name

    @property
    def size(self) -> int:
        """File size in bytes."""
        return self._wrapped.size

    @property
    def content_type(self) -> str:
        """MIME type of the file."""
        return self._wrapped.content_type

    @property
    def file(self) -> Any:
        """The underlying file-like object."""
        return self._wrapped

    @property
    def wrapped(self) -> UploadedFileProtocol:
        """The original Django UploadedFile object."""
        return self._wrapped

    def __bool__(self) -> bool:
        """Allow truthy checks: if file_field: ..."""
        return True

    def __repr__(self) -> str:
        return f"UploadedFileWrapper({self.name!r}, size={self.size}, content_type={self.content_type!r})"


# Marker type for file upload fields.
# Maps to Django's FileField.
# In validators, receives an UploadedFileWrapper instance.
FileUpload = Annotated[Any, Field(json_schema_extra={"format": "binary"})]

# Marker type for image upload fields.
# Maps to Django's ImageField (includes Pillow validation).
# In validators, receives an UploadedFileWrapper instance.
ImageUpload = Annotated[Any, Field(json_schema_extra={"format": "image"})]
