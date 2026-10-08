# IA Director Core

[English](README.md) · **Español**

IA Director Core es un núcleo experimental e independiente del proveedor para convertir una intención humana en ejecución acotada con autorización, verificación y evidencia.

El software actual puede:

- representar resultados, criterios de aceptación, objetivos, efectos, destinos de datos y restricciones de riesgo y costo;
- descubrir y evaluar capacidades de forma acotada;
- mantener separadas la autorización humana y la selección de capacidades;
- vincular la ejecución con la capacidad, el objetivo, los efectos, los destinos y el riesgo autorizados;
- exigir aprobación vinculada a la acción para operaciones de riesgo material;
- ejecutar procesos locales sin interpolación de shell y con límites de tiempo y salida;
- verificar resultados acotados independientemente del éxito de la ejecución;
- minimizar la persistencia de cargas y resultados sin procesar;
- conservar el estado de una ejecución interrumpida sin reportarla silenciosamente como completada.

Requiere Python 3.11 o superior y no tiene dependencias de ejecución de terceros.

## Instalación

Clona el repositorio y usa un entorno aislado de Python.

### Windows

```powershell
git clone https://github.com/Luguisaca/ia-director-core.git
cd ia-director-core
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-deps .
```

En Windows **no necesitas activar el entorno virtual**. Los comandos documentados llaman directamente a los ejecutables dentro de `.venv`, así que no es necesario cambiar la política de ejecución de PowerShell. Si `Activate.ps1` aparece bloqueado, omite la activación y continúa con los comandos directos `.venv\Scripts\...` indicados abajo. No deshabilites ni debilites la política de ejecución del equipo solo para ejecutar IA Director.

### Ubuntu / Debian

```sh
git clone https://github.com/Luguisaca/ia-director-core.git
cd ia-director-core
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps .
```

La instalación en un entorno virtual requiere que el sistema operativo proporcione soporte para `venv` y pip.

## Verificar la instalación

En Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

En Ubuntu / Debian, con el entorno virtual activado:

```sh
python -m unittest discover -s tests -v
```

La suite de pruebas del repositorio es la línea base ejecutable de regresión. Que pase demuestra únicamente las propiedades cubiertas por esas pruebas; no constituye una certificación de seguridad, privacidad, cumplimiento ni preparación para producción.

## Entrada por intención

Ejecuta IA Director indicando el resultado que quieres:

```powershell
.\.venv\Scripts\ia-director.exe "Créame una aplicación pequeña que haga X"
```

La CLI solicita únicamente la autoridad que realmente necesita: modificar el proyecto local, adquirir herramientas persistentes cuando no exista un runtime de desarrollo compatible, autenticar al proveedor cuando corresponda y permitir el uso de los datos necesarios por ese proveedor.

En hosts Windows compatibles puede usar Windows Package Manager para adquirir Node.js si falta y npm para adquirir el adaptador Codex actualmente demostrado, siempre después de una aprobación explícita. La autenticación sigue siendo una acción bajo autoridad humana.

Una ejecución de desarrollo verificada por máquina alcanza `HUMAN_TEST_PENDING`. Eso significa que la solución generada está lista para que una persona pruebe su utilidad; no significa que IA Director ni el producto generado sean, de forma general, seguros, conformes o aptos para producción.

El adaptador de runtime es reemplazable. Codex es el adaptador de desarrollo demostrado actualmente, no una dependencia arquitectónica. Si no existe una ruta de adquisición compatible, el software falla de forma cerrada en lugar de inventar capacidad.

Para ejecutar la demostración determinista anterior del núcleo, usa `--legacy-demo` junto con sus argumentos explícitos de alcance y riesgo.

## Límite del piloto demostrado

Un piloto real y acotado demostró que la entrada por intención actual puede seleccionar el adaptador de desarrollo Codex disponible sin que quien llama prescriba ese adaptador, producir una pequeña aplicación local de tareas, preservar efectos observables después de que el proveedor superara su límite de ejecución de 180 segundos, volver a verificar independientemente el workspace resultante y alcanzar `HUMAN_TEST_PENDING` mediante reconciliación fail-closed. La prueba humana de utilidad de esa aplicación concreta fue positiva.

Esto constituye evidencia de **un caso acotado de desarrollo de software**; no demuestra autonomía general, independencia práctica de proveedor, preparación para producción ni soporte universal de tareas. Los resultados de validación de otras versiones no demuestran el comportamiento de esta versión. Valida el software en el entorno objetivo antes de depender de él.

## Seguridad y aseguramiento

El software es experimental. No infieras autorización a partir del acceso técnico, los metadatos de una capacidad o la salida de un modelo/herramienta. No lo uses para cargas privilegiadas, destructivas, remotas o sensibles sin validar por separado los controles aplicables al entorno.

Consulta `docs/ASSURANCE.md` para conocer los límites públicos de aseguramiento vigentes.

## Licencia

IA Director Core se distribuye bajo **PolyForm Noncommercial License 1.0.0** (`PolyForm-Noncommercial-1.0.0`).

Aviso requerido: Copyright 2026 Luis Salamanca / LUGUISACA

El uso, modificación y distribución no comerciales están sujetos a los términos de la licencia. Esta licencia pública no concede uso comercial. Consulta `LICENSE`.
