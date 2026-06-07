-- Schema updated dynamically for SQLite

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    user_id VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    password_salt VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NULL,
    filename VARCHAR(255) NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_hash VARCHAR(64) NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS raw_statement_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_id INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    parser_confidence REAL NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(statement_id) REFERENCES statements(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_line_id INTEGER NOT NULL UNIQUE,
    statement_id INTEGER NOT NULL,
    transaction_date DATE NOT NULL,
    merchant VARCHAR(255) NOT NULL,
    amount REAL NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Others',
    description TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_line_id) REFERENCES raw_statement_lines(id),
    FOREIGN KEY(statement_id) REFERENCES statements(id)
);

CREATE TABLE IF NOT EXISTS non_banking_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    transaction_date DATE NOT NULL,
    beneficiary VARCHAR(255) NOT NULL,
    amount REAL NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Others / Uncategorized',
    description TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    loan_name VARCHAR(255) NOT NULL,
    lender VARCHAR(255) NOT NULL,
    principal_amount REAL NOT NULL,
    interest_rate REAL NOT NULL,
    tenure_months INTEGER NOT NULL,
    emi_amount REAL NOT NULL DEFAULT 0,
    start_date DATE NOT NULL,
    total_paid REAL NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    notes TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    asset_name VARCHAR(255) NOT NULL,
    purchase_price REAL NOT NULL,
    purchase_year INTEGER NOT NULL,
    rate_per_year REAL NOT NULL DEFAULT 0,
    notes TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Indices for rapid querying
CREATE INDEX ix_users_user_id ON users(user_id);
CREATE INDEX ix_statements_user_id ON statements(user_id);
CREATE INDEX ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX ix_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX ix_transactions_statement_id ON transactions(statement_id);
CREATE INDEX ix_transactions_raw_line_id ON transactions(raw_line_id);
CREATE INDEX ix_transactions_transaction_date ON transactions(transaction_date);
CREATE INDEX ix_transactions_category ON transactions(category);
CREATE INDEX ix_transactions_merchant ON transactions(merchant);
CREATE INDEX ix_non_banking_transactions_user_id ON non_banking_transactions(user_id);
CREATE INDEX ix_non_banking_transactions_transaction_date ON non_banking_transactions(transaction_date);
CREATE INDEX ix_non_banking_transactions_category ON non_banking_transactions(category);
