"""Módulo de criptografia para o cofre de passwords.

Utiliza AES-256-GCM para encriptação simétrica e PBKDF2-SHA256
para derivação de chave a partir da password mestra.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import bcrypt


def gerar_salt() -> str:
    """Gera um salt aleatório de 32 bytes, devolvido como base64."""
    return base64.b64encode(os.urandom(32)).decode('utf-8')


def derivar_chave(password: str, salt: str, iterations: int = 600000) -> bytes:
    """Deriva uma chave AES-256 a partir da password e salt usando PBKDF2-SHA256."""
    salt_bytes = base64.b64decode(salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=iterations,
    )
    return kdf.derive(password.encode('utf-8'))


def hash_password_mestre(password: str) -> str:
    """Gera um hash bcrypt da password mestra para verificação."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verificar_password_mestre(password: str, hash_str: str) -> bool:
    """Verifica se a password corresponde ao hash bcrypt."""
    return bcrypt.checkpw(password.encode('utf-8'), hash_str.encode('utf-8'))


def cifrar(chave: bytes, texto: str) -> tuple[bytes, bytes, bytes]:
    """Encripta texto com AES-256-GCM.

    Devolve (ciphertext, iv, tag) — nonce de 12 bytes (96-bit).
    """
    aesgcm = AESGCM(chave)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, texto.encode('utf-8'), None)
    # AESGCM retorna ciphertext+tag concatenados
    tag = ciphertext[-16:]
    data = ciphertext[:-16]
    return data, iv, tag


def decifrar(chave: bytes, ciphertext: bytes, iv: bytes, tag: bytes) -> str:
    """Desencripta texto com AES-256-GCM."""
    aesgcm = AESGCM(chave)
    full = ciphertext + tag
    plaintext = aesgcm.decrypt(iv, full, None)
    return plaintext.decode('utf-8')


def bytes_para_b64(data: bytes) -> str:
    """Converte bytes para base64 string."""
    return base64.b64encode(data).decode('utf-8')


def b64_para_bytes(data: str) -> bytes:
    """Converte base64 string para bytes."""
    return base64.b64decode(data)


