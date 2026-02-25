from pydantic import BaseModel, HttpUrl

class QRCodeOut(BaseModel):
    qr_id: int
    user_id: int
    code: str
    qr_image_url: HttpUrl | None = None

    editor_id: int
    editor_public_id: str
    editor_url: str

    current_template_id: int | None = None
    current_template_file_url: str | None = None

    class Config:
        from_attributes = True
        orm_mode = True


class QRSetTemplateIn(BaseModel):
    template_id: int
    base_url: str | None = None  # Опционально: домен для QR-ссылки
