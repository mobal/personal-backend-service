from app.models.camel_model import CamelModel


class CreateAttachment(CamelModel):
    name: str
    data: str
