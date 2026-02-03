"""Comprehensive tests for type annotations."""

import typing

import pytest
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from schemaform.types import FileUpload, ImageUpload


class TestFileUploadType:
    """Test FileUpload type annotation."""

    @pytest.fixture
    def file_upload_metadata(self):
        """Extract FileUpload type metadata."""
        args = typing.get_args(FileUpload)
        return {
            "origin": typing.get_origin(FileUpload),
            "base_type": args[0],
            "field_info": args[1],
        }

    def test_has_annotated_structure_with_binary_format(self, file_upload_metadata):
        """FileUpload is Annotated[Any, FieldInfo] with format='binary'."""
        assert file_upload_metadata["origin"] is typing.Annotated
        assert file_upload_metadata["base_type"] is typing.Any
        assert isinstance(file_upload_metadata["field_info"], FieldInfo)
        assert file_upload_metadata["field_info"].json_schema_extra == {
            "format": "binary"
        }


class TestImageUploadType:
    """Test ImageUpload type annotation."""

    @pytest.fixture
    def image_upload_metadata(self):
        """Extract ImageUpload type metadata."""
        args = typing.get_args(ImageUpload)
        return {
            "origin": typing.get_origin(ImageUpload),
            "base_type": args[0],
            "field_info": args[1],
        }

    def test_has_annotated_structure_with_image_format(self, image_upload_metadata):
        """ImageUpload is Annotated[Any, FieldInfo] with format='image'."""
        assert image_upload_metadata["origin"] is typing.Annotated
        assert image_upload_metadata["base_type"] is typing.Any
        assert isinstance(image_upload_metadata["field_info"], FieldInfo)
        assert image_upload_metadata["field_info"].json_schema_extra == {
            "format": "image"
        }


class TestPydanticIntegration:
    """Test that type annotations work correctly with Pydantic models."""

    def test_works_as_required_pydantic_field_preserving_format(self):
        """Required FileUpload/ImageUpload fields preserve format markers."""

        class TestModel(BaseModel):
            document: FileUpload
            photo: ImageUpload

        model_fields = TestModel.model_fields

        # Fields exist and are required
        assert "document" in model_fields
        assert "photo" in model_fields
        assert model_fields["document"].is_required() is True
        assert model_fields["photo"].is_required() is True

        # Format markers are preserved
        assert model_fields["document"].json_schema_extra == {"format": "binary"}
        assert model_fields["photo"].json_schema_extra == {"format": "image"}

    def test_works_as_optional_pydantic_field_preserving_format(self):
        """Optional FileUpload/ImageUpload fields preserve format markers."""

        class TestModel(BaseModel):
            document: FileUpload | None = None
            photo: ImageUpload | None = None

        model_fields = TestModel.model_fields

        # Fields exist and are optional
        assert "document" in model_fields
        assert "photo" in model_fields
        assert model_fields["document"].is_required() is False
        assert model_fields["photo"].is_required() is False

        # Format markers are preserved in nested metadata
        doc_args = typing.get_args(model_fields["document"].annotation)
        if doc_args and hasattr(doc_args[0], "__metadata__"):
            metadata = doc_args[0].__metadata__[0]
            assert isinstance(metadata, FieldInfo)
            assert metadata.json_schema_extra == {"format": "binary"}

        photo_args = typing.get_args(model_fields["photo"].annotation)
        if photo_args and hasattr(photo_args[0], "__metadata__"):
            metadata = photo_args[0].__metadata__[0]
            assert isinstance(metadata, FieldInfo)
            assert metadata.json_schema_extra == {"format": "image"}

    def test_accepts_any_value_in_pydantic_validation(self):
        """FileUpload/ImageUpload accept any value (Annotated[Any, ...])."""

        class TestModel(BaseModel):
            document: FileUpload
            photo: ImageUpload

        # Accept any value without validation error
        model = TestModel(document="test.txt", photo=123)
        assert model.document == "test.txt"
        assert model.photo == 123

        # Accept None for the underlying Any type
        model2 = TestModel(document=None, photo=None)
        assert model2.document is None
        assert model2.photo is None


