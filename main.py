import hashlib
import requests
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Importações do banco de dados (certifique-se de que database.py e models.py existem)
from database import engine, SessionLocal, Base
import models

# Cria as tabelas no banco de dados automaticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Trace AI Backend")

# Libera o acesso para o Painel HTML e para a Extensão do Chrome
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependência do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schemas de Validação (Pydantic) ---
class OcorrenciaCreate(BaseModel):
    texto_interceptado: str
    url_origem: str
    ip_origem: str = "IP_DESCONHECIDO"

class OcorrenciaUpdate(BaseModel):
    status: str

# --- Função de Privacidade LGPD ---
def anonimizar_ip(ip_real: str) -> str:
    if not ip_real or ip_real == "IP_DESCONHECIDO":
        return "IP_DESCONHECIDO"
    # Criptografa o IP em uma hash irreversível
    ip_hash = hashlib.sha256(ip_real.encode('utf-8')).hexdigest()
    # Retorna apenas os 10 primeiros caracteres com o prefixo
    return f"HASH-{ip_hash[:10].upper()}"


# --- ROTAS DA API ---

@app.post("/api/v1/ocorrencias/")
def criar_ocorrencia(dados: OcorrenciaCreate, db: Session = Depends(get_db)):
    
    # 1. Análise de Risco com a IA (Hugging Face)
    API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    # ATENÇÃO: Coloque o seu token real aqui se for exigido pela API
    headers = {"Authorization": "Bearer SEU_TOKEN_HUGGING_FACE"} 
    
    score_calculado = 0.0
    try:
        resposta_ia = requests.post(API_URL, headers=headers, json={"inputs": dados.texto_interceptado})
        if resposta_ia.status_code == 200:
            resultados = resposta_ia.json()
            score_calculado = resultados[0][0].get("score", 0.0)
    except Exception as e:
        print(f"Erro ao conectar com Hugging Face: {e}")

    # 2. Aplica o Hashing no IP
    ip_seguro = anonimizar_ip(dados.ip_origem)

    # 3. Salva no banco de dados com o IP protegido
    nova_ocorrencia = models.Ocorrencia(
        texto_interceptado=dados.texto_interceptado,
        score_risco=score_calculado,
        url_origem=dados.url_origem,
        ip_origem=ip_seguro,
        status="pendente"
    )
    
    db.add(nova_ocorrencia)
    db.commit()
    db.refresh(nova_ocorrencia)
    
    return nova_ocorrencia


@app.get("/api/v1/ocorrencias/")
def listar_ocorrencias(db: Session = Depends(get_db)):
    # Retorna todas as ocorrências ordenadas da mais recente para a mais antiga
    return db.query(models.Ocorrencia).order_by(models.Ocorrencia.id.desc()).all()


@app.patch("/api/v1/ocorrencias/{ocorrencia_id}")
def atualizar_status(ocorrencia_id: int, dados: OcorrenciaUpdate, db: Session = Depends(get_db)):
    ocorrencia = db.query(models.Ocorrencia).filter(models.Ocorrencia.id == ocorrencia_id).first()
    
    if not ocorrencia:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    
    ocorrencia.status = dados.status
    db.commit()
    db.refresh(ocorrencia)
    
    return ocorrencia