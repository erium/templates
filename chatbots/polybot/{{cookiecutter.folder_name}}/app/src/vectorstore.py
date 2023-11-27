# data handling, context finding, LLM
import configparser
from .environment import Environment
import errno
import json
from langchain.document_loaders import DirectoryLoader, UnstructuredFileIOLoader
from langchain.schema.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
import os
from pathlib import Path
from .prettyprint import prettyprint as pprint, MessageType as mt
import requests
from typing import List


class PromptServerEmbeddings(EmbeddingFunction):
    def __init__(self):
        # get path of config file
        script_dir = os.path.dirname(os.path.realpath(__file__))
        config_path = script_dir + '/../config.conf'
        config_dir = os.path.dirname(config_path)

        # set up configparser
        configs = configparser.ConfigParser()
        if not configs.read(config_path):
            raise FileNotFoundError("Unable to read the configuration file.")

        self.local = configs["app"]["local"] == True
        args = {}
        if self.local:
            args = {
                "base_url": "https://pro.halerium.ai",
                "tenant": "erium",
                "workspace": "64d22ad1c3c95e001224f120",
                "runner_id": "",
                "runner_token": "",
            }

        self.env = Environment(local=configs["app"]["local"] == "True", args=args)

    def __call__(self, input: Documents) -> Embeddings:
        """
        Embeds documents.

        Args:
            input (Documents): Documents to embed.

        Returns:
            Embeddings: Embedded documents.
        """
        return self.embed_documents(input)

    def embed_documents(self, documents: List[Document], q: bool = False) -> Embeddings:
        """
        Embeds chunks.

        Args:
            chunks (list): Chunked data.

        Returns:
            list: Embedded chunks.
        """
        try:
            # ensure that documents is a list
            docs = documents.copy()
            if not isinstance(docs, list):
                docs = [docs]

            # embed chunks
            for i, d in enumerate(docs):
                if isinstance(d, Document):
                    docs[i] = d.page_content

            pprint(f"Embedding {len(docs)} chunks.", type=mt.INFO)
            # call to prompt server
            response = requests.post(
                self.env.get_prompt_server_url(),
                json=self.env.build_embedding_payload(
                    text_chunks=list(docs), model_id="ada2-embedding"
                ),
                headers=self.env.build_prompt_server_headers(),
            )

            # collector list for embeddings
            embeddings = []
            prev_line = ""
            for line in response.text.splitlines():
                if prev_line == "event: embedding":
                    embeddings.append(json.loads(line[6:]).get("embedding"))
                prev_line = line

            # debugging: pprint dimensionality of each embedding
            # for i, e in enumerate(embeddings):
            #     pprint(f"{i}, {len(e)}")

        except Exception as e:
            pprint(f"Error while embedding chunks: {e}", type=mt.ERROR)
        else:
            if not q and not isinstance(documents, Document):
                pprint(f"Embedded {len(documents)} chunks.", type=mt.SUCCESS)
            elif not q and isinstance(documents, Document):
                pprint(f"Embedded query.", type=mt.SUCCESS)

        return embeddings

    def embed_query(self, q: str) -> List[float]:
        """
        Embeds a query.

        Args:
            q (str): Query.

        Returns:
            Embeddings: Embedded query.
        """

        pprint(f"Embedding query: {q}", type=mt.INFO)

        response = requests.post(
            self.env.get_prompt_server_url(),
            json=self.env.build_embedding_payload(
                text_chunks=[q], model_id="ada2-embedding"
            ),
            headers=self.env.build_prompt_server_headers(),
        )

        # collector list for embeddings
        embeddings = []
        prev_line = ""
        for line in response.text.splitlines():
            if prev_line == "event: embedding":
                embeddings += json.loads(line[6:]).get("embedding")
            prev_line = line

        return embeddings


