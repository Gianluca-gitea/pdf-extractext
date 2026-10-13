import importlib
import requests
import tkinter as tk
from unittest.mock import MagicMock

import interface


def test_seleccionar_pdf_exito(mocker):
    interface.archivo_pdf = None
    ruta_falsa = "/ruta/falsa/mi_documento.pdf"

    mocker.patch("interface.filedialog.askopenfilename", return_value=ruta_falsa)

    interface.seleccionar_pdf()

    assert interface.archivo_pdf == ruta_falsa
    assert "mi_documento.pdf" in interface.label_archivo.cget("text")


def test_extraer_texto_exito(mocker):

    interface.archivo_pdf = "archivo_ficticio.pdf"
    interface.texto_extraido_global = ""
    interface.texto_resultado.delete("1.0", tk.END)

    mocker.patch("builtins.open", mocker.mock_open(read_data=b"contenido pdf fake"))

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"extracted_text": "Texto extraído por el mock"}
    mocker.patch("interface.requests.post", return_value=mock_response)

    interface.extraer_texto()

    assert interface.texto_extraido_global == "Texto extraído por el mock"

    texto_en_pantalla = interface.texto_resultado.get("1.0", tk.END).strip()
    assert texto_en_pantalla == "Texto extraído por el mock"


def test_descargar_txt_sin_texto_muestra_alerta(mocker):
    interface.texto_extraido_global = ""

    mock_warning = mocker.patch("interface.messagebox.showwarning")
    mock_asksaveas = mocker.patch("interface.filedialog.asksaveasfilename")

    interface.descargar_txt()

    mock_warning.assert_called_once_with("Advertencia", "No hay texto para descargar.")
    mock_asksaveas.assert_not_called()


def test_descargar_txt_exito(mocker):
    interface.texto_extraido_global = "texto para guardar en el disco"
    ruta_guardado = "/ruta/falsa/descarga.txt"

    mocker.patch("interface.filedialog.asksaveasfilename", return_value=ruta_guardado)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_showinfo = mocker.patch("interface.messagebox.showinfo")

    interface.descargar_txt()

    mock_open.assert_called_once_with(ruta_guardado, "w", encoding="utf-8")
    mock_open().write.assert_called_once_with("texto para guardar en el disco")
    mock_showinfo.assert_called_once_with("Éxito", "TXT descargado correctamente.")


def test_extraer_texto_falla_con_error_http(mocker):
    interface.archivo_pdf = "archivo.pdf"
    mocker.patch("builtins.open", mocker.mock_open(read_data=b"data"))

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Error interno del servidor"
    mocker.patch("interface.requests.post", return_value=mock_response)

    mock_showerror = mocker.patch("interface.messagebox.showerror")

    interface.extraer_texto()

    mock_showerror.assert_called_once_with("Error", "Error interno del servidor")


def test_extraer_texto_falla_sin_conexion(mocker):
    interface.archivo_pdf = "archivo.pdf"
    mocker.patch("builtins.open", mocker.mock_open(read_data=b"data"))

    mocker.patch(
        "interface.requests.post",
        side_effect=requests.exceptions.ConnectionError("Failed to connect"),
    )
    mock_showerror = mocker.patch("interface.messagebox.showerror")

    interface.extraer_texto()

    assert mock_showerror.call_count == 1
    args, _ = mock_showerror.call_args
    assert args[0] == "Error de Conexión"
    assert "No se pudo conectar" in args[1]


def test_extraer_texto_falla_por_permisos_de_archivo(mocker):
    interface.archivo_pdf = "/ruta/protegida/archivo.pdf"

    mocker.patch("builtins.open", side_effect=PermissionError("Permiso denegado"))
    mock_showerror = mocker.patch("interface.messagebox.showerror")

    interface.extraer_texto()

    mock_showerror.assert_called_once()
    args, _ = mock_showerror.call_args
    assert args[0] == "Error"
    assert "Permiso denegado" in args[1]


