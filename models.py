from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime
from database import Base

class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id = Column(Integer, primary_key=True, index=True)
    ip_origem = Column(String(45), nullable=False) # Suporta IPv4 e IPv6
    texto_interceptado = Column(Text, nullable=False)
    score_risco = Column(Float, nullable=False) # Nota de 0.0 a 1.0 dada pela IA
    status = Column(String(20), default="pendente") # pendente, aprovado, descartado
    data_hora = Column(DateTime, default=datetime.utcnow) # Registro de data/hora oficial
    url_origem = Column(String(255), nullable=False) # Link da rede social