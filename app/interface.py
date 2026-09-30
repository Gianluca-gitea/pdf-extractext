import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import requests
from requests.exceptions import ConnectionError
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


class ApiClient:
    """Cliente HTTP desacoplado para la API del backend."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def upload(self, file_path: str, filename: str) -> dict:
        with open(file_path, "rb") as pdf:
            files = {"file": (filename, pdf, "application/pdf")}
        response = requests.post(f"{self.base_url}/documents/upload", files=files)
        response.raise_for_status()
        return response.json()

    def list_documents(self, limit: int = 50) -> list:
        response = requests.get(f"{self.base_url}/documents", params={"limit": limit})
        response.raise_for_status()
        return response.json().get("items", [])

    def get_document(self, doc_id: str, include_text: bool = True) -> dict:
        params = {"include_text": "true" if include_text else "false"}
        response = requests.get(f"{self.base_url}/documents/{doc_id}", params=params)
        response.raise_for_status()
        return response.json().get("document", {})

    def patch_document(self, doc_id: str, data: dict) -> dict:
        response = requests.patch(f"{self.base_url}/documents/{doc_id}", json=data)
        response.raise_for_status()
        return response.json()

    def delete_document(self, doc_id: str) -> dict:
        response = requests.delete(f"{self.base_url}/documents/{doc_id}")
        response.raise_for_status()
        return response.json()


# Instancia por defecto (puede ser reemplazada para testing)
api_client = ApiClient()

archivo_pdf = None
texto_extraido_global = ""
ventana = None
label_archivo = None
texto_resultado = None


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
def extraer_texto(client: ApiClient = None):
    global texto_extraido_global
    client = client or api_client

    if not archivo_pdf:
        logger.warning("Extraction attempted but no PDF was selected")
        messagebox.showwarning(
            "Advertencia",
            "Seleccioná un PDF primero."
        )
        return

    logger.info("Starting text extraction process for file: %s", archivo_pdf)

    try:
        filename = os.path.basename(archivo_pdf)
        data = client.upload(archivo_pdf, filename)

        logger.info("Backend request successful (200 OK)")

        texto_extraido_global = data.get("extracted_text", "")
        logger.debug("Received extracted text length=%d", len(texto_extraido_global))

        texto_resultado.delete("1.0", tk.END)
        texto_resultado.insert(tk.END, texto_extraido_global)

    except ConnectionError:
        logger.error("Failed to connect to backend at %s", API_BASE_URL)
        messagebox.showerror(
            "Error de Conexión",
            f"No se pudo conectar con el servidor backend en {API_BASE_URL}.\n\n"
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


def cargar_lista_historial(tree, client: ApiClient = None):
    client = client or api_client
    logger.debug("Fetching document history from backend")
    for row in tree.get_children():
        tree.delete(row)
    try:
        docs = client.list_documents(limit=50)
        logger.info("History loaded successfully: %d items retrieved", len(docs))
        for d in docs:
            fecha = d.get("created_at", "")[:16].replace("T", " ")
            tree.insert(
                "",
                tk.END,
                values=(d.get("_id"), d.get("pdf_nombre"), d.get("estado"), fecha)
            )
    except ConnectionError as e:
        logger.error("Connection error while fetching history: %s", e)
        messagebox.showerror("Error", "Servidor desconectado.")
    except Exception as e:
        logger.error("Failed to load history: %s", e)
        messagebox.showerror("Error", "No se pudo cargar el historial.")


def _get_selected_document(tree) -> str | None:
    seleccion = tree.selection()
    if not seleccion:
        logger.warning("Action attempted but no document selected")
        messagebox.showwarning("Advertencia", "Seleccioná un documento de la lista.")
        return None
    return tree.item(seleccion[0])['values'][0]


def ver_texto_historial(tree, ventana_historial, client: ApiClient = None):
    client = client or api_client
    global texto_extraido_global
    doc_id = _get_selected_document(tree)
    if doc_id is None:
        return
    logger.info("Fetching text for document id: %s", doc_id)

    try:
        data = client.get_document(doc_id, include_text=True)
        texto = data.get("txt_contenido", "")

        texto_extraido_global = texto
        texto_resultado.delete("1.0", tk.END)
        texto_resultado.insert(tk.END, texto_extraido_global)

        logger.info("Text successfully loaded into main window for document id: %s", doc_id)
        messagebox.showinfo("Éxito", "Texto cargado en la pantalla principal.")
        ventana_historial.destroy()
    except ConnectionError as e:
        logger.error("Connection error while fetching document text: %s", e)
        messagebox.showerror("Error", "Servidor desconectado.")
    except Exception as e:
        logger.error("Failed to load document text: %s", e)
        messagebox.showerror("Error", "No se pudo cargar el documento.")


def renombrar_historial(tree, client: ApiClient = None):
    client = client or api_client
    doc_id = _get_selected_document(tree)
    if doc_id is None:
        return

    seleccion = tree.selection()
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
            client.patch_document(doc_id, {"pdf_nombre": nuevo_nombre})
            logger.info("Document successfully renamed")
            cargar_lista_historial(tree, client)
        except ConnectionError as e:
            logger.error("Connection error while renaming document: %s", e)
            messagebox.showerror("Error", "Servidor desconectado.")
        except Exception as e:
            logger.error("Failed to rename document: %s", e)
            messagebox.showerror("Error", f"Fallo al renombrar: {e}")
    else:
        logger.debug("Rename dialog cancelled by user or name unchanged")


def eliminar_historial(tree, client: ApiClient = None):
    client = client or api_client
    doc_id = _get_selected_document(tree)
    if doc_id is None:
        return
    msg = "¿Seguro que querés eliminar este documento de la base de datos?"
    if messagebox.askyesno("Confirmar", msg):
        logger.info("Attempting to delete document id: %s", doc_id)
        try:
            client.delete_document(doc_id)
            logger.info("Document successfully deleted")
            global texto_extraido_global
            texto_extraido_global = ""
            texto_resultado.delete("1.0", tk.END)
            cargar_lista_historial(tree, client)
        except ConnectionError as e:
            logger.error("Connection error while deleting document: %s", e)
            messagebox.showerror("Error", "Servidor desconectado.")
        except Exception as e:
            logger.error("Failed to delete document: %s", e)
            messagebox.showerror("Error", "No se pudo eliminar.")
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
        command=lambda: ver_texto_historial(tree, ventana_historial, api_client),
        bg="#2196F3",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_ver.pack(side=tk.LEFT, padx=5)

    btn_renombrar = tk.Button(
        panel_botones,
        text="Renombrar",
        command=lambda: renombrar_historial(tree, api_client),
        bg="#FFEB3B",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_renombrar.pack(side=tk.LEFT, padx=5)

    btn_eliminar = tk.Button(
        panel_botones,
        text="Eliminar",
        command=lambda: eliminar_historial(tree, api_client),
        bg="#F44336",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_eliminar.pack(side=tk.LEFT, padx=5)

    btn_actualizar = tk.Button(
        panel_botones,
        text="Actualizar Lista",
        command=lambda: cargar_lista_historial(tree, api_client),
        bg="#4CAF50",
        fg="black",
        font=("Arial", 10, "bold")
    )
    btn_actualizar.pack(side=tk.LEFT, padx=5)

    cargar_lista_historial(tree, api_client)


# Ejecutar ventana
if __name__ == "__main__":
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
        command=lambda: extraer_texto(api_client),
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

    logger.info("Entering Tkinter main loop")
    ventana.mainloop()