def test_cargar_lista_historial_exito(mocker):
    mock_tree = MagicMock()
    mock_tree.get_children.return_value = ["row1"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "_id": "111",
                "pdf_nombre": "test.pdf",
                "estado": "ok",
                "created_at": "2026-05-25T10:00:00",
            }
        ]
    }
    mock_get = mocker.patch("interface.requests.get", return_value=mock_response)

    interface.cargar_lista_historial(mock_tree)

    mock_tree.delete.assert_called_once_with("row1")
    mock_get.assert_called_once_with("http://127.0.0.1:8000/documents?limit=50")
    mock_tree.insert.assert_called_with(
        "", tk.END, values=("111", "test.pdf", "ok", "2026-05-25 10:00")
    )


def test_ver_texto_historial_exito(mocker):
    mock_tree = MagicMock()
    mock_tree.selection.return_value = ["item1"]
    mock_tree.item.return_value = {"values": ["doc_123", "viejo.pdf"]}
    mock_ventana = MagicMock()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"document": {"txt_contenido": "texto recuperado"}}
    mock_get = mocker.patch("interface.requests.get", return_value=mock_response)
    mock_showinfo = mocker.patch("interface.messagebox.showinfo")

    interface.texto_resultado.delete("1.0", tk.END)

    interface.ver_texto_historial(mock_tree, mock_ventana)

    mock_get.assert_called_with("http://127.0.0.1:8000/documents/doc_123?include_text=true")
    assert interface.texto_extraido_global == "texto recuperado"
    assert interface.texto_resultado.get("1.0", tk.END).strip() == "texto recuperado"
    mock_showinfo.assert_called_once()
    mock_ventana.destroy.assert_called_once()


def test_renombrar_historial_exito(mocker):
    mock_tree = MagicMock()
    mock_tree.selection.return_value = ["item1"]
    mock_tree.item.return_value = {"values": ["doc_123", "viejo.pdf"]}

    mocker.patch("interface.simpledialog.askstring", return_value="nuevo_nombre.pdf")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_patch = mocker.patch("interface.requests.patch", return_value=mock_response)
    mock_cargar = mocker.patch("interface.cargar_lista_historial")

    interface.renombrar_historial(mock_tree)

    mock_patch.assert_called_with(
        "http://127.0.0.1:8000/documents/doc_123", json={"pdf_nombre": "nuevo_nombre.pdf"}
    )
    mock_cargar.assert_called_once_with(mock_tree)


def test_eliminar_historial_exito(mocker):
    mock_tree = MagicMock()
    mock_tree.selection.return_value = ["item1"]
    mock_tree.item.return_value = {"values": ["doc_123", "viejo.pdf"]}

    mocker.patch("interface.messagebox.askyesno", return_value=True)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_delete = mocker.patch("interface.requests.delete", return_value=mock_response)
    mock_cargar = mocker.patch("interface.cargar_lista_historial")

    interface.eliminar_historial(mock_tree)

    mock_delete.assert_called_with("http://127.0.0.1:8000/documents/doc_123")
    mock_cargar.assert_called_once_with(mock_tree)


def test_historial_acciones_sin_seleccion_muestra_advertencia(mocker):
    mock_tree = MagicMock()
    mock_tree.selection.return_value = []

    mock_warning = mocker.patch("interface.messagebox.showwarning")

    interface.ver_texto_historial(mock_tree, MagicMock())
    interface.renombrar_historial(mock_tree)
    interface.eliminar_historial(mock_tree)

    assert mock_warning.call_count == 3


def test_historial_acciones_error_de_conexion(mocker):
    mock_tree = MagicMock()
    mock_tree.selection.return_value = ["item1"]
    mock_tree.item.return_value = {"values": ["doc_123", "viejo.pdf"]}

    mocker.patch("interface.simpledialog.askstring", return_value="nuevo.pdf")
    mocker.patch("interface.messagebox.askyesno", return_value=True)

    mocker.patch(
        "interface.requests.get", side_effect=requests.exceptions.ConnectionError("Failed")
    )
    mocker.patch(
        "interface.requests.patch", side_effect=requests.exceptions.ConnectionError("Failed")
    )
    mocker.patch(
        "interface.requests.delete", side_effect=requests.exceptions.ConnectionError("Failed")
    )

    mock_showerror = mocker.patch("interface.messagebox.showerror")

    interface.cargar_lista_historial(mock_tree)
    interface.ver_texto_historial(mock_tree, MagicMock())
    interface.renombrar_historial(mock_tree)
    interface.eliminar_historial(mock_tree)

    assert mock_showerror.call_count == 4


