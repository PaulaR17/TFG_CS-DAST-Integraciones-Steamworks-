import json
from datetime import datetime


LOG_FILE = "/app/audit_logs.jsonl"


def write_audit_log(event_type: str, data: dict):
    #monto un evento simple con fecha, tipo y los datos extra que me pasen
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        **data
    }

    #lo guardo como jsonl, o sea, un json por linea
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")
