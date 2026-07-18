from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cria um arquivo local chamado shield_isoc.db para guardar os dados
DATABASE_URL = "sqlite:///./shield_isoc.db"

# O motor que processa as operações no banco
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Fábrica de sessões (usada para abrir e fechar conexões a cada requisição)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# A classe base que usaremos para construir nossas tabelas no próximo arquivo
Base = declarative_base()