CREATE DATABASE IF NOT EXISTS my_finance_buddy;

USE my_finance_buddy;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    user_id VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    password_salt VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_session_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS statements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    filename VARCHAR(255) NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_hash VARCHAR(64) NULL,
    CONSTRAINT fk_statement_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    statement_id INT NOT NULL,
    transaction_date DATE NOT NULL,
    merchant VARCHAR(255) NOT NULL,
    amount DOUBLE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Others',
    description TEXT NULL,
    raw_text TEXT NULL,
    parser_confidence DOUBLE NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_statement FOREIGN KEY (statement_id) REFERENCES statements(id)
);

CREATE TABLE IF NOT EXISTS non_banking_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    transaction_date DATE NOT NULL,
    beneficiary VARCHAR(255) NOT NULL,
    amount DOUBLE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Others / Uncategorized',
    description TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_non_banking_transaction_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS loans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    loan_name VARCHAR(255) NOT NULL,
    lender VARCHAR(255) NOT NULL,
    principal_amount DOUBLE NOT NULL,
    interest_rate DOUBLE NOT NULL,
    tenure_months INT NOT NULL,
    emi_amount DOUBLE NOT NULL DEFAULT 0,
    start_date DATE NOT NULL,
    total_paid DOUBLE NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    notes TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_loan_user FOREIGN KEY (user_id) REFERENCES users(id)
);
