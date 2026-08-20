from dataclasses import dataclass


@dataclass
class Extension:
    _extension: str = ""

    def obtener_extension(self) -> str:
        return self._extension.lower()

    def establecer_extension(self, extension: str) -> None:
        self._extension = extension.lower()

    def es_extension_valida(self) -> bool:
        return self._extension.startswith(".") or self._extension == ""

    def normalizar(self) -> str:
        ext = self._extension.lower()
        if ext and not ext.startswith("."):
            ext = "." + ext
        self._extension = ext
        return ext