class TestAdvancedUsage:
    """Test advanced usage scenarios with Pydantic models."""

    @pytest.mark.parametrize(
        "scenario,model_factory,assertions",
        [
            (
                "field_customization",
                lambda: type(
                    "TestModel",
                    (BaseModel,),
                    {
                        "__annotations__": {"document": FileUpload},
                        "document": Field(
                            title="Document Upload",
                            description="Upload a document file",
                        ),
                    },
                ),
                lambda model: (
                    model.model_fields["document"].title == "Document Upload",
                    model.model_fields["document"].description
                    == "Upload a document file",
                    model.model_fields["document"].json_schema_extra
                    == {"format": "binary"},
                    model.model_fields["document"].annotation is typing.Any,
                ),
            ),
            (
                "nested_models",
                lambda: (
                    type(
                        "AttachmentModel",
                        (BaseModel,),
                        {
                            "__annotations__": {
                                "file": FileUpload,
                                "thumbnail": FileUpload | None,
                            },
                            "thumbnail": None,
                        },
                    ),
                    type(
                        "DocumentModel",
                        (BaseModel,),
                        {
                            "__annotations__": {
                                "title": str,
                                "attachment": type.__call__,
                            },  # Placeholder
                        },
                    ),
                ),
                lambda models: (
                    "file" in models[0].model_fields,
                    "thumbnail" in models[0].model_fields,
                ),
            ),
            (
                "list_types",
                lambda: type(
                    "TestModel",
                    (BaseModel,),
                    {
                        "__annotations__": {
                            "documents": list[FileUpload],
                            "images": list[ImageUpload],
                        },
                        "images": [],
                    },
                ),
                lambda model: (
                    "documents" in model.model_fields,
                    "images" in model.model_fields,
                    model.model_fields["documents"].is_required() is True,
                    model.model_fields["images"].is_required() is False,
                ),
            ),
        ],
    )
    def test_works_in_advanced_pydantic_scenarios(
        self, scenario, model_factory, assertions
    ):
        """FileUpload/ImageUpload work with Field customization, nested models, and lists."""
        if scenario == "field_customization":
            model = model_factory()
            results = assertions(model)
            assert all(results)
        elif scenario == "nested_models":

            class AttachmentModel(BaseModel):
                file: FileUpload
                thumbnail: ImageUpload | None = None

            class DocumentModel(BaseModel):
                title: str
                attachment: AttachmentModel

            assert "file" in AttachmentModel.model_fields
            assert "thumbnail" in AttachmentModel.model_fields
            assert "attachment" in DocumentModel.model_fields
        elif scenario == "list_types":
            model = model_factory()
            results = assertions(model)
            assert all(results)


class TestPublicAPI:
    """Test that types are exported in the public API."""

    def test_types_exported_in_public_api(self):
        """FileUpload and ImageUpload are accessible from schemaform package."""
        import schemaform

        assert hasattr(schemaform, "FileUpload")
        assert hasattr(schemaform, "ImageUpload")
        assert schemaform.FileUpload is FileUpload
        assert schemaform.ImageUpload is ImageUpload

    def test_uploaded_file_wrapper_exported_in_public_api(self):
        """UploadedFileWrapper is accessible from schemaform package."""
        import schemaform

        assert hasattr(schemaform, "UploadedFileWrapper")


class TestUploadedFileWrapper:
    """Tests for UploadedFileWrapper class."""

    @pytest.fixture
    def mock_uploaded_file(self):
        """Create a mock Django UploadedFile."""
        from unittest.mock import Mock

        mock = Mock()
        mock.name = "test_file.pdf"
        mock.size = 12345
        mock.content_type = "application/pdf"
        return mock

    def test_wraps_uploaded_file_properties(self, mock_uploaded_file):
        """Wrapper exposes name, size, content_type from wrapped file."""
        from schemaform.types import UploadedFileWrapper

        wrapper = UploadedFileWrapper(mock_uploaded_file)

        assert wrapper.name == "test_file.pdf"
        assert wrapper.size == 12345
        assert wrapper.content_type == "application/pdf"

    def test_file_property_returns_wrapped_object(self, mock_uploaded_file):
        """The .file property returns the wrapped UploadedFile for reading."""
        from schemaform.types import UploadedFileWrapper

        wrapper = UploadedFileWrapper(mock_uploaded_file)

        assert wrapper.file is mock_uploaded_file

    def test_wrapped_property_returns_original(self, mock_uploaded_file):
        """The .wrapped property returns the original UploadedFile."""
        from schemaform.types import UploadedFileWrapper

        wrapper = UploadedFileWrapper(mock_uploaded_file)

        assert wrapper.wrapped is mock_uploaded_file

    def test_is_truthy(self, mock_uploaded_file):
        """Wrapper should be truthy for use in conditionals."""
        from schemaform.types import UploadedFileWrapper

        wrapper = UploadedFileWrapper(mock_uploaded_file)

        assert wrapper
        assert bool(wrapper) is True

    def test_repr_shows_file_info(self, mock_uploaded_file):
        """repr() should show file info for debugging."""
        from schemaform.types import UploadedFileWrapper

        wrapper = UploadedFileWrapper(mock_uploaded_file)

        result = repr(wrapper)

        assert "test_file.pdf" in result
        assert "12345" in result
        assert "application/pdf" in result

    def test_works_with_simple_uploaded_file(self):
        """Wrapper works with Django's SimpleUploadedFile."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        from schemaform.types import UploadedFileWrapper

        file = SimpleUploadedFile(
            "test.pdf", b"file content", content_type="application/pdf"
        )
        wrapper = UploadedFileWrapper(file)  # type: ignore[arg-type]

        assert wrapper.name == "test.pdf"
        assert wrapper.size == len(b"file content")
        assert wrapper.content_type == "application/pdf"
