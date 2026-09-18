import json, logging, sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Id da requisição em andamento: entra em toda linha de log emitida durante ela (inclusive nas threads do FastAPI).
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

class JsonFormatter(logging.Formatter):
    # Uma linha JSON por evento: dá para filtrar por request_id/job_id, e quebras de linha em valores
    # saem escapadas, então não há como forjar linhas de log.
    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "service": "api",
            "msg": record.getMessage(),
        }
        if request_id := request_id_var.get():
            entry["request_id"] = request_id
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)

def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    # Os logs do uvicorn saem no mesmo formato. uvicorn.access fica como o --no-access-log deixou (desligado):
    # propagá-lo para a raiz reativaria o log de acesso dele, duplicando o de main.py.
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

logger = logging.getLogger("relay")

def log(msg: str, level: int = logging.INFO, exc_info=None, **fields):
    logger.log(level, msg, exc_info=exc_info, extra={"fields": fields})
