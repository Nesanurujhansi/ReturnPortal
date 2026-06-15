import io
import mimetypes
import logging
from bson import ObjectId
from fastapi import UploadFile, HTTPException
from typing import Dict, Any, Optional, Tuple
from app.database.mongodb import db

logger = logging.getLogger("app.gridfs")

# Fallback offline cache for image uploads when MongoDB is not connected
MOCK_GRIDFS_CACHE = {}
MOCK_METADATA_CACHE = {}

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

class GridFSService:
    @staticmethod
    def validate_file(file: UploadFile, file_size: int) -> Tuple[bool, str]:
        """Validate file content type and size limits."""
        # 1. Content Type Check
        if file.content_type not in ALLOWED_TYPES:
            return False, f"Unsupported file type ({file.content_type}). Only JPEG, PNG, JPG, and WEBP images are allowed."

        # 2. File Size Check
        if file_size > MAX_FILE_SIZE:
            return False, f"File size too large ({(file_size / (1024 * 1024)):.2f} MB). Maximum size allowed is 5 MB."

        return True, ""

    @classmethod
    async def upload_file(cls, file: UploadFile, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Uploads file content to GridFS and inserts metadata records."""
        # Read file bytes to validate size
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        # Reset file cursor for any future reads
        await file.seek(0)

        # Validate
        is_valid, err_msg = cls.validate_file(file, file_size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=err_msg)

        meta_doc = metadata or {}
        meta_doc.update({
            "filename": file.filename,
            "contentType": file.content_type,
            "size_bytes": file_size
        })

        if db.fs is not None:
            try:
                # Open upload stream
                grid_in = db.fs.open_upload_stream(
                    filename=file.filename,
                    metadata=meta_doc
                )
                await grid_in.write(file_bytes)
                await grid_in.close()
                file_id = str(grid_in._id)

                # Store metadata log in return_images_metadata
                meta_doc["file_id"] = file_id
                await db.return_images_metadata.insert_one(meta_doc)

                logger.info(f"Image {file.filename} uploaded to GridFS. file_id={file_id}")
                return file_id
            except Exception as e:
                logger.error(f"MongoDB GridFS upload failed: {e}")
                raise HTTPException(status_code=500, detail=f"Database upload failed: {str(e)}")
        else:
            # Fallback mock setup
            file_id = str(ObjectId())
            MOCK_GRIDFS_CACHE[file_id] = {
                "bytes": file_bytes,
                "filename": file.filename,
                "contentType": file.content_type
            }
            MOCK_METADATA_CACHE[file_id] = meta_doc
            logger.warning(f"Saved file {file.filename} in simulated fallback cache. file_id={file_id}")
            return file_id

    @classmethod
    async def get_file(cls, file_id: str) -> Tuple[io.BytesIO, str, str]:
        """Retrieves raw file stream, filename, and content type from GridFS."""
        if db.fs is not None:
            try:
                obj_id = ObjectId(file_id)
                grid_out = await db.fs.open_download_stream(obj_id)
                
                # Fetch metadata
                content_type = grid_out.metadata.get("contentType") if grid_out.metadata else None
                if not content_type:
                    content_type, _ = mimetypes.guess_type(grid_out.filename)
                content_type = content_type or "application/octet-stream"

                # Read all file bytes into stream
                file_bytes = await grid_out.read()
                return io.BytesIO(file_bytes), grid_out.filename, content_type
            except Exception as e:
                logger.error(f"Failed to retrieve file {file_id} from GridFS: {e}")
                raise HTTPException(status_code=404, detail="Image file not found.")
        else:
            # Fallback mock lookup
            mock_file = MOCK_GRIDFS_CACHE.get(file_id)
            if not mock_file:
                raise HTTPException(status_code=404, detail="Simulated image file not found.")
            return io.BytesIO(mock_file["bytes"]), mock_file["filename"], mock_file["contentType"]

    @classmethod
    async def delete_file(cls, file_id: str) -> bool:
        """Deletes file binary from GridFS and updates metadata logs."""
        deleted = False
        if db.fs is not None:
            try:
                obj_id = ObjectId(file_id)
                await db.fs.delete(obj_id)
                await db.return_images_metadata.delete_many({"file_id": file_id})
                deleted = True
                logger.info(f"Successfully deleted GridFS file: {file_id}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_id} from GridFS: {e}")
                raise HTTPException(status_code=404, detail="File could not be found for deletion.")
        else:
            # Fallback mock delete
            if file_id in MOCK_GRIDFS_CACHE:
                del MOCK_GRIDFS_CACHE[file_id]
                MOCK_METADATA_CACHE.pop(file_id, None)
                deleted = True
                logger.info(f"Successfully deleted simulated file: {file_id}")

        return deleted
