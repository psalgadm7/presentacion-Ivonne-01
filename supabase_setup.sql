-- ============================================================
-- supabase_setup.sql
-- Ejecutar UNA SOLA VEZ en el SQL Editor de Supabase
-- (supabase.com → proyecto → SQL Editor → New query)
-- ============================================================

-- 1. Tabla: contenido (fila única con todo el JSON del sitio)
CREATE TABLE IF NOT EXISTS contenido (
  id         INTEGER     PRIMARY KEY,
  data       JSONB       NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO contenido (id, data) VALUES (1, '{}')
ON CONFLICT (id) DO NOTHING;

-- 2. Tabla: imagen_orden (fila única con array de {nombre, url, public_id})
CREATE TABLE IF NOT EXISTS imagen_orden (
  id         INTEGER     PRIMARY KEY,
  orden      JSONB       NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO imagen_orden (id, orden) VALUES (1, '[]')
ON CONFLICT (id) DO NOTHING;

-- 3. Tabla: media (registro de todos los archivos subidos a Cloudinary)
CREATE TABLE IF NOT EXISTS media (
  id         SERIAL      PRIMARY KEY,
  tipo       TEXT        NOT NULL, -- imagen | video | audio | documento
  nombre     TEXT        NOT NULL,
  url        TEXT        NOT NULL,
  public_id  TEXT        NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Deshabilitar RLS para acceso con anon key
--    (si necesitas seguridad, configura políticas RLS según tu caso)
ALTER TABLE contenido    DISABLE ROW LEVEL SECURITY;
ALTER TABLE imagen_orden DISABLE ROW LEVEL SECURITY;
ALTER TABLE media        DISABLE ROW LEVEL SECURITY;
