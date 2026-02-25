"""
File Validation Utilities

Валидация MIME типов при загрузке файлов для защиты от загрузки опасных файлов.
"""
from fastapi import UploadFile, HTTPException
import magic

# Разрешённые MIME типы для изображений
ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}

# Максимальный размер файла (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


async def validate_image_file(file: UploadFile) -> None:
    """
    Валидирует файл изображения.
    
    Args:
        file: Загружаемый файл
        
    Raises:
        HTTPException: Если файл не проходит валидацию
    """
    # Читаем первые байты для определения MIME типа
    content = await file.read(2048)
    await file.seek(0)  # Возвращаемся в начало файла
    
    # Проверяем MIME тип через magic (по содержимому, не по расширению)
    try:
        mime = magic.from_buffer(content, mime=True)
    except Exception:
        # Fallback: проверяем через content_type из запроса
        mime = file.content_type
    
    if mime not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_file_type",
                "msg": f"Недопустимый тип файла. Разрешены: {', '.join(ALLOWED_IMAGE_MIMES)}",
                "received_mime": mime,
            }
        )
    
    # Проверяем размер файла
    await file.seek(0, 2)  # Переходим в конец файла
    file_size = file.tell()
    await file.seek(0)  # Возвращаемся в начало
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "file_too_large",
                "msg": f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / 1024 / 1024:.1f} MB",
                "file_size_mb": file_size / 1024 / 1024,
            }
        )


async def validate_template_file(file: UploadFile) -> None:
    """
    Валидирует файл шаблона (расширенный набор типов).
    
    Args:
        file: Загружаемый файл
        
    Raises:
        HTTPException: Если файл не проходит валидацию
    """
    # Для шаблонов разрешаем также PDF, JSON, SVG
    allowed_mimes = ALLOWED_IMAGE_MIMES | {
        "application/pdf",
        "application/json",
        "text/plain",
    }
    
    content = await file.read(2048)
    await file.seek(0)
    
    try:
        mime = magic.from_buffer(content, mime=True)
    except Exception:
        mime = file.content_type
    
    if mime not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_file_type",
                "msg": f"Недопустимый тип файла. Разрешены: {', '.join(allowed_mimes)}",
                "received_mime": mime,
            }
        )
    
    # Проверяем размер (шаблоны могут быть больше)
    await file.seek(0, 2)
    file_size = file.tell()
    await file.seek(0)
    
    max_template_size = 50 * 1024 * 1024  # 50 MB для шаблонов
    if file_size > max_template_size:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "file_too_large",
                "msg": f"Файл слишком большой. Максимум: {max_template_size / 1024 / 1024:.1f} MB",
            }
        )
