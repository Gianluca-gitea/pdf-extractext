import tkinter as tk
from tkinter import filedialog, messagebox
import requests

archivo_pdf = None
texto_extraido_global = ""

# Seleccionar PDF
def seleccionar_pdf():
    global archivo_pdf

    archivo = filedialog.askopenfilename(
        filetypes=[("PDF Files", "*.pdf")]
    )

    if archivo:
        archivo_pdf = archivo
        label_archivo.config(
            text=f"PDF seleccionado:\n{archivo}"
        )

# Enviar PDF al backend
def extraer_texto():
    global archivo_pdf
    global texto_extraido_global

    if not archivo_pdf:
        messagebox.showwarning(
            "Advertencia",
            "Seleccioná un PDF primero."
        )
        return

    try:
        with open(archivo_pdf, "rb") as pdf:

            files = {
                "file": (
                    "archivo.pdf",
                    pdf,
                    "application/pdf"
                )
            }

            response = requests.post(
                "http://127.0.0.1:8000/documents/upload",
                files=files
            )

        if response.status_code == 200:

            data = response.json()

            texto_extraido_global = data["extracted_text"]

            texto_resultado.delete("1.0", tk.END)

            texto_resultado.insert(
                tk.END,
                texto_extraido_global
            )

        else:
            messagebox.showerror(
                "Error",
                response.text
            )

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

# Descargar TXT
def descargar_txt():

    global texto_extraido_global

    if not texto_extraido_global:

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

        with open(
            archivo_guardado,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(texto_extraido_global)

        messagebox.showinfo(
            "Éxito",
            "TXT descargado correctamente."
        )

# Ventana principal
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
ventana.mainloop()