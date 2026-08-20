# Zorma

Clasificador automático de archivos con interfaz gráfica (PyQt6) y monitorización en tiempo real vía watchdog.

## Características

- **Monitor en segundo plano** — observa carpetas y clasifica archivos automáticamente al crearse.
- **Reglas por extensión, tamaño, fecha o nombre** — cada archivo se mueve, copia o renombra según la regla que coincida.
- **Interfaz gráfica** — dashboard, vista de reglas, historial de clasificación, vista previa y resolución de conflictos.
- **Tema oscuro y claro** — oscuro con paleta Catppuccin, claro siguiendo el sistema de diseño del proyecto ([DESING.md](DESING.md)), toggle en la barra superior.
- **Deshacer/Rehacer** — permite revertir y reaplicar clasificaciones.

## Descargar

La última versión compilada para Windows (`.exe`, no requiere Python instalado) está en [Releases](https://github.com/MarceloDov/Zorma/releases).

## Requisitos (desarrollo)

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) como gestor de paquetes

## Instalación

```bash
git clone https://github.com/MarceloDov/Zorma.git
cd Zorma
uv sync --all-extras
```

## Uso

```bash
uv run python -m zorma
```

## Generar el ejecutable

```bash
uv run pyinstaller --noconfirm zorma.spec
```

Genera `dist/zorma/zorma.exe`. Ver [AGENTS.md](AGENTS.md) para más comandos (lint, type check, build).

## Estructura

```text
src/zorma/
├── __main__.py        # Punto de entrada
├── core/               # Lógica de dominio: modelos, servicios
├── adapters/           # Implementaciones concretas (persistencia JSON, watchdog, notificaciones)
├── ui/                 # Interfaz gráfica (PyQt6)
└── config/             # Configuración global
```

## Tests

```bash
uv run pytest -q
```

## Licencia

MIT