def test_abrir_historial_crea_ui(mocker):
    mocker.patch("interface.tk.Toplevel")
    mocker.patch("interface.ttk.Treeview")
    mocker.patch("interface.tk.Frame")
    mocker.patch("interface.tk.Button")

    mock_cargar = mocker.patch("interface.cargar_lista_historial")

    interface.abrir_historial()

    mock_cargar.assert_called_once()


def test_extraer_markdown_usa_extract_y_muestra_content(mocker):
    interface.archivo_pdf = "archivo_ficticio.pdf"
    interface.texto_extraido_global = ""
    interface.texto_resultado.delete("1.0", tk.END)

    mocker.patch("builtins.open", mocker.mock_open(read_data=b"contenido pdf fake"))

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "# Titulo\n\nCuerpo", "page_count": 1}
    mock_post = mocker.patch("interface.requests.post", return_value=mock_response)

    interface.extraer_markdown()

    assert mock_post.call_args.args[0] == "http://127.0.0.1:8000/extract"
    assert interface.texto_extraido_global == "# Titulo\n\nCuerpo"
    assert interface.texto_resultado.get("1.0", tk.END).strip() == "# Titulo\n\nCuerpo"


def test_descargar_md_guarda_archivo_markdown(mocker):
    interface.texto_extraido_global = "# Titulo"
    ruta_guardado = "/ruta/falsa/descarga.md"

    mock_asksaveas = mocker.patch(
        "interface.filedialog.asksaveasfilename", return_value=ruta_guardado
    )
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_showinfo = mocker.patch("interface.messagebox.showinfo")

    interface.descargar_md()

    assert mock_asksaveas.call_args.kwargs["defaultextension"] == ".md"
    mock_open.assert_called_once_with(ruta_guardado, "w", encoding="utf-8")
    mock_open().write.assert_called_once_with("# Titulo")
    mock_showinfo.assert_called_once_with("Éxito", "MD descargado correctamente.")


def test_extraer_texto_envia_el_nombre_real_del_archivo(mocker):
    interface.archivo_pdf = "/ruta/falsa/mi_documento.pdf"
    mocker.patch("builtins.open", mocker.mock_open(read_data=b"contenido pdf fake"))
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"extracted_text": ""}
    mock_post = mocker.patch("interface.requests.post", return_value=mock_response)

    interface.extraer_texto()

    assert mock_post.call_args.kwargs["files"]["file"][0] == "mi_documento.pdf"


def test_api_url_se_lee_del_entorno(monkeypatch):
    monkeypatch.setenv("API_URL", "http://api.ejemplo:9000")
    try:
        importlib.reload(interface)
        assert interface.API_URL == "http://api.ejemplo:9000"
    finally:
        monkeypatch.delenv("API_URL")
        importlib.reload(interface)


def test_urls_por_servicio_usan_api_url_por_defecto(monkeypatch):
    monkeypatch.setenv("API_URL", "http://gateway:8000")
    monkeypatch.delenv("EXTRACT_API_URL", raising=False)
    monkeypatch.delenv("DOCUMENTS_API_URL", raising=False)
    try:
        importlib.reload(interface)
        assert interface.EXTRACT_API_URL == "http://gateway:8000"
        assert interface.DOCUMENTS_API_URL == "http://gateway:8000"
    finally:
        monkeypatch.delenv("API_URL")
        importlib.reload(interface)


def test_urls_por_servicio_se_pueden_separar(monkeypatch, mocker):
    monkeypatch.setenv("EXTRACT_API_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("DOCUMENTS_API_URL", "http://127.0.0.1:8002")
    try:
        importlib.reload(interface)
        interface.archivo_pdf = "/ruta/falsa/doc.pdf"
        mocker.patch("builtins.open", mocker.mock_open(read_data=b"pdf"))
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"content": "", "extracted_text": ""}
        mock_post = mocker.patch("interface.requests.post", return_value=mock_response)

        interface.extraer_markdown()
        interface.extraer_texto()

        urls = [call.args[0] for call in mock_post.call_args_list]
        assert urls == ["http://127.0.0.1:8001/extract", "http://127.0.0.1:8002/documents/upload"]
    finally:
        monkeypatch.delenv("EXTRACT_API_URL")
        monkeypatch.delenv("DOCUMENTS_API_URL")
        importlib.reload(interface)
