from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.dependencies import get_rss_service
from app.services.rss_service import RSSService

router = APIRouter()


@router.get("/rss.xml", include_in_schema=False)
def get_rss_feed(
    request: Request,
    rss_service: Annotated[RSSService, Depends(get_rss_service)],
) -> Response:
    return Response(
        content=rss_service.generate_feed(str(request.base_url)),
        media_type="application/rss+xml; charset=utf-8",
    )
