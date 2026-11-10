"""Aplicación de escritorio para los servicios existentes de PDF Extractext."""

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from api_client import ApiClient, ApiError
from app_settings import load_settings, save_settings

logger = logging.getLogger(__name__)
PAGE_SIZE = 20


class PDFExtractApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings["theme"])
        ctk.set_default_color_theme("blue")
        self.title("PDF Extractext")
        self.geometry("1180x760")
        self.minsize(900, 620)
        self.selected_file = None
        self.result_source = None
        self.result_format = None
        self.busy = False
        self.jobs = queue.Queue()
        self.history_offset = 0
        self.history_items = []
        self.selected_id = None
        self.selected_name = None
        self._build_layout()
        self.show_page("extract")
        self.after(80, self._poll_jobs)

    def api(self):
        return ApiClient(self.settings["extract_url"], self.settings["documents_url"])

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        side = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=("#eef2f7", "#151a24"))
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkLabel(
            side, text="PDF", font=ctk.CTkFont(size=28, weight="bold"), text_color="#3b82f6"
        ).pack(anchor="w", padx=24, pady=(32, 0))
        ctk.CTkLabel(side, text="EXTRACTEXT", font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=24
        )
        ctk.CTkLabel(
            side, text="Tu espacio de documentos", text_color="gray", font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=24, pady=(3, 36))
        self.nav = {}
        for key, label in [
            ("extract", "  Extraer texto"),
            ("history", "  Historial"),
            ("settings", "  Configuración"),
        ]:
            button = ctk.CTkButton(
                side,
                text=label,
                anchor="w",
                height=42,
                corner_radius=9,
                fg_color="transparent",
                text_color=("#273449", "#e4eaf3"),
                hover_color=("#dbeafe", "#23324a"),
                command=lambda k=key: self.show_page(k),
            )
            button.pack(fill="x", padx=14, pady=3)
            self.nav[key] = button
        ctk.CTkLabel(
            side,
            text="EXTRACCIÓN DE PDF\nTrabajo local y conectado",
            justify="left",
            text_color="gray",
            font=ctk.CTkFont(size=10),
        ).pack(side="bottom", anchor="w", padx=24, pady=24)
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for name in ("extract", "history", "settings"):
            page = ctk.CTkFrame(self.content, fg_color="transparent")
            page.grid(row=0, column=0, sticky="nsew", padx=32, pady=25)
            self.pages[name] = page
        self._build_extract()
        self._build_history()
        self._build_settings()
        self.status = ctk.CTkLabel(
            self.content,
            text="Listo para comenzar",
            anchor="w",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        )
        self.status.grid(row=1, column=0, sticky="ew", padx=34, pady=(0, 10))

    def _heading(self, page, title, subtitle):
        ctk.CTkLabel(page, text=title, font=ctk.CTkFont(size=26, weight="bold"), anchor="w").pack(
            fill="x", anchor="w"
        )
        ctk.CTkLabel(page, text=subtitle, text_color="gray", anchor="w").pack(
            fill="x", anchor="w", pady=(2, 18)
        )

    def _build_extract(self):
        page = self.pages["extract"]
        self._heading(
            page, "Extraer texto", "Convertí tus archivos PDF en contenido listo para usar."
        )
        card = ctk.CTkFrame(page, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(15, 5))
        info = ctk.CTkFrame(top, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            info, text="DOCUMENTO", text_color="gray", font=ctk.CTkFont(size=10, weight="bold")
        ).pack(anchor="w")
        self.file_label = ctk.CTkLabel(
            info,
            text="Ningún archivo seleccionado",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        )
        self.file_label.pack(fill="x", anchor="w")
        self.file_info = ctk.CTkLabel(
            info, text="Seleccioná un archivo PDF para comenzar", text_color="gray", anchor="w"
        )
        self.file_info.pack(fill="x", anchor="w")
        self.select_button = ctk.CTkButton(
            top, text="Seleccionar PDF", width=140, command=self.select_file
        )
        self.select_button.pack(side="right", padx=(12, 0))
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(8, 14))
        ctk.CTkLabel(actions, text="Formato:", text_color="gray").pack(side="left", padx=(0, 10))
        self.format_choice = ctk.CTkSegmentedButton(actions, values=["Texto", "Markdown"])
        self.format_choice.set("Texto")
        self.format_choice.pack(side="left")
        self.extract_button = ctk.CTkButton(
            actions, text="Iniciar extracción", height=36, command=self.extract
        )
        self.extract_button.pack(side="right")
        self.progress = ctk.CTkProgressBar(page, mode="determinate", height=6)
        self.progress.pack(fill="x", pady=(0, 10))
        self.progress.set(0)
        result_head = ctk.CTkFrame(page, fg_color="transparent")
        result_head.pack(fill="x", pady=(3, 5))
        ctk.CTkLabel(result_head, text="Resultado", font=ctk.CTkFont(size=17, weight="bold")).pack(
            side="left"
        )
        self.result_label = ctk.CTkLabel(result_head, text="Sin contenido", text_color="gray")
        self.result_label.pack(side="left", padx=12)
        ctk.CTkButton(
            result_head,
            text="Copiar",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self.copy_result,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(result_head, text="Exportar", width=100, command=self.export_result).pack(
            side="right"
        )
        self.textbox = ctk.CTkTextbox(
            page, wrap="word", corner_radius=10, font=ctk.CTkFont(size=13)
        )
        self.textbox.pack(fill="both", expand=True)
        ctk.CTkLabel(
            page,
            text="Podés editar el resultado antes de copiarlo o exportarlo.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", pady=(6, 0))

    def _build_history(self):
        page = self.pages["history"]
        self._heading(
            page, "Historial", "Consultá los documentos guardados por el servicio de texto."
        )
        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(bar, text="Actualizar", width=100, command=lambda: self.load_history(0)).pack(
            side="left"
        )
        self.history_page_label = ctk.CTkLabel(bar, text="", text_color="gray")
        self.history_page_label.pack(side="right")
        self.history_frame = ctk.CTkScrollableFrame(page, corner_radius=10)
        self.history_frame.pack(fill="both", expand=True)
        controls = ctk.CTkFrame(page, fg_color="transparent")
        controls.pack(fill="x", pady=(12, 0))
        ctk.CTkButton(
            controls,
            text="Anterior",
            width=85,
            command=lambda: self.load_history(max(0, self.history_offset - PAGE_SIZE)),
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(controls, text="Siguiente", width=85, command=self.next_history).pack(
            side="left"
        )
        ctk.CTkButton(
            controls,
            text="Eliminar",
            width=90,
            fg_color="#b94a48",
            hover_color="#963c3b",
            command=self.delete_history,
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            controls,
            text="Renombrar",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self.rename_history,
        ).pack(side="right", padx=6)
        ctk.CTkButton(controls, text="Abrir texto", width=110, command=self.open_history).pack(
            side="right"
        )
        self.selection_label = ctk.CTkLabel(
            page, text="Seleccioná un documento de la lista.", text_color="gray", anchor="w"
        )
        self.selection_label.pack(fill="x", pady=(8, 0))

    def _build_settings(self):
        page = self.pages["settings"]
        self._heading(
            page, "Configuración", "Personalizá la apariencia y la conexión con los servicios."
        )
        box = ctk.CTkFrame(page, corner_radius=12)
        box.pack(fill="x")
        for label, attr, key in [
            ("URL del servicio de extracción", "extract_entry", "extract_url"),
            ("URL del servicio de documentos", "documents_entry", "documents_url"),
        ]:
            ctk.CTkLabel(box, text=label, anchor="w").pack(fill="x", padx=20, pady=(16, 3))
            entry = ctk.CTkEntry(box, height=36)
            entry.insert(0, self.settings[key])
            entry.pack(fill="x", padx=20)
            setattr(self, attr, entry)
        ctk.CTkLabel(box, text="Apariencia", anchor="w").pack(fill="x", padx=20, pady=(16, 3))
        self.theme = ctk.CTkOptionMenu(box, values=["Oscuro", "Claro", "Sistema"])
        self.theme.set(
            {"dark": "Oscuro", "light": "Claro", "system": "Sistema"}[self.settings["theme"]]
        )
        self.theme.pack(anchor="w", padx=20)
        ctk.CTkLabel(
            box,
            text="Con Docker, ambas URLs pueden apuntar al gateway. Sin Docker, usá las URLs de cada servicio.",
            text_color="gray",
            wraplength=610,
            justify="left",
        ).pack(anchor="w", padx=20, pady=14)
        ctk.CTkButton(box, text="Guardar configuración", command=self.apply_settings).pack(
            anchor="w", padx=20, pady=(0, 20)
        )

    def show_page(self, name):
        self.pages[name].tkraise()
        for key, button in self.nav.items():
            button.configure(fg_color=("#dbeafe", "#263b59") if key == name else "transparent")
        if name == "history" and not self.busy:
            self.load_history(0)

    def select_file(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(
            title="Seleccionar PDF", filetypes=[("Archivos PDF", "*.pdf")]
        )
        if not path:
            return
        try:
            size = Path(path).stat().st_size
        except OSError as exc:
            messagebox.showerror("Archivo", f"No se pudo acceder al archivo: {exc}", parent=self)
            return
        self.selected_file = path
        self.file_label.configure(text=Path(path).name)
        self.file_info.configure(text=f"{size / 1024 / 1024:.2f} MB · {path}")
        self.textbox.delete("1.0", "end")
        self.result_source = self.result_format = None
        self.result_label.configure(text="Sin contenido")

    def run_job(self, label, work, on_success):
        if self.busy:
            messagebox.showinfo(
                "Operación en curso", "Esperá a que termine la operación actual.", parent=self
            )
            return
        self.busy = True
        self.select_button.configure(state="disabled")
        self.extract_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self.status.configure(text=label)

        def worker():
            try:
                self.jobs.put((True, work(), on_success))
            except Exception as exc:
                logger.exception("Error en operación de backend")
                self.jobs.put((False, exc, on_success))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_jobs(self):
        try:
            while True:
                success, result, callback = self.jobs.get_nowait()
                self.busy = False
                self.select_button.configure(state="normal")
                self.extract_button.configure(state="normal")
                self.progress.stop()
                self.progress.configure(mode="determinate")
                self.progress.set(0)
                if success:
                    self.status.configure(text="Operación completada")
                    callback(result)
                else:
                    self.status.configure(text="No se pudo completar la operación")
                    if self.result_source is None:
                        self.result_label.configure(text="Sin contenido")
                    messagebox.showerror(
                        "Error",
                        (
                            str(result)
                            if isinstance(result, ApiError)
                            else "Ocurrió un error inesperado. Revisá los registros de la aplicación."
                        ),
                        parent=self,
                    )
        except queue.Empty:
            pass
        self.after(80, self._poll_jobs)

    def extract(self):
        if not self.selected_file:
            messagebox.showwarning(
                "Seleccionar PDF", "Seleccioná un archivo PDF primero.", parent=self
            )
            return
        if self.busy:
            return
        path = self.selected_file
        fmt = "md" if self.format_choice.get() == "Markdown" else "txt"
        self.textbox.delete("1.0", "end")
        self.result_source = self.result_format = None
        self.result_label.configure(text="Procesando…")
        client = self.api()

        def done(text):
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", text)
            self.result_source, self.result_format = Path(path).name, fmt
            self.result_label.configure(text=f"{self.result_source} · {fmt.upper()}")
            if not text.strip():
                messagebox.showinfo(
                    "Sin texto",
                    "No se encontró texto. Si el documento es escaneado, el OCR debe estar habilitado en el servidor.",
                    parent=self,
                )

        self.run_job(
            "Extrayendo contenido… La barra indica actividad, no porcentaje.",
            lambda: client.extract(path, fmt),
            done,
        )

    def current_text(self):
        return self.textbox.get("1.0", "end-1c")

    def copy_result(self):
        text = self.current_text()
        if not text:
            messagebox.showwarning("Sin contenido", "No hay texto para copiar.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.configure(text="Texto copiado al portapapeles")

    def export_result(self):
        text = self.current_text()
        if not text:
            messagebox.showwarning("Sin contenido", "No hay texto para exportar.", parent=self)
            return
        ext = "." + (self.result_format or "txt")
        name = Path(self.result_source or "resultado").stem + ext
        path = filedialog.asksaveasfilename(
            title="Exportar resultado",
            initialfile=name,
            defaultextension=ext,
            filetypes=[("Texto", "*.txt"), ("Markdown", "*.md")],
        )
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
            except OSError as exc:
                messagebox.showerror("Error al guardar", str(exc), parent=self)
                return
            self.status.configure(text="Resultado guardado correctamente")

    def load_history(self, offset):
        client = self.api()

        def done(items):
            self.history_offset, self.history_items = offset, items
            self.selected_id = self.selected_name = None
            self.selection_label.configure(text="Seleccioná un documento de la lista.")
            for widget in self.history_frame.winfo_children():
                widget.destroy()
            if not items:
                ctk.CTkLabel(
                    self.history_frame, text="No hay documentos en esta página.", text_color="gray"
                ).pack(pady=24)
            for doc in items:
                doc_id = str(doc.get("_id", ""))
                name = str(doc.get("pdf_nombre", "Sin nombre"))
                date = str(doc.get("created_at", ""))[:16].replace("T", " ")
                label = f'{name}   ·   {doc.get("estado", "")}   ·   {date}'
                ctk.CTkButton(
                    self.history_frame,
                    text=label,
                    anchor="w",
                    fg_color="transparent",
                    text_color=("#273449", "#e4eaf3"),
                    hover_color=("#dbeafe", "#23324a"),
                    command=lambda i=doc_id, n=name: self.select_history(i, n),
                ).pack(fill="x", padx=6, pady=3)
            self.history_page_label.configure(
                text=f"Documentos {offset + 1 if items else 0}–{offset + len(items)}"
            )

        self.run_job("Cargando historial…", lambda: client.history(offset, PAGE_SIZE), done)

    def next_history(self):
        if len(self.history_items) == PAGE_SIZE:
            self.load_history(self.history_offset + PAGE_SIZE)

    def select_history(self, doc_id, name):
        self.selected_id, self.selected_name = doc_id, name
        self.selection_label.configure(text=f"Seleccionado: {name}")

    def _has_selection(self):
        if not self.selected_id:
            messagebox.showwarning("Historial", "Seleccioná un documento de la lista.", parent=self)
            return False
        return True

    def open_history(self):
        if not self._has_selection():
            return
        client, doc_id = self.api(), self.selected_id

        def done(doc):
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", doc["txt_contenido"])
            self.result_source, self.result_format = doc.get("pdf_nombre", "documento"), "txt"
            self.result_label.configure(text=f"{self.result_source} · TXT · Historial")
            self.show_page("extract")

        self.run_job("Abriendo documento…", lambda: client.document(doc_id), done)

    def rename_history(self):
        if not self._has_selection():
            return
        dialog = ctk.CTkInputDialog(title="Renombrar", text="Nuevo nombre del documento:")
        name = dialog.get_input()
        if name is None:
            return
        name = name.strip()
        if not name or len(name) > 200:
            messagebox.showwarning(
                "Nombre inválido", "Ingresá un nombre de entre 1 y 200 caracteres.", parent=self
            )
            return
        client, doc_id, offset = self.api(), self.selected_id, self.history_offset
        self.run_job(
            "Renombrando documento…",
            lambda: client.rename(doc_id, name),
            lambda _: self.load_history(offset),
        )

    def delete_history(self):
        if not self._has_selection():
            return
        if not messagebox.askyesno(
            "Eliminar", f"¿Eliminar «{self.selected_name}» del historial?", parent=self
        ):
            return
        client, doc_id, offset = self.api(), self.selected_id, self.history_offset
        self.run_job(
            "Eliminando documento…",
            lambda: client.delete(doc_id),
            lambda _: self.load_history(offset),
        )

    def apply_settings(self):
        settings = {
            "extract_url": self.extract_entry.get().strip().rstrip("/"),
            "documents_url": self.documents_entry.get().strip().rstrip("/"),
            "theme": {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}[self.theme.get()],
        }
        try:
            save_settings(settings)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Configuración", str(exc), parent=self)
            return
        self.settings = settings
        ctk.set_appearance_mode(settings["theme"])
        self.status.configure(text="Configuración guardada")
        messagebox.showinfo("Configuración", "Configuración guardada correctamente.", parent=self)


def main():
    logging.basicConfig(level=logging.INFO)
    PDFExtractApp().mainloop()


if __name__ == "__main__":
    main()
