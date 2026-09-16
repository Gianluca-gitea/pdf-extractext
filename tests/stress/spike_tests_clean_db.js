import http from 'k6/http';

// Variante de spike_tests.js que vacía la base antes de la corrida, para que
// ningún PDF se resuelva por deduplicación de checksum y se mida la extracción real.
export { options, default } from './spike_tests.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const PAGE_SIZE = 100;

export function setup() {
    let deleted = 0;

    // El borrado es lógico: los documentos borrados dejan de aparecer en el listado
    // y en la búsqueda por checksum, así que se pide siempre la primera página.
    while (true) {
        const res = http.get(`${BASE_URL}/documents?limit=${PAGE_SIZE}`);
        if (res.status !== 200) {
            throw new Error(`No se pudo listar documentos (status ${res.status})`);
        }

        const items = res.json('items');
        if (items.length === 0) {
            break;
        }

        for (const item of items) {
            const del = http.del(`${BASE_URL}/documents/${item._id}`);
            if (del.status !== 200) {
                throw new Error(`No se pudo borrar ${item._id} (status ${del.status})`);
            }
            deleted++;
        }
    }

    console.log(`Base vaciada: ${deleted} documentos borrados`);
}
