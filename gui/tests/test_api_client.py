"""Pruebas del cliente que conecta la interfaz con el backend."""

from unittest.mock import Mock

import pytest
import requests

from api_client import ApiClient, ApiError


def crear_respuesta(datos, estado=200):
    respuesta = Mock(
        ok=estado < 400,
        status_code=estado,
    )

    respuesta.json.return_value = datos

    return respuesta


def test_texto_usa_el_servicio_de_documentos(tmp_path):
    pdf = tmp_path / "informe.pdf"
    pdf.write_bytes(b"%PDF-datos")

    sesion = Mock()

    sesion.request.return_value = crear_respuesta({"extracted_text": "hola"})

    cliente = ApiClient(
        "http://extract",
        "http://documents",
        session=sesion,
    )

    resultado = cliente.extract(pdf, "txt")

    assert resultado == "hola"

    argumentos, opciones = sesion.request.call_args

    assert argumentos == (
        "POST",
        "http://documents/documents/upload",
    )

    assert opciones["files"]["file"][0] == "informe.pdf"

    assert opciones["files"]["file"][2] == "application/pdf"

    assert opciones["timeout"] == (5, 120)


def test_markdown_usa_el_servicio_de_extraccion(tmp_path):
    pdf = tmp_path / "archivo.pdf"
    pdf.write_bytes(b"%PDF-datos")

    sesion = Mock()

    sesion.request.return_value = crear_respuesta(
        {
            "content": "# Título",
            "page_count": 1,
        }
    )

    cliente = ApiClient(
        "http://extract/",
        "http://documents/",
        session=sesion,
    )

    resultado = cliente.extract(pdf, "md")

    assert resultado == "# Título"

    assert sesion.request.call_args.args == (
        "POST",
        "http://extract/extract",
    )


def test_errores_de_conexion_y_tiempo_de_espera():
    sesion = Mock()

    cliente = ApiClient(
        "http://extract",
        "http://documents",
        session=sesion,
    )

    sesion.request.side_effect = requests.Timeout()

    with pytest.raises(
        ApiError,
        match="tardó demasiado",
    ):
        cliente.history()

    sesion.request.side_effect = requests.ConnectionError()

    with pytest.raises(
        ApiError,
        match="conectar",
    ):
        cliente.history()


def test_respuesta_de_error_y_respuesta_invalida():
    sesion = Mock()

    cliente = ApiClient(
        "http://extract",
        "http://documents",
        session=sesion,
    )

    sesion.request.return_value = crear_respuesta(
        {"detail": "PDF inválido"},
        400,
    )

    with pytest.raises(
        ApiError,
        match="PDF inválido",
    ):
        cliente.history()

    sesion.request.return_value = crear_respuesta({"datos_incorrectos": []})

    with pytest.raises(
        ApiError,
        match="historial inválido",
    ):
        cliente.history()


def test_operaciones_del_historial():
    sesion = Mock()

    sesion.request.side_effect = [
        crear_respuesta({"items": []}),
        crear_respuesta(
            {
                "document": {
                    "txt_contenido": "hola",
                }
            }
        ),
        crear_respuesta({}),
        crear_respuesta({}),
    ]

    cliente = ApiClient(
        "http://extract",
        "http://documents",
        session=sesion,
    )

    assert cliente.history(20, 20) == []

    assert sesion.request.call_args.kwargs["params"] == {
        "skip": 20,
        "limit": 20,
    }

    documento = cliente.document("abc")

    assert documento["txt_contenido"] == "hola"

    cliente.rename("abc", "nuevo.pdf")
    cliente.delete("abc")

    assert sesion.request.call_args.args == (
        "DELETE",
        "http://documents/documents/abc",
    )
