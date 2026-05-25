import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import requests
from requests.exceptions import ConnectionError
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
            logger.error(
                "Backend request failed: status_code=%d response=%s",
                response.status_code,
                response.text
            )
            messagebox.showerror("Error", response.text)

    except ConnectionError:
        logger.error("Failed to connect to backend at http://127.0.0.1:8000")
        messagebox.showerror(
            "Error de Conexión",
            "No se pudo conectar con el servidor backend.\n\n"
            "Asegurate de que Uvicorn esté corriendo en el puerto 8000."
        )
    except Exception as e:
        logger.error("Exception occurred during text extraction: %s", e, exc_info=True)
        messagebox.showerror("Error", str(e))


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


def cargar_lista_historial(tree):
    logger.debug("Fetching document history from backend")
    for row in tree.get_children():
        tree.delete(row)
    try:
        response = requests.get("http://127.0.0.1:8000/documents?limit=50")
        if response.status_code == 200:
            docs = response.json().get("items", [])
            logger.info("History loaded successfully: %d items retrieved", len(docs))
            for d in docs:
                fecha = d.get("created_at", "")[:16].replace("T", " ")
                tree.insert(
                    "",
                    tk.END,
                    values=(d.get("_id"), d.get("pdf_nombre"), d.get("estado"), fecha)
                )
        else:
            logger.error(
                "Failed to load history: status_code=%d response=%s",
                response.status_code,
                response.text
            )
            messagebox.showerror("Error", "No se pudo cargar el historial.")
    except ConnectionError as e:
        logger.error("Connection error while fetching history: %s", e)
        messagebox.showerror("Error", "Servidor desconectado.")


def ver_texto_historial(tree, ventana_historial):
    global texto_extraido_global
    seleccion = tree.selection()
    if not seleccion:
        logger.warning("Load text attempted but no document selected")
        messagebox.showwarning("Advertencia", "Seleccioná un documento de la lista.")
        return

    doc_id = tree.item(seleccion[0])['values'][0]
    logger.info("Fetching text for document id: %s", doc_id)

    try:
        resp = requests.get(f"http://127.0.0.1:8000/documents/{doc_id}?include_text=true")
        if resp.status_code == 200:
            data = resp.json().get("document", {})
            texto = data.get("txt_contenido", "")

            texto_extraido_global = texto
            texto_resultado.delete("1.0", tk.END)
            texto_resultado.insert(tk.END, texto_extraido_global)

            logger.info("Text successfully loaded into main window for document id: %s", doc_id)
            messagebox.showinfo("Éxito", "Texto cargado en la pantalla principal.")
            ventana_historial.destroy()
        else:
            logger.error(
                "Failed to load document text: status_code=%d response=%s",
                resp.status_code,
                resp.text
            )
            messagebox.showerror("Error", "No se pudo cargar el documento.")
    except ConnectionError as e:
        logger.error("Connection error while fetching document text: %s", e)
        messagebox.showerror("Error", "Servidor desconectado.")


def renombrar_historial(tree):
    seleccion = tree.selection()
    if not seleccion:
        logger.warning("Rename attempted but no document selected")
        messagebox.showwarning("Advertencia", "Seleccioná un documento de la lista.")
        return

    doc_id = tree.item(seleccion[0])['values'][0]
    nombre_actual = tree.item(seleccion[0])['values'][1]

    nuevo_nombre = simpledialog.askstring(
        "Renombrar",
        "Nuevo nombre del PDF:",
        initialvalue=nombre_actual
    )
    
    if nuevo_nombre and nuevo_nombre != nombre_actual:
        logger.info(
            "Attempting to rename document id: %s from '%s' to '%s'",
            doc_id,
            nombre_actual,
            nuevo_nombre
        )
        try:
            resp = requests.patch(
                f"http://127.0.0.1:8000/documents/{doc_id}",
                json={"pdf_nombre": nuevo_nombre}
            )
            if resp.status_code == 200:
                logger.info("Document successfully renamed")
                cargar_lista_historial(tree)
            else:
                logger.error(
                    "Failed to rename document: status_code=%d response=%s",
                    resp.status_code,
                    resp.text
                )
                messagebox.showerror("Error", f"Fallo al renombrar: {resp.json().get('detail')}")
        except ConnectionError as e:
            logger.error("Connection error while renaming document: %s", e)
            messagebox.showerror("Error", "Servidor desconectado.")
    else:
        logger.debug("Rename dialog cancelled by user or name unchanged")


