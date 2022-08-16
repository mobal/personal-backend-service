from aws_lambda_powertools import Logger, Tracer, Metrics

from app.settings import Settings

settings = Settings()

# Logging
logger = Logger(service=settings.app_name)
# Tracing
tracer = Tracer()
# Metrics
metrics = Metrics(namespace='personal', service=settings.app_name)
metrics.set_default_dimensions(environment=settings.app_stage)
