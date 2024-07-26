from aws_lambda_powertools import Logger
from fastapi import APIRouter

from app.jwt_bearer import JWTBearer
from app.services.storage_service import StorageService

logger = Logger(utc=True)

jwt_bearer = JWTBearer()
storage_service = StorageService()
router = APIRouter()
