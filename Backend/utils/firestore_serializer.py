"""
Firestore Serialization Utility
Safely converts Python objects (including numpy arrays) to Firestore-compatible types.

This module handles:
- numpy arrays → Python lists
- numpy scalars → Python scalars
- Nested structures (dicts, lists)
- Type validation with clear error messages
- Logging of problematic fields
"""

import logging
from typing import Any, Dict, List, Set, Tuple
import numpy as np

logger = logging.getLogger("pocket_journal.firestore_serializer")

# Firestore-supported types
FIRESTORE_TYPES = (list, dict, float, int, str, bool, type(None))


class FirestoreSerializationError(Exception):
    """Raised when data cannot be serialized for Firestore."""
    pass


def _is_numpy_type(obj: Any) -> bool:
    """Check if object is a numpy type."""
    try:
        return isinstance(obj, (np.ndarray, np.generic))
    except (TypeError, NameError):
        return False


def _convert_numpy_to_python(obj: Any) -> Any:
    """
    Convert numpy types to native Python types.
    
    Args:
        obj: Object to convert
        
    Returns:
        Python-native equivalent
    """
    if isinstance(obj, np.ndarray):
        # Convert array to list
        return obj.tolist()
    elif isinstance(obj, np.generic):
        # Convert numpy scalar (e.g., np.float32, np.int64) to Python scalar
        return obj.item()
    return obj


def serialize_for_firestore(
    data: Any,
    max_depth: int = 100,
    path: str = "<root>",
    collected_errors: Dict[str, str] = None
) -> Any:
    """
    Recursively convert data to Firestore-compatible types.
    
    Handles:
    - numpy.ndarray → list
    - numpy scalars → Python scalars (int, float)
    - Nested dicts and lists
    - Validates all types
    
    Args:
        data: Data to serialize
        max_depth: Maximum recursion depth (prevent infinite loops)
        path: Current path in nested structure (for error messages)
        collected_errors: Dict to collect errors during traversal
        
    Returns:
        Serialized data safe for Firestore
        
    Raises:
        FirestoreSerializationError: If unsupported types remain after conversion
    """
    if collected_errors is None:
        collected_errors = {}
    
    if max_depth <= 0:
        error_msg = f"Max recursion depth exceeded at {path}"
        logger.error(error_msg)
        collected_errors[path] = error_msg
        raise FirestoreSerializationError(error_msg)
    
    # Handle None
    if data is None:
        return None
    
    # Convert numpy types
    if _is_numpy_type(data):
        try:
            converted = _convert_numpy_to_python(data)
            logger.debug(f"Converted numpy type at {path}: {type(data).__name__} → {type(converted).__name__}")
            # Recursively serialize the converted value (in case it's a list)
            return serialize_for_firestore(converted, max_depth - 1, path, collected_errors)
        except Exception as e:
            error_msg = f"Failed to convert numpy type at {path}: {str(e)}"
            logger.error(error_msg)
            collected_errors[path] = error_msg
            raise FirestoreSerializationError(error_msg) from e
    
    # Handle dict
    if isinstance(data, dict):
        serialized_dict = {}
        for key, value in data.items():
            if not isinstance(key, str):
                error_msg = f"Dict key at {path} is not string: {type(key).__name__}"
                logger.error(error_msg)
                collected_errors[f"{path}.{key}"] = error_msg
                raise FirestoreSerializationError(error_msg)
            
            field_path = f"{path}.{key}"
            try:
                serialized_dict[key] = serialize_for_firestore(
                    value, max_depth - 1, field_path, collected_errors
                )
            except FirestoreSerializationError:
                # Re-raise serialization errors immediately
                raise
            except Exception as e:
                error_msg = f"Error serializing field {field_path}: {str(e)}"
                logger.error(error_msg)
                collected_errors[field_path] = error_msg
                raise FirestoreSerializationError(error_msg) from e
        
        return serialized_dict
    
    # Handle list
    if isinstance(data, list):
        serialized_list = []
        for idx, item in enumerate(data):
            item_path = f"{path}[{idx}]"
            try:
                serialized_list.append(
                    serialize_for_firestore(item, max_depth - 1, item_path, collected_errors)
                )
            except FirestoreSerializationError:
                # Re-raise serialization errors immediately
                raise
            except Exception as e:
                error_msg = f"Error serializing list item at {item_path}: {str(e)}"
                logger.error(error_msg)
                collected_errors[item_path] = error_msg
                raise FirestoreSerializationError(error_msg) from e
        
        return serialized_list
    
    # Handle Firestore-compatible scalars
    if isinstance(data, FIRESTORE_TYPES):
        return data
    
    # Unsupported type
    type_name = type(data).__name__
    error_msg = f"Unsupported type at {path}: {type_name}. Must be one of: {', '.join(t.__name__ for t in FIRESTORE_TYPES if t is not type(None))}, None, numpy.ndarray, or numpy scalar"
    logger.error(error_msg)
    logger.error(f"Value: {repr(data)[:200]}")  # Log first 200 chars
    collected_errors[path] = error_msg
    raise FirestoreSerializationError(error_msg)


