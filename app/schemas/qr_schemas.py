from pydantic import BaseModel, HttpUrl

class QRCodeOut(BaseModel):
    canvas_id: int
    qr_id: int
    qr_link: HttpUrl

    class Config:
        orm_mode = True
