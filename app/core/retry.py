"""Retry com backoff exponencial para chamadas a APIs externas.

Uso:
    @retry(times=3, exceptions=(ConnectionError, TimeoutError))
    def chamada_externa(): ...
"""
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class RetryExhaustedError(Exception):
    """Todas as tentativas falharam."""

    def __init__(self, func_name: str, last_error: Exception) -> None:
        self.func_name = func_name
        self.last_error = last_error
        super().__init__(f"{func_name} falhou após todas as tentativas: {last_error}")


def retry(times: int = 3, backoff: float = 2.0, initial_delay: float = 1.0,
          exceptions: tuple[type[Exception], ...] = (Exception,),
          log=None) -> Callable[[F], F]:
    """Decorador de retry com backoff exponencial (1s, 2s, 4s, ...).

    `exceptions` limita quais erros são re-tentáveis (ex.: erros de rede/transientes).
    Outras exceções (ex.: credenciais inválidas) propagam imediatamente.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_error: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    if attempt == times:
                        break
                    if log:
                        log.warning(
                            "%s falhou (tentativa %d/%d): %s — retry em %.1fs",
                            func.__name__, attempt, times, exc, delay,
                        )
                    time.sleep(delay)
                    delay *= backoff
            raise RetryExhaustedError(func.__name__, last_error or Exception("desconhecido")) from last_error
        return wrapper  # type: ignore[return-value]
    return decorator