def validate_firestore_compatible(data: Any, path: str = "<root>") -> bool:
    """
    Validate that data is Firestore-compatible WITHOUT converting.
    Useful for pre-flight checks.
    
    Args:
        data: Data to validate
        path: Current path in structure (for error messages)
        
    Returns:
        True if valid
        
    Raises:
        FirestoreSerializationError: If invalid type found
    """
    if data is None:
        return True
    
    if _is_numpy_type(data):
        raise FirestoreSerializationError(
            f"Numpy type found at {path}: {type(data).__name__}. "
            "Call serialize_for_firestore() to convert."
        )
    
    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str):
                raise FirestoreSerializationError(
                    f"Dict key at {path} is not string: {type(key).__name__}"
                )
            validate_firestore_compatible(value, f"{path}.{key}")
        return True
    
    if isinstance(data, list):
        for idx, item in enumerate(data):
            validate_firestore_compatible(item, f"{path}[{idx}]")
        return True
    
    if isinstance(data, FIRESTORE_TYPES):
        return True
    
    raise FirestoreSerializationError(
        f"Unsupported type at {path}: {type(data).__name__}"
    )


def sanitize_firestore_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a complete Firestore document for writing.
    
    Args:
        document: Document dict to sanitize
        
    Returns:
        Sanitized document safe for Firestore
        
    Raises:
        FirestoreSerializationError: If document contains unsupported types
    """
    try:
        serialized = serialize_for_firestore(document, path="document")
        logger.debug("Document sanitized successfully")
        return serialized
    except FirestoreSerializationError as e:
        logger.error(f"Failed to sanitize document: {str(e)}")
        raise


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Test 1: Simple numpy array (embedding)
    print("Test 1: Embedding (numpy array)")
    embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    serialized = serialize_for_firestore(embedding)
    print(f"  Original type: {type(embedding)}")
    print(f"  Serialized type: {type(serialized)}")
    print(f"  Value: {serialized}\n")
    
    # Test 2: Document with embedding
    print("Test 2: Document with embedding")
    doc = {
        "id": "song_123",
        "title": "Test Song",
        "embedding": np.array([0.1, 0.2, 0.3], dtype=np.float32),
        "popularity": np.int64(85),
        "duration_ms": 180000,
    }
    serialized_doc = serialize_for_firestore(doc)
    print(f"  Original embedding type: {type(doc['embedding'])}")
    print(f"  Serialized embedding type: {type(serialized_doc['embedding'])}")
    print(f"  Serialized doc: {serialized_doc}\n")
    
    # Test 3: Nested structure
    print("Test 3: Nested structure")
    nested = {
        "items": [
            {
                "name": "item1",
                "values": np.array([1.0, 2.0, 3.0], dtype=np.float32),
            },
            {
                "name": "item2",
                "values": np.array([4.0, 5.0, 6.0], dtype=np.float32),
            }
        ],
        "metadata": {
            "count": np.int32(2),
            "total_size": 1500.5
        }
    }
    serialized_nested = serialize_for_firestore(nested)
    print(f"  Nested serialized successfully")
    print(f"  First item values type: {type(serialized_nested['items'][0]['values'])}\n")
    
    # Test 4: Error handling
    print("Test 4: Error handling (unsupported type)")
    try:
        bad_doc = {
            "id": "test",
            "bad_field": object(),  # Unsupported type
        }
        serialize_for_firestore(bad_doc)
    except FirestoreSerializationError as e:
        print(f"  Caught expected error: {str(e)}\n")
    
    print("All tests completed!")