class Builder:
    def __init__(self) -> None:

        # get path of config file
        script_dir = os.path.dirname(os.path.realpath(__file__))
        config_path = script_dir + '/../config.conf'
        config_dir = os.path.dirname(config_path)

        # set up configparser
        configs = configparser.ConfigParser()
        if not configs.read(config_path):
            raise FileNotFoundError("Unable to read the configuration file.")

        self.embedding_function = PromptServerEmbeddings()

        self.data_path = (
            os.path.dirname(os.path.realpath(__file__))
            + "/../"
            + configs["paths"]["data_dir"]
        )
        self.vs_path = (
            os.path.dirname(os.path.realpath(__file__))
            + "/../"
            + configs["paths"]["vs_dir"]
        )
        self.collection_name = "default"

    def load_directory(self, path: str = "", filetype: str = "") -> list:
        """
        Loads documents from a data directory and splits them into chunks.
        If no filetype is declared, all supported files will be used.

        Args:
            path (str): Path to data directory. Defaults to self.data_path.
            filetype (str, optional): Filetype (e.g. 'pdf'). Defaults to '' (all supported files).

        Returns:
            list: Chunked data.
        """
        if not path:
            path = self.data_path

        # raise error if path does not exist
        if not Path(path).exists():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)

        pprint(
            f"Loading {f'{filetype} files' if filetype else 'files'} from {path}",
            type=mt.INFO,
        )

        # add '.' to filetype for glob filter
        if filetype:
            filetype = f".{filetype}"

        loader = DirectoryLoader(path=path, glob=f"*{filetype}", show_progress=True)
        raw_docs = loader.load()

        return raw_docs

    def load_document(self, document) -> list:
        """
        Loads a single document and splits it into chunks.

        Args:
            document (Any): A document (e.g. a pdf file)

        Returns:
            list: Chunked data.
        """
        if isinstance(document, str):
            document = open(Path(document), "rb")

        pprint(f"Preparing document: {document.name}", type=mt.INFO)
        loader = UnstructuredFileIOLoader(document)
        raw_doc = loader.load()

        return raw_doc

    def create_chunks(self, document) -> list:
        """
        Splits a document into chunks.

        Args:
            document (Any): A document (e.g. a pdf file)

        Returns:
            list: Chunked data.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        chunks = text_splitter.split_documents(document)
        pprint(f"Chunked documents into {len(chunks)} chunks", type=mt.INFO)

        return chunks

    def from_halerium_chunks(self, path_to_dir: str) -> list:
        """
        Transforms the contents of a .chunks file into chunks.
        Format of the .chunks file should be:
        {"content": "chunk content", "metadata": {"key": "value"}}

        Args:
            path_to_dir (str): Path to directory containing .chunks file(s).

        Returns:
            list: chromadb readable chunks.
        """
        glob = Path(path_to_dir).glob("*.chunks")
        files = [file for file in glob]
        pprint(f"Found {len(files)} .chunks files.", type=mt.INFO)

        transformed_chunks = []
        for file in files:
            with open(Path(file), "r") as f:
                for line in f.readlines():
                    json_chunk = json.loads(line)
                    langchain_document_chunk = Document(
                        page_content=json_chunk["content"],
                        metadata=json_chunk["metadata"],
                    )
                    transformed_chunks.append(langchain_document_chunk)

        pprint(
            f"Transformed {len(transformed_chunks)} chunks from {len(files)} files.",
            type=mt.INFO,
        )

        return transformed_chunks

    def create_vector_db(self, documents: List[Document], persist: bool = False):
        """
        Embeds chunks and stores them in a non-persistent vector database.

        Args:
            documents (list): Chunked data.

        Returns:
            Chroma: Vector database.
        """
        args = {
            "collection_name": self.collection_name,
            "documents": documents,
            "embedding": self.embedding_function,
        }

        if persist:
            args["persist_directory"] = self.vs_path

        # create new collection
        chroma = chromadb.PersistentClient(path=self.vs_path)
        try:
            chroma.delete_collection(name=self.collection_name)
            pprint("Deleted existing collection.", type=mt.INFO)
        except Exception as e:
            pprint("No existing collection to delete")
        finally:
            chroma_coll = chroma.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"},
            )

        # embed chunks
        embeddings = self.embedding_function.embed_documents(documents, q=False)

        try:
            # add document, ids, and embeddings to db
            chroma_coll.add(
                ids=[str(i) for i in range(len(documents))],
                documents=[d.page_content for d in documents],
                embeddings=embeddings,
                metadatas=[d.metadata for d in documents],
            )
        except Exception as e:
            pprint(f"Error while adding embedded chunks to db: {e}", type=mt.ERROR)

        pprint("Created vectorDB.", type=mt.SUCCESS)

        if not persist:
            return chroma_coll

    def peek_vector_db(self, q: str):
        client = chromadb.PersistentClient(path=self.vs_path)
        chroma_coll = client.get_collection(
            name=self.collection_name, embedding_function=self.embedding_function
        )

        q_embs = self.embedding_function.embed_query(q)

        return chroma_coll.query(
            # query_texts=Document(page_content=q),
            query_embeddings=q_embs,
            n_results=4,
        )


if __name__ == "__main__":
    vs_builder = Builder()

    # create vector db from documents in a directory
    documents = vs_builder.load_directory()
    chunks = vs_builder.create_chunks(documents)
    vs_builder.create_vector_db(chunks, persist=True)