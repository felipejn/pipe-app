import secrets
import string
import math
from app.passwords.wordlist import PALAVRAS


def _forca(password: str) -> tuple[int, str]:
    charset = 0
    if any(c.islower() for c in password):
        charset += 26
    if any(c.isupper() for c in password):
        charset += 26
    if any(c.isdigit() for c in password):
        charset += 10
    if any(c in string.punctuation for c in password):
        charset += 32
    if charset == 0:
        return 0, "Sem força"
    entropia = len(password) * math.log2(charset)
    if entropia < 28:
        return 1, "Muito fraca"
    if entropia < 36:
        return 2, "Fraca"
    if entropia < 60:
        return 3, "Boa"
    if entropia < 80:
        return 4, "Forte"
    return 5, "Muito forte"


AMBIGUOS = set("0Ol1I")


def gerar_password(comprimento: int, maiusculas: bool, minusculas: bool,
                   numeros: bool, simbolos: bool, excluir_ambiguos: bool) -> dict:
    alfabeto = ""
    if maiusculas:
        alfabeto += string.ascii_uppercase
    if minusculas:
        alfabeto += string.ascii_lowercase
    if numeros:
        alfabeto += string.digits
    if simbolos:
        alfabeto += "!@#$%^&*()-_=+[]{}|;:,.<>?"
    if not alfabeto:
        alfabeto = string.ascii_letters + string.digits
    if excluir_ambiguos:
        alfabeto = "".join(c for c in alfabeto if c not in AMBIGUOS)
    if not alfabeto:
        alfabeto = string.ascii_letters

    pw = "".join(secrets.choice(alfabeto) for _ in range(comprimento))
    score, label = _forca(pw)
    return {"valor": pw, "forca_score": score, "forca_label": label}


def gerar_passphrase(num_palavras: int) -> dict:
    palavras = [secrets.choice(PALAVRAS) for _ in range(num_palavras)]
    pp = "-".join(palavras)
    score, label = _forca(pp)
    return {"valor": pp, "forca_score": score, "forca_label": label}


def gerar_pin(comprimento: int) -> dict:
    pin = "".join(secrets.choice(string.digits) for _ in range(comprimento))
    return {"valor": pin, "forca_score": 0, "forca_label": "—"}
