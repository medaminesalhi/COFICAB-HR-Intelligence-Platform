/**
 * Base API URL.
 *
 * En développement, proxy.conf.json transmet /api vers Flask.
 * En production, le reverse proxy doit router /api vers le backend.
 */
export const API_BASE_URL = '/api';
