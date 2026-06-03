"""PII masking utilities (C-07).

Funciones para enmascarar datos sensibles antes de exponerlos en
respuestas HTTP o logs.  Cada funcion es pura y deterministica.

Patrones de enmascaramiento:
  - email:      ``"j***@example.com"``
  - dni:        ``"*****1234"``
  - cuil:       ``"*****5678-9"``
  - cbu:        ``"*****8901"``
  - alias_cbu:  ``"j***"`` (primer caracter + ``***``)
"""

from __future__ import annotations

from typing import Optional


def mask_email(email: str) -> str:
    """Enmascara un email mostrando solo la primera letra y el dominio.

    Args:
        email: Email a enmascarar.

    Returns:
        Email enmascarado, ej: ``"j***@example.com"``.

    Raises:
        ValueError: Si el email está vacío.
    """
    if not email:
        raise ValueError("email vacío")
    parts = email.split("@", 1)
    local = parts[0]
    domain = parts[1] if len(parts) > 1 else ""
    return f"{local[0]}***@{domain}"


def mask_dni(dni: Optional[str]) -> Optional[str]:
    """Enmascara un DNI mostrando solo los ultimos 4 digitos.

    Args:
        dni: DNI a enmascarar o None.

    Returns:
        DNI enmascarado, ej: ``"*****1234"``, o None/"".
    """
    if dni is None:
        return None
    if not dni:
        return ""
    return f"*****{dni[-4:]}"


def mask_cuil(cuil: Optional[str]) -> Optional[str]:
    """Enmascara un CUIL mostrando solo los ultimos 4 digitos
    y el digito verificador.

    Args:
        cuil: CUIL a enmascarar o None.

    Returns:
        CUIL enmascarado, ej: ``"*****5678-9"``, o None.
    """
    if cuil is None:
        return None
    # Si tiene formato XX-XXXXXXXX-X, preservar el ultimo segmento
    if "-" in cuil:
        parts = cuil.split("-")
        # parts[1] es el numero central
        last_four = parts[1][-4:] if len(parts[1]) >= 4 else parts[1]
        suffix = f"-{parts[-1]}" if len(parts) > 2 else ""
        return f"*****{last_four}{suffix}"
    # Sin separadores — formato XXNNNNNNNNK (11 chars)
    # Mostrar ultimos 4 del cuerpo + digito verificador
    if len(cuil) >= 5:
        return f"*****{cuil[-5:]}"
    return f"*****{cuil}"


def mask_cbu(cbu: Optional[str]) -> Optional[str]:
    """Enmascara un CBU mostrando solo los ultimos 4 digitos.

    Args:
        cbu: CBU a enmascarar o None.

    Returns:
        CBU enmascarado, ej: ``"*****8901"``, o None.
    """
    if cbu is None:
        return None
    return f"*****{cbu[-4:]}"


def mask_alias_cbu(alias: Optional[str]) -> Optional[str]:
    """Enmascara un alias de CBU mostrando solo la primera letra.

    Args:
        alias: Alias a enmascarar o None.

    Returns:
        Alias enmascarado, ej: ``"j***"``, o None.
    """
    if alias is None:
        return None
    if not alias:
        return ""
    return f"{alias[0]}***"
