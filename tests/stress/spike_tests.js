import http from 'k6/http';
import { Trend } from 'k6/metrics';
import { check } from 'k6';

const statusTrend = new Trend('status_codes');

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '20s', target: 100 },
        { duration: '10s', target: 0 },
    ],
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Carga de PDFs en modo binario durante la inicialización (init context de k6)
const pdfFiles = [
    { name: '2020-Scrum-Guide-Spanish-Latin-South-American.pdf', data: open('./pdfs/2020-Scrum-Guide-Spanish-Latin-South-American.pdf', 'b') },
    { name: 'Essential-Kanban-Condensed-Spanish.pdf', data: open('./pdfs/Essential-Kanban-Condensed-Spanish.pdf', 'b') },
    { name: 'Filosofia Lean.pdf', data: open('./pdfs/Filosofia Lean.pdf', 'b') },
    { name: 'scrum_manager_historias_usuario.pdf', data: open('./pdfs/scrum_manager_historias_usuario.pdf', 'b') },
];

export default function () {
    // Selección aleatoria de un PDF de la lista
    const randomPdf = pdfFiles[Math.floor(Math.random() * pdfFiles.length)];

    // La API espera el PDF como multipart/form-data en el campo "file"
    const body = {
        file: http.file(randomPdf.data, randomPdf.name, 'application/pdf'),
    };

    const res = http.post(`${BASE_URL}/documents/upload`, body);

    statusTrend.add(res.status);

    check(res, {
        'status 200': (r) => r.status === 200,
    });
}
