import os
import logging
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, NoResultFound
import asyncio

try:
    from app.s3.s3 import S3ClientError
except Exception:
    class S3ClientError(Exception):
        pass

DEBUG = str(os.getenv("DEBUG", "")).lower() in {"1", "true", "yes"}


def short_error(msg: str, code: str):
    data = {"error": code, "msg": msg}
    if DEBUG:
        data["debug"] = True
    return data


def handle_error(exc: Exception, logger: logging.Logger, context: str = "") -> HTTPException:
    """Приводит любое исключение к короткому HTTPException"""
    logger.exception("Ошибка в [%s]: %s", context, exc)

    if isinstance(exc, HTTPException):
        # нормализуем формат detail
        if isinstance(exc.detail, dict):
            return exc
        return HTTPException(status_code=exc.status_code, detail=short_error(str(exc.detail), "request_error"))

    if isinstance(exc, ValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=short_error("Ошибка валидации данных", "validation_error"))

    if isinstance(exc, NoResultFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=short_error("Не найдено", "not_found"))

    if isinstance(exc, IntegrityError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT,
                             detail=short_error("Конфликт данных", "conflict"))

    if isinstance(exc, SQLAlchemyError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail=short_error("Ошибка базы данных", "db_error"))

    if isinstance(exc, S3ClientError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                             detail=short_error("Ошибка S3", "s3_error"))

    if isinstance(exc, (OSError, IOError)):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                             detail=short_error("Ошибка файловой системы", "fs_error"))

    if isinstance(exc, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail=short_error("Недостаточно прав", "forbidden"))

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                             detail=short_error("Таймаут операции", "timeout"))

    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=short_error(str(exc), "bad_request"))

    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                         detail=short_error("Внутренняя ошибка сервера", "server_error"))
