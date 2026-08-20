from dataclasses import dataclass


@dataclass
class Nombre:
    _nombre: str = ""

    def obtener_nombre(self) -> str:
        return self._nombre

    def establecer_nombre(self, nombre: str) -> None:
        self._nombre = nombre

    def validar_nombre(self) -> bool:
        # TODO: Implementar validación real
        return len(self._nombre) > 0 and len(self._nombre) <= 255
