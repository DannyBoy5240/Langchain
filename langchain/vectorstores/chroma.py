"""Wrapper around ChromaDB embeddings platform."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Iterable, List, Optional

from langchain.docstore.document import Document
from langchain.embeddings.base import Embeddings
from langchain.vectorstores.base import VectorStore

logger = logging.getLogger()


class Chroma(VectorStore):
    """Wrapper around ChromaDB embeddings platform.

    To use, you should have the ``chromadb`` python package installed.

    Example:
        .. code-block:: python

                from langchain.vectorstores import Chroma
                from langchain.embeddings.openai import OpenAIEmbeddings

                embeddings = OpenAIEmbeddings()
                vectorstore = Chroma("langchain_store", embeddings.embed_query)
    """

    def __init__(
        self, collection_name: str, embedding_function: Optional[Embeddings] = None
    ) -> None:
        """Initialize with Chroma client."""
        try:
            import chromadb
        except ImportError:
            raise ValueError(
                "Could not import chromadb python package. "
                "Please it install it with `pip install chromadb`."
            )

        # TODO: Add support for custom client. For now this is in-memory only.
        self._client = chromadb.Client()
        self._embedding_function = embedding_function

        # Check if the collection exists, create it if not
        if collection_name in [col.name for col in self._client.list_collections()]:
            self._collection = self._client.get_collection(name=collection_name)
            if embedding_function is not None:
                logger.warning(
                    f"Collection {collection_name} already exists,"
                    " embedding function will not be updated."
                )
        else:
            self._collection = self._client.create_collection(
                name=collection_name,
                embedding_fn=self._embedding_function.embed_documents
                if self._embedding_function is not None
                else None,
            )

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Run more texts through the embeddings and add to the vectorstore.

        Args:
            texts (Iterable[str]): Texts to add to the vectorstore.
            metadatas (Optional[List[dict]], optional): Optional list of metadatas.
            ids (Optional[List[str]], optional): Optional list of IDs.

        Returns:
            List[str]: List of IDs of the added texts.
        """
        # TODO: Handle the case where the user doesn't provide ids on the Collection
        if ids is None:
            ids = [str(uuid.uuid1()) for _ in texts]
        self._collection.add(metadatas=metadatas, documents=texts, ids=ids)
        return ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> List[Document]:
        """Run similarity search with Chroma.

        Args:
            query (str): Query text to search for.
            k (int): Number of results to return. Defaults to 4.
            filter (Optional[Dict[str, str]]): Filter by metadata. Defaults to None.

        Returns:
            List[Document]: List of documents most simmilar to the query text.
        """
        if self._embedding_function is None:
            results = self._collection.query(
                query_texts=[query], n_results=k, where=filter
            )
        else:
            query_embedding = self._embedding_function.embed_query(query)
            results = self._collection.query(
                query_embeddings=[query_embedding], n_results=k, where=filter
            )

        docs = [
            # TODO: Chroma can do batch querying,
            # we shouldn't hard code to the 1st result
            Document(page_content=result[0], metadata=result[1])
            for result in zip(results["documents"][0], results["metadatas"][0])
        ]
        return docs

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Optional[Embeddings] = None,
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "langchain",
        **kwargs: Any,
    ) -> Chroma:
        """Create a Chroma vectorstore from a raw documents.

        Args:
            collection_name (str): Name of the collection to create.
            documents (List[Document]): List of documents to add.
            embedding (Optional[Embeddings]): Embedding function. Defaults to None.
            metadatas (Optional[List[dict]]): List of metadatas. Defaults to None.
            ids (Optional[List[str]]): List of document IDs. Defaults to None.

        Returns:
            Chroma: Chroma vectorstore.
        """
        chroma_collection = cls(
            collection_name=collection_name, embedding_function=embedding
        )
        chroma_collection.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        return chroma_collection

    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding: Optional[Embeddings] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "langchain",
        **kwargs: Any,
    ) -> Chroma:
        """Create a Chroma vectorstore from a list of documents.

        Args:
            collection_name (str): Name of the collection to create.
            documents (List[Document]): List of documents to add to the vectorstore.
            embedding (Optional[Embeddings]): Embedding function. Defaults to None.

        Returns:
            Chroma: Chroma vectorstore.
        """
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return cls.from_texts(
            collection_name=collection_name,
            texts=texts,
            embedding=embedding,
            metadatas=metadatas,
            ids=ids,
        )
