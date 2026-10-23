import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

BASE_DIR = Path(__file__).resolve().parent
DOC_PATH = BASE_DIR / "conhecimento" / "state.md"
INDEX_PATH = BASE_DIR / "faiss_index"

class StateRAG:
    def __init__(self):
        # Usando embeddings
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.vectorstore = self._carregar_ou_criar_indice()
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 2})

    def _carregar_ou_criar_indice(self):
        if INDEX_PATH.exists():
            return FAISS.load_local(
                str(INDEX_PATH), 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
 
        if not DOC_PATH.exists():
            raise FileNotFoundError(f"Arquivo de conhecimento não encontrado em: {DOC_PATH}")

        loader = TextLoader(str(DOC_PATH), encoding="utf-8")
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n## ", "\n### ", "\n\n", "\n", " "]
        )
        chunks = text_splitter.split_documents(docs)

        vectorstore = FAISS.from_documents(chunks, self.embeddings)
        vectorstore.save_local(str(INDEX_PATH))
        return vectorstore

    def buscar_contexto(self, query: str) -> str:
        docs = self.retriever.invoke(query)
        if not docs:
            return "Nenhum contexto específico encontrado."
        return "\n\n---\n\n".join([d.page_content for d in docs])


rag_service = StateRAG()