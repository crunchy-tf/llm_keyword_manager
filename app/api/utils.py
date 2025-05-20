# app/api/utils.py
# (Content remains the same as the last corrected version provided previously)
from bson import ObjectId
from pydantic import GetJsonSchemaHandler, GetCoreSchemaHandler
from pydantic_core import core_schema
from typing import Any

class PyObjectId(ObjectId):
    """ Custom Pydantic type for MongoDB ObjectId handling. """

    @classmethod
    def _validate(cls, v: Any) -> ObjectId:
        """ Internal validation logic. """
        if isinstance(v, ObjectId): return v
        if ObjectId.is_valid(v): return ObjectId(v)
        raise ValueError(f"'{v}' is not a valid ObjectId")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """ Defines core validation and serialization """
        input_schema = core_schema.union_schema(
            [ core_schema.is_instance_schema(ObjectId), core_schema.str_schema(strict=False), ],
        )
        final_schema = core_schema.no_info_after_validator_function(cls._validate, schema=input_schema,)
        serialization_schema = core_schema.plain_serializer_function_ser_schema(
            lambda instance: str(instance), info_arg=False, when_used='json-unless-none'
        )
        return core_schema.lax_or_strict_schema(
                lax_schema=final_schema, strict_schema=final_schema, serialization=serialization_schema,
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema_obj: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        """ Defines the JSON Schema representation (always string). """
        json_schema = handler(core_schema_obj); json_schema = handler.resolve_ref_schema(json_schema)
        json_schema.update(type="string", example="66243f8a1d5b8e9f7a0c1d2e")
        return json_schema