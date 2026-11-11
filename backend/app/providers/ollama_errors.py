"""Ollama provider failures — never silently swapped for mock heuristics."""


class OllamaProviderError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
