import base64
import json
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


bearer_scheme = HTTPBearer()


def create_demo_token(user_id: str, steam_id: str) -> str:
    #este token es debil a proposito: solo guarda datos en json
    payload = {
        "user_id": user_id,
        "steam_id": steam_id
    }

    #lo paso a base64 para que parezca un token, pero no tiene firma ni caducidad
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def decode_demo_token(token: str) -> dict:
    try:
        #deshago el base64 y vuelvo a sacar el json
        raw = base64.urlsafe_b64decode(token.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_identity(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    #solo acepto el formato authorization: bearer <token>
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")

    #devuelvo la identidad que viene dentro del token
    return decode_demo_token(credentials.credentials)
