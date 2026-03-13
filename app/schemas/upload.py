from typing import Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    bucket: str
    path: str
    public_url: Optional[str] = None
    content_type: str
    size: int
    message: str