import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

archivo_pdf = None
texto_extraido_global = ""


# Seleccionar PDF
def seleccionar_pdf():
    global archivo_pdf

    archivo = filedialog.askopenfilename(
        filetypes=[("PDF Files", "*.pdf")]
    )

    if archivo:
        logger.info("PDF file selected via UI: %s", archivo)
        archivo_pdf = archivo
        label_archivo.config(
            text=f"PDF seleccionado:\n{archivo}"
        )
    else:
        logger.debug("PDF file selection cancelled by user")


# Enviar PDF al backend
def extraer_texto():
    global texto_extraido_global

    if not archivo_pdf:
        logger.warning("Extraction attempted but no PDF was selected")
        messagebox.showwarning(
            "Advertencia",
            "Seleccioná un PDF primero."
        )
        return

    logger.info("Starting text extraction process for file: %s", archivo_pdf)

    try:
        with open(archivo_pdf, "rb") as pdf:
            files = {
                "file": (
                    "archivo.pdf",
                    pdf,
                    "application/pdf"
                )
            }

            logger.debug("Sending POST request to /documents/upload")
            response = requests.post(
                "http://127.0.0.1:8000/documents/upload",
                files=files
            )

        if response.status_code == 200:
            logger.info("Backend request successful (200 OK)")
            data = response.json()

            texto_extraido_global = data.get("extracted_text", "")
            logger.debug("Received extracted text length=%d", len(texto_extraido_global))

            texto_resultado.delete("1.0", tk.END)
            texto_resultado.insert(tk.END, texto_extraido_global)

        else:
            logger.error("Backend request failed: status_code=%d response=%s", response.status_code, response.text)
            messagebox.showerror(
                "Error",
                response.text
            )

    except Exception as e:
        logger.error("Exception occurred during text extraction: %s", e, exc_info=True)
        messagebox.showerror(
            "Error",
            str(e)
        )


# Descargar TXT
def descargar_txt():

    if not texto_extraido_global:
        logger.warning("TXT download attempted but no text is available in memory")
        messagebox.showwarning(
            "Advertencia",
            "No hay texto para descargar."
        )
        return

    archivo_guardado = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt")],
        title="Guardar TXT"
    )

    if archivo_guardado:
        logger.info("Saving extracted text to local path: %s", archivo_guardado)
        try:
            with open(
                archivo_guardado,
                "w",
                encoding="utf-8"
            ) as file:
                file.write(texto_extraido_global)

            logger.info("TXT file successfully saved")
            messagebox.showinfo(
                "Éxito",
                "TXT descargado correctamente."
            )
        except Exception as e:
            logger.error("Failed to write TXT file to disk: %s", e, exc_info=True)
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    else:
        logger.debug("TXT save dialog cancelled by user")


# Ventana principal
logger.info("Initializing Extractor PDF Tkinter UI")
ventana = tk.Tk()

ventana.title("Extractor PDF")
ventana.geometry("900x600")
ventana.config(bg="#1e1e1e")

# Título
titulo = tk.Label(
    ventana,
    text="Extractor de PDF",
    font=("Arial", 24, "bold"),
    bg="#1e1e1e",
    fg="white"
)

titulo.pack(pady=20)

# Botón seleccionar PDF
boton_pdf = tk.Button(
    ventana,
    text="Seleccionar PDF",
    command=seleccionar_pdf,
    bg="#4CAF50",
    fg="white",
    font=("Arial", 12),
    padx=10,
    pady=5
)

boton_pdf.pack(pady=10)

# Label PDF seleccionado
label_archivo = tk.Label(
    ventana,
    text="Ningún PDF seleccionado",
    bg="#1e1e1e",
    fg="white",
    font=("Arial", 10)
)

label_archivo.pack(pady=10)

# Botón extraer texto
boton_extraer = tk.Button(
    ventana,
    text="Extraer Texto",
    command=extraer_texto,
    bg="#2196F3",
    fg="white",
    font=("Arial", 12),
    padx=10,
    pady=5
)

boton_extraer.pack(pady=10)

# Botón descargar TXT
boton_descargar = tk.Button(
    ventana,
    text="Descargar TXT",
    command=descargar_txt,
    bg="#FF9800",
    fg="white",
    font=("Arial", 12),
    padx=10,
    pady=5
)

boton_descargar.pack(pady=10)

# Área de texto
texto_resultado = tk.Text(
    ventana,
    wrap="word",
    font=("Arial", 11),
    bg="#2d2d2d",
    fg="white"
)

texto_resultado.pack(
    padx=20,
    pady=20,
    fill="both",
    expand=True
)

# Ejecutar ventana
logger.info("Entering Tkinter main loop")
ventana.mainloop()
