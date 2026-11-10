"""Pruebas de la interfaz que no necesitan abrir una ventana."""

import queue

from types import SimpleNamespace
from unittest.mock import Mock

import interface


def crear_interfaz_simulada(texto="Contenido editado"):
    return SimpleNamespace(
        textbox=Mock(),
        current_text=Mock(return_value=texto),
        status=Mock(),
        clipboard_clear=Mock(),
        clipboard_append=Mock(),
        result_source="ejemplo.pdf",
        result_format="txt",
    )


def test_copiar_usa_el_texto_visible():
    app = crear_interfaz_simulada()

    interface.PDFExtractApp.copy_result(app)

    app.clipboard_clear.assert_called_once()

    app.clipboard_append.assert_called_once_with("Contenido editado")


def test_exportar_guarda_el_texto_editado(
    tmp_path,
    monkeypatch,
):
    app = crear_interfaz_simulada("Texto corregido: áé")

    archivo = tmp_path / "resultado.txt"

    monkeypatch.setattr(
        interface.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(archivo),
    )

    interface.PDFExtractApp.export_result(app)

    contenido = archivo.read_text(encoding="utf-8")

    assert contenido == "Texto corregido: áé"


def test_importar_interfaz_no_abre_una_ventana():
    assert callable(interface.main)
    assert not hasattr(interface, "ventana")


def test_seleccionar_otro_pdf_limpia_resultado_anterior(
    tmp_path,
    monkeypatch,
):
    pdf = tmp_path / "nuevo.pdf"
    pdf.write_bytes(b"%PDF-ejemplo")

    monkeypatch.setattr(
        interface.filedialog,
        "askopenfilename",
        lambda **kwargs: str(pdf),
    )

    app = SimpleNamespace(
        busy=False,
        file_label=Mock(),
        file_info=Mock(),
        textbox=Mock(),
        result_source="anterior.pdf",
        result_format="txt",
        result_label=Mock(),
    )

    interface.PDFExtractApp.select_file(app)

    assert app.selected_file == str(pdf)
    assert app.result_source is None
    assert app.result_format is None

    app.textbox.delete.assert_called_once_with(
        "1.0",
        "end",
    )


def test_extraccion_markdown_solicita_formato_correcto(
    tmp_path,
):
    app = SimpleNamespace(
        selected_file=str(tmp_path / "prueba.pdf"),
        busy=False,
        format_choice=Mock(),
        textbox=Mock(),
        result_label=Mock(),
        api=Mock(),
        run_job=Mock(),
    )

    app.format_choice.get.return_value = "Markdown"

    interface.PDFExtractApp.extract(app)

    trabajo = app.run_job.call_args.args[1]
    trabajo()

    app.api.return_value.extract.assert_called_once_with(
        app.selected_file,
        "md",
    )

    assert app.result_source is None


def test_tarea_en_segundo_plano_devuelve_resultado():
    app = SimpleNamespace(
        busy=False,
        select_button=Mock(),
        extract_button=Mock(),
        progress=Mock(),
        status=Mock(),
        jobs=queue.Queue(),
    )

    callback = Mock()

    interface.PDFExtractApp.run_job(
        app,
        "Procesando",
        lambda: "resultado",
        callback,
    )

    exito, resultado, callback_recibido = app.jobs.get(timeout=2)

    assert exito is True
    assert resultado == "resultado"
    assert callback_recibido == callback
    assert app.busy is True


def test_historial_no_avanza_si_la_pagina_esta_incompleta():
    app = SimpleNamespace(
        history_items=[{}],
        history_offset=0,
        load_history=Mock(),
    )

    interface.PDFExtractApp.next_history(app)

    app.load_history.assert_not_called()


def test_historial_avanza_si_la_pagina_esta_completa():
    app = SimpleNamespace(
        history_items=[{}] * interface.PAGE_SIZE,
        history_offset=20,
        load_history=Mock(),
    )

    interface.PDFExtractApp.next_history(app)

    app.load_history.assert_called_once_with(40)
