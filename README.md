# PDF Extract Text

## Descripción
Este proyecto fue desarrollado con el objetivo de extraer texto de archivos de una forma automática. 
La idea surge para tener que evitarnos estar copiando contenido de una forma manual, facilitando así de una forma sencilla el procesamiento de documentos

## Objetivos
Nuestro objetivo es desarrollar una herramienta simple y funcional que permita procesar archivos PDF y obtener su contenido de forma rápida y eficiente.

## Funcionalidades
- Permite extraer texto desde archivos pdf
- Facilita el manejo de informacion contenida en documentos

## Arquitectura
Nuestro proyecto se organiza en capas para separar las responsabilidades y facilitar su mantenimiento.

### Capa de Presentación
Se encarga de ejecutar el programa y recibir el archivo PDF que se desea procesar.
Responsabilidades:
- Ejecutar el programa
- Recibir el archivo PDF a procesar
- Iniciar la extracción de texto

### Capa de Lógica
Contiene las funciones encargadas de procesar el PDF y extraer el texto.
Responsabilidades:
- Procesar el archivo PDF
- Extraer el texto
- Realizar transformaciones necesarias sobre los datos

### Capa de Datos
Está pensada para:
- Almacenar el texto extraído
- Permitir la reutilización de la información
- Integrarse con una base de datos en futuras versiones

## Estructura

## Tecnologias usadas
- Python
lenguaje principal de desarrollo
- OpenCode
herramienta de apoyo en el desarrollo del proyecto 
- UV 
gestión de dependencias y entorno del proyecto  
-MongoDB
base de datos planificada para futuras mejoras

## Uso 
Para ejecutar el programa, se debe correr el archivo principal pasando como parámetro el PDF que deseamos procesar:

```bash
python aplicación/main.py archivo.pdf
