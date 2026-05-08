"""
Demo Orchestrator para defensa del TFG.
Lanza ataques contra el backend con timings configurables, mientras
Paula juega en Unity en W1. Cerberus captura el tráfico mezclado.

Uso:
    python demo_orchestrator.py --mode demo
    python demo_orchestrator.py --mode fast
    python demo_orchestrator.py --mode loop --interval 45
    python demo_orchestrator.py --mode demo --only bola,bopla
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ATTACKS_DIR = Path(__file__).resolve().parent.parent / "attacks"

ATTACKS = {
    "bola":("BOLA / IDOR ATTACK","bola_attack.py"),
    "bopla":("BOPLA / Mass Assignment","bopla_attack.py"),
    "token":("Weak Token Impersonation","weak_token_impersonation.py"),
    "fraud":("Transaction Fraud","transaction_fraud_attack.py"),
}

# timings por modo (segundos antes de cada ataque y al final)
MODES = {
    "fast":{"pre":0,"between":1,"post":2},
    "demo":{"pre":5,"between":15,"post":10},
    "loop":{"pre":0,"between":8,"post":5},
}


def color(text, code):
    return f"\033[{code}m{text}\033[0m"


def banner(text, char="=", width=70):
    print(color(char * width, "36"))
    print(color(text.center(width), "36;1"))
    print(color(char * width, "36"))


def now():
    return datetime.now().strftime("%H:%M:%S")


def run_attack(key, name, script):
    print()
    print(color(f"[{now()}] >>> Lanzando: {name}", "33;1"))
    print(color(f"           script: {script}", "90"))
    script_path = ATTACKS_DIR / script
    if not script_path.exists():
        print(color(f"[ERROR] No existe {script_path}", "31"))
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ATTACKS_DIR.parent),
            timeout=60,
        )
        ok = result.returncode == 0
        marker = color("[OK]", "32;1") if ok else color("[FAIL]", "31;1")
        print(f"[{now()}] {marker} {name}")
        return ok
    except subprocess.TimeoutExpired:
        print(color(f"[{now()}] [TIMEOUT] {name}", "31"))
        return False


def run_round(selected, timing):
    results = {}
    time.sleep(timing["pre"])
    for key in selected:
        name, script = ATTACKS[key]
        results[key] = run_attack(key, name, script)
        time.sleep(timing["between"])
    time.sleep(timing["post"])
    return results


def print_summary(results):
    print()
    banner("SUMMARY", "=")
    for key, ok in results.items():
        name = ATTACKS[key][0]
        status = color("CONFIRMED", "32;1") if ok else color("FAILED", "31;1")
        print(f"  {name:35} {status}")
    confirmed = sum(1 for v in results.values() if v)
    total = len(results)
    print()
    print(color(f"Confirmed findings: {confirmed}/{total}", "36;1"))
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Demo orchestrator para defensa del TFG"
    )
    parser.add_argument("--mode", choices=["fast", "demo", "loop"], default="demo",
                        help="fast=0s, demo=15s, loop=8s entre ataques")
    parser.add_argument("--only", default="",
                        help="lista separada por comas: bola,bopla,token,fraud")
    parser.add_argument("--interval", type=int, default=30,
                        help="(solo loop) segundos entre rondas")
    parser.add_argument("--rounds", type=int, default=0,
                        help="(solo loop) número de rondas (0 = infinito)")
    args = parser.parse_args()

    if args.only:
        selected = [k.strip() for k in args.only.split(",") if k.strip() in ATTACKS]
        if not selected:
            print(color("[ERROR] --only no contiene ataques válidos.", "31"))
            sys.exit(1)
    else:
        selected = list(ATTACKS.keys())

    timing = MODES[args.mode]

    banner("STEAMWORKS DAST LAB - DEMO ORCHESTRATOR", "=")
    print(f"  Mode:     {args.mode}")
    print(f"  Attacks:  {', '.join(selected)}")
    print(f"  Timing:   pre={timing['pre']}s  between={timing['between']}s  post={timing['post']}s")
    if args.mode == "loop":
        print(f"  Interval: {args.interval}s entre rondas")
        print(f"  Rounds:   {'∞' if args.rounds == 0 else args.rounds}")
    print()

    if args.mode != "loop":
        results = run_round(selected, timing)
        print_summary(results)
        return

    # modo loop: para grabación de demo larga
    round_num = 0
    try:
        while args.rounds == 0 or round_num < args.rounds:
            round_num += 1
            banner(f"ROUND {round_num}", "-")
            results = run_round(selected, timing)
            print_summary(results)
            if args.rounds == 0 or round_num < args.rounds:
                print(color(f"[{now()}] Esperando {args.interval}s para siguiente ronda...", "90"))
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print()
        print(color(f"[{now()}] Demo interrumpida por usuario.", "33"))


if __name__ == "__main__":
    main()