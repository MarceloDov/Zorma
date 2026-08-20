# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

## [0.1.0] - 2026-08-20

### Added
- Primer commit del proyecto: clasificador automático de archivos de escritorio.
- Mejoras en el manejo de eventos y filtros del sistema de vigilancia de archivos.
- Animación de navegación y mejor visibilidad de widgets en la interfaz.
- Integración de CI/CD.

### Changed
- Refactorización de pruebas para usar ZormaRepository y mejorar estructura general.
- Refactorización de componentes de la UI para usar nombres de objetos y propiedades de estilo.
- Refactorización del dominio a nomenclatura en español, reforzando robustez.
- Simplificación del dominio e identidad visual del dashboard.
- Traducción de la API interna a español e integración del sistema de diseño.
- Renombrado de clases y archivos a español (adapters, core/models, ui/), manteniendo préstamos deliberados (PyQt, Watchdog, Zorma, ViewModel).

### Fixed
- Restauración de la herencia `Archivo(Nombre, Extension)`.
- Corrección de contraste WCAG AA (4.5:1) en el tema claro: se agrega token `text_on_primary` por tema y se oscurecen `text_muted` y `border`.