def eliminar_historial(tree):
    seleccion = tree.selection()
    if not seleccion:
        logger.warning("Delete attempted but no document selected")
        messagebox.showwarning("Advertencia", "Seleccioná un documento de la lista.")
        return

    doc_id = tree.item(seleccion[0])['values'][0]
    msg = "¿Seguro que querés eliminar este documento de la base de datos?"
    if messagebox.askyesno("Confirmar", msg):
        logger.info("Attempting to delete document id: %s", doc_id)
        try:
            resp = requests.delete(f"http://127.0.0.1:8000/documents/{doc_id}")
            if resp.status_code == 200:
                logger.info("Document successfully deleted")
                cargar_lista_historial(tree)
            else:
                logger.error(
                    "Failed to delete document: status_code=%d response=%s",
                    resp.status_code,
                    resp.text
                )
                messagebox.showerror("Error", "No se pudo eliminar.")
        except ConnectionError as e:
            logger.error("Connection error while deleting document: %s", e)
            messagebox.showerror("Error", "Servidor desconectado.")
    else:
        logger.debug("Delete confirmation cancelled by user")


# Abrir Ventana de Historial
def abrir_historial():
    logger.info("Opening document history window")
    ventana_historial = tk.Toplevel(ventana)
    ventana_historial.title("Historial de Documentos")
    ventana_historial.geometry("850x400")
    ventana_historial.config(bg="#1e1e1e")

    # Tabla (Treeview)
    columnas = ("ID", "Nombre", "Estado", "Fecha")
    tree = ttk.Treeview(ventana_historial, columns=columnas, show="headings")
    tree.heading("ID", text="ID MongoDB")
    tree.heading("Nombre", text="Nombre del Archivo")
    tree.heading("Estado", text="Estado")
    tree.heading("Fecha", text="Fecha de Creación")

    tree.column("ID", width=200, anchor=tk.CENTER)
    tree.column("Nombre", width=350, anchor=tk.W)
    tree.column("Estado", width=100, anchor=tk.CENTER)
    tree.column("Fecha", width=150, anchor=tk.CENTER)

    tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    panel_botones = tk.Frame(ventana_historial, bg="#1e1e1e")
    panel_botones.pack(pady=10)

    btn_ver = tk.Button(
        panel_botones,
        text="Cargar Texto",
        command=lambda: ver_texto_historial(tree, ventana_historial),
        bg="#2196F3",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_ver.pack(side=tk.LEFT, padx=5)

    btn_renombrar = tk.Button(
        panel_botones,
        text="Renombrar",
        command=lambda: renombrar_historial(tree),
        bg="#FFEB3B",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_renombrar.pack(side=tk.LEFT, padx=5)

    btn_eliminar = tk.Button(
        panel_botones,
        text="Eliminar",
        command=lambda: eliminar_historial(tree),
        bg="#F44336",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_eliminar.pack(side=tk.LEFT, padx=5)

    btn_actualizar = tk.Button(
        panel_botones,
        text="Actualizar Lista",
        command=lambda: cargar_lista_historial(tree),
        bg="#4CAF50",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_actualizar.pack(side=tk.LEFT, padx=5)

    cargar_lista_historial(tree)


# Ventana principal
logger.info("Initializing Extractor PDF Tkinter UI")
ventana = tk.Tk()

ventana.title("Extractor PDF")
ventana.geometry("900x650")
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
    fg="black",
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
    fg="black",
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
    fg="black",
    font=("Arial", 12),
    padx=10,
    pady=5
)

boton_descargar.pack(pady=10)

boton_historial = tk.Button(
    ventana,
    text="Ver Historial",
    command=abrir_historial,
    bg="#9C27B0",
    fg="black",
    font=("Arial", 12),
    padx=10,
    pady=5
)
boton_historial.pack(pady=5)

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
if __name__ == "__main__":
    logger.info("Entering Tkinter main loop")
    ventana.mainloop()
