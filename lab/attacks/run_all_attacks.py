from bola_attack import run_bola_attack
from bopla_attack import run_bopla_attack
from weak_token_impersonation import run_weak_token_impersonation_attack
from transaction_fraud_attack import run_transaction_fraud_attack
from common import print_title


def main() -> None:
    """
    lanza todos los ataques del laboratorio de una vez.

    asi no tengo que ir ejecutando cada archivo a mano.
    """

    print_title("STEAMWORKS DAST LAB - AUTOMATED ATTACK SUITE")

    #ejecuto cada ataque y guardo si ha confirmado el fallo o no
    results = {
        "BOLA / IDOR": run_bola_attack(),
        "BOPLA / Mass Assignment": run_bopla_attack(),
        "Weak Token Impersonation": run_weak_token_impersonation_attack(),
        "Transaction Fraud": run_transaction_fraud_attack()
    }

    print_title("SUMMARY")

    #imprimo el resultado de cada ataque
    for attack_name, success in results.items():
        status = "CONFIRMED" if success else "NOT CONFIRMED"
        print(f"{attack_name}: {status}")

    #cuento cuantos han salido confirmados en total
    confirmed_count = sum(1 for success in results.values() if success)

    print()
    print(f"Confirmed findings: {confirmed_count}/{len(results)}")


if __name__ == "__main__":
    main()
