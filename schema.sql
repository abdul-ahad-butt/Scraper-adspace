-- schema.sql
DROP TABLE IF EXISTS billboards;

CREATE TABLE IF NOT EXISTS billboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    media_type TEXT,
    city TEXT,
    price TEXT,
    numeric_price REAL,
    size TEXT,
    zone TEXT,
    extendable TEXT,
    availability_status TEXT,
    image_url TEXT,
    detail_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_billboards_city ON billboards(city);
CREATE INDEX IF NOT EXISTS idx_billboards_media_type ON billboards(media_type);
