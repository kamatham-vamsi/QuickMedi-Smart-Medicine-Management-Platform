-- Reference schema for MySQL 8. The app also creates these tables automatically on startup.
CREATE DATABASE IF NOT EXISTS quickmedi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quickmedi;

CREATE TABLE IF NOT EXISTS medicines (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(150) NOT NULL,
  generic_name  VARCHAR(150),
  category      VARCHAR(80)  NOT NULL DEFAULT 'General',
  manufacturer  VARCHAR(150),
  batch_number  VARCHAR(60),
  quantity      INT NOT NULL DEFAULT 0,
  reorder_level INT NOT NULL DEFAULT 10,
  unit_price    DECIMAL(10,2) NOT NULL DEFAULT 0,
  expiry_date   DATE NOT NULL,
  storage_notes TEXT,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_medicines_name (name),
  INDEX idx_medicines_category (category),
  INDEX idx_medicines_expiry (expiry_date)
);

CREATE TABLE IF NOT EXISTS stock_movements (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  medicine_id INT NOT NULL,
  `change`    INT NOT NULL,
  reason      VARCHAR(200),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_movements_medicine (medicine_id),
  CONSTRAINT fk_movements_medicine FOREIGN KEY (medicine_id)
    REFERENCES medicines(id) ON DELETE CASCADE
);
