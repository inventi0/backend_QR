from pydantic import BaseModel, HttpUrl

class QRCodeOut(BaseModel):
    canvas_id: int
    qr_id: int
    qr_image_url: HttpUrl
    code: str
    target_url: HttpUrl

    class Config:
        orm_mode = True
