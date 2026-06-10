import logging
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, status
from fastapi.responses import StreamingResponse
from app.services.gridfs_service import GridFSService

logger = logging.getLogger("app.api.uploads")
router = APIRouter()

@router.post("/uploads/return-image")
async def upload_return_image(
    file: UploadFile = File(...),
    order_id: str = Form(...),
    product_id: str = Form(...),
    reason: str = Form(...)
):
    """
    Validate, store in GridFS, record return metadata logs, and return file_id.
    """
    # Build metadata dictionary to store alongside GridFS binary
    metadata = {
        "order_id": order_id,
        "product_id": product_id,
        "reason": reason
    }

    try:
        file_id = await GridFSService.upload_file(file, metadata=metadata)
        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "message": "Image uploaded successfully"
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Image upload API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload processing failed: {str(e)}"
        )

@router.get("/uploads/{file_id}")
async def get_return_image(file_id: str):
    """
    Fetch image file from GridFS and stream it back with correct MIME headers.
    """
    try:
        file_stream, filename, content_type = await GridFSService.get_file(file_id)
        
        async def file_generator():
            # Stream in chunks
            while chunk := file_stream.read(1024 * 64):
                yield chunk

        return StreamingResponse(file_generator(), media_type=content_type)
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Get image API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve file: {str(e)}"
        )

@router.delete("/uploads/{file_id}")
async def delete_return_image(file_id: str):
    """
    Clean up file from GridFS storage and clean up return_images_metadata logs.
    """
    try:
        deleted = await GridFSService.delete_file(file_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found or already deleted.")
        return {
            "success": True,
            "message": "Image deleted successfully from database and GridFS"
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Delete image API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )
