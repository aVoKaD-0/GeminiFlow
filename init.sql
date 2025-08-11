CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_key_encrypted VARCHAR(255),
    subscription_plan VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE,
    reward_claimed BOOLEAN DEFAULT FALSE,
    current_chat_id INTEGER
);

CREATE TABLE chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT REFERENCES users(telegram_id),
    title VARCHAR(255) DEFAULT 'Новый чат',
    model_name VARCHAR(255) DEFAULT 'gemini-1.5-flash',
    temperature FLOAT DEFAULT 1.0,
    top_p FLOAT,
    top_k INTEGER,
    system_prompt TEXT,
    max_output_tokens INTEGER DEFAULT 1000,
    safety_settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id INTEGER REFERENCES chats(id),
    role VARCHAR(50),
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE subscription_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    duration_days INTEGER,
    price_stars INTEGER,
    price_external NUMERIC(10, 2),    
    currency VARCHAR(3) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT REFERENCES users(telegram_id),
    referred_id BIGINT REFERENCES users(telegram_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE settings (
    
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    description TEXT
);

CREATE TABLE gemini_limits (
    model_name VARCHAR(255) PRIMARY KEY,
    requests_per_minute INTEGER,
    requests_per_day INTEGER,
    tokens_per_minute INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE subscription_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    duration_days INTEGER,
    price_stars INTEGER,
    price_external NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT TRUE
    is_active = Column(Boolean, default=True)
);

CREATE TABLE referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT REFERENCES users(telegram_id),
    referred_id BIGINT REFERENCES users(telegram_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    

CREATE TABLE settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    description TEXT
);

CREATE TABLE gemini_limits (
    model_name VARCHAR(255) PRIMARY KEY,
    requests_per_minute INTEGER,
    requests_per_day INTEGER,
    tokens_per_minute INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



