"""Workers package — procesos background asíncronos.

Cada worker es un módulo invocable como ``python -m workers.<nombre>``
que corre su propio loop asyncio con polling periódico.
"""
