import hashlib
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import config

ARQUIVO_HASH = "material.sha256"


def _hash_material(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class StateRAG:
    def __init__(self, caminho_material=config.CONHECIMENTO, caminho_indice=config.INDICE_RAG):
        self.caminho_material = caminho_material
        self.caminho_indice = caminho_indice
        self.embeddings = OllamaEmbeddings(model=config.MODELO_EMBEDDING, base_url=config.OLLAMA_URL)
        self.vectorstore = self._carregar_ou_criar_indice()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": config.RAG_K})

    def _carregar_ou_criar_indice(self):
        if not self.caminho_material.exists():
            raise FileNotFoundError(f"Arquivo de conhecimento nao encontrado em: {self.caminho_material}")
        texto = self.caminho_material.read_text(encoding="utf-8")
        hash_atual = _hash_material(texto)

        # Reaproveita o indice so se ele foi gerado a partir desta versao do material
        arquivo_hash = self.caminho_indice / ARQUIVO_HASH
        if arquivo_hash.exists() and arquivo_hash.read_text().strip() == hash_atual:
            return FAISS.load_local(str(self.caminho_indice), self.embeddings,
                                    allow_dangerous_deserialization=True)  # arquivo gerado por nos mesmos

        # Divide primeiro por secao
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.RAG_TAMANHO_TRECHO,
            chunk_overlap=150,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "],
        )
        trechos = splitter.split_documents([Document(page_content=texto, metadata={"fonte": "state.md"})])

        vectorstore = FAISS.from_documents(trechos, self.embeddings)
        vectorstore.save_local(str(self.caminho_indice))
        arquivo_hash.write_text(hash_atual)
        return vectorstore

    def buscar_contexto(self, query: str) -> str:
        docs = self.retriever.invoke(query)
        if not docs:
            return "Nenhum trecho do material foi encontrado para esta pergunta."
        return "\n\n---\n\n".join(d.page_content for d in docs)


_instancia = None


def get_rag_service() -> StateRAG:
    global _instancia
    if _instancia is None:
        _instancia = StateRAG()
    return _instancia
