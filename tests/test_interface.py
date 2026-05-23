import requests
import tkinter as tk
from unittest.mock import MagicMock

from app import interface


def test_seleccionar_pdf_exito(mocker):
    interface.archivo_pdf = None
    ruta_falsa = "/ruta/falsa/mi_documento.pdf"

    mocker.patch('app.interface.filedialog.askopenfilename', return_value=ruta_falsa)

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
    mocker.patch('app.interface.requests.post', return_value=mock_response)

    interface.extraer_texto()

    assert interface.texto_extraido_global == "Texto extraído por el mock"

    texto_en_pantalla = interface.texto_resultado.get("1.0", tk.END).strip()
    assert texto_en_pantalla == "Texto extraído por el mock"


def test_descargar_txt_sin_texto_muestra_alerta(mocker):
    interface.texto_extraido_global = ""

    mock_warning = mocker.patch('app.interface.messagebox.showwarning')
    mock_asksaveas = mocker.patch('app.interface.filedialog.asksaveasfilename')

    interface.descargar_txt()

    mock_warning.assert_called_once_with("Advertencia", "No hay texto para descargar.")
    mock_asksaveas.assert_not_called()


def test_descargar_txt_exito(mocker):
    interface.texto_extraido_global = "texto para guardar en el disco"
    ruta_guardado = "/ruta/falsa/descarga.txt"

    mocker.patch('app.interface.filedialog.asksaveasfilename', return_value=ruta_guardado)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    mock_showinfo = mocker.patch('app.interface.messagebox.showinfo')

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
    mocker.patch('app.interface.requests.post', return_value=mock_response)

    mock_showerror = mocker.patch('app.interface.messagebox.showerror')

    interface.extraer_texto()

    mock_showerror.assert_called_once_with("Error", "Error interno del servidor")


def test_extraer_texto_falla_sin_conexion(mocker):
    interface.archivo_pdf = "archivo.pdf"
    mocker.patch("builtins.open", mocker.mock_open(read_data=b"data"))

    mocker.patch('app.interface.requests.post', side_effect=requests.exceptions.ConnectionError("Failed to connect"))
    mock_showerror = mocker.patch('app.interface.messagebox.showerror')

    interface.extraer_texto()

    assert mock_showerror.call_count == 1
    args, _ = mock_showerror.call_args
    assert args[0] == "Error de Conexión"
    assert "No se pudo conectar" in args[1]


def test_extraer_texto_falla_por_permisos_de_archivo(mocker):
    interface.archivo_pdf = "/ruta/protegida/archivo.pdf"

    mocker.patch("builtins.open", side_effect=PermissionError("Permiso denegado"))
    mock_showerror = mocker.patch('app.interface.messagebox.showerror')

    interface.extraer_texto()

    mock_showerror.assert_called_once()
    args, _ = mock_showerror.call_args
    assert args[0] == "Error"
    assert "Permiso denegado" in args[1]
