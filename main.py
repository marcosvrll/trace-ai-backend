from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import requests
from database import engine, Base, SessionLocal
import models

# 1. Inicialização do Banco de Dados
Base.metadata.create_all(bind=engine)

# 2. Inicialização do Framework FastAPI
app = FastAPI(title="Trace AI - ISOC Backend (Cloud Version)")

# 3. Configuração de Segurança (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# 4. Gerenciamento de Sessão do Banco de Dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. Schema de Validação do Payload
class OcorrenciaForm(BaseModel):
    ip_origem: str
    texto_interceptado: str
    url_origem: str

# 6. Rota Principal de Inserção de Ocorrências
@app.post("/api/v1/ocorrencias/")
def registrar_ocorrencia(dados: OcorrenciaForm, db: Session = Depends(get_db)):
    
    # URL oficial da API de Inferência gratuita da Hugging Face
    API_URL = "https://api-inference.huggingface.co/models/nlptown/bert-base-multilingual-uncased-sentiment"
    
    try:
        # Envia o texto pela internet para os servidores da Hugging Face processarem
        resposta = requests.post(API_URL, json={"inputs": dados.texto_interceptado})
        
        # Verifica se a Hugging Face respondeu com sucesso (Código 200)
        if resposta.status_code == 200:
            dados_ia = resposta.json()
            # A API devolve uma lista de probabilidades. Pegamos a classificação vencedora.
            label_estrelas = dados_ia[0][0]['label']
        else:
            # Caso a API gratuita esteja sobrecarregada no momento, evitamos que o sistema quebre
            label_estrelas = "3 stars" 
            
    except Exception as e:
        print(f"Erro de comunicação com a IA: {e}")
        label_estrelas = "3 stars"

    # Mapeamento Tático: Conversão da escala de sentimento para Score de Risco
    if label_estrelas == "1 star":
        score_risco = 0.95
    elif label_estrelas == "2 stars":
        score_risco = 0.75
    elif label_estrelas == "3 stars":
        score_risco = 0.50
    elif label_estrelas == "4 stars":
        score_risco = 0.15
    else:
        score_risco = 0.05
    
    # Instanciação e salvamento no Banco de Dados
    nova_ocorrencia = models.Ocorrencia(
        ip_origem=dados.ip_origem,
        texto_interceptado=dados.texto_interceptado,
        url_origem=dados.url_origem,
        score_risco=score_risco,
        status="pendente"
    )
    
    db.add(nova_ocorrencia)
    db.commit()
    db.refresh(nova_ocorrencia)
    
    return {
        "mensagem": "Telemetria recebida e processada via API Nuvem",
        "id_gerado": nova_ocorrencia.id,
        "risco_detectado": nova_ocorrencia.score_risco,
        "classificacao_label": label_estrelas
    }

# 7. Rota de Consulta (Painel ISOC)
@app.get("/api/v1/ocorrencias/")
def listar_ocorrencias(db: Session = Depends(get_db)):
    ocorrencias = db.query(models.Ocorrencia).order_by(models.Ocorrencia.data_hora.desc()).all()
    return ocorrencias

# ... (Mantenha todo o código anterior intacto)

# Schema de Validação para a Atualização
class OcorrenciaUpdate(BaseModel):
    status: str

# Nova Rota PATCH: Atualiza o status de uma ocorrência específica
@app.patch("/api/v1/ocorrencias/{ocorrencia_id}")
def atualizar_status(ocorrencia_id: int, dados: OcorrenciaUpdate, db: Session = Depends(get_db)):
    # 1. Busca a ocorrência no banco pelo ID
    ocorrencia = db.query(models.Ocorrencia).filter(models.Ocorrencia.id == ocorrencia_id).first()
    
    # 2. Se não encontrar, retorna erro
    if not ocorrencia:
        return {"erro": "Ocorrência não encontrada"}
    
    # 3. Atualiza o status e salva no banco
    ocorrencia.status = dados.status
    db.commit()
    db.refresh(ocorrencia)
    
    return {"mensagem": f"Status da ocorrência {ocorrencia_id} atualizado para {dados.status}"}