import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class LangfuseClient:
    @classmethod
    def connect(cls):
        """Returns a Langfuse client or None if keys are not configured."""
        if not (settings.langfuse_public_key and settings.langfuse_secret_key):
            return None
        try:
            from langfuse import Langfuse
            client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            logger.info("Langfuse client connected (host=%s)", settings.langfuse_host)
            return client
        except Exception:
            logger.warning("Langfuse init failed — tracing disabled", exc_info=True)
            return None
