export const MEDIO_TXT = { efectivo: 'EF · efectivo', transferencia: 'TR · transferencia', mercadopago: 'MP · mercadopago', debito: 'DB · débito', credito: 'CD · crédito', tarjeta: 'Tarjeta' };
export const MEDIOS_SEL = Object.entries(MEDIO_TXT).filter(([v]) => v !== 'tarjeta');
export const MEDIO_SHORT = { efectivo: 'EF', transferencia: 'TR', mercadopago: 'MP', debito: 'DB', credito: 'CD', tarjeta: 'Tarj.' };
