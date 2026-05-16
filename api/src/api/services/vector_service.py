"""
vector_service.py — Servicio para manejo de embeddings y búsqueda semántica con pgvector.

Optimiza el pipeline evitando regenerar SQL para consultas idénticas o muy similares.
"""

import uuid
from typing import Optional, List, Tuple
import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from google import genai
from google.genai import types

from api.models.database import QueryVector, SchemaDocumentation
from api.models.schemas import ResponseType
from api.config import Settings

class VectorService:
    """
    Servicio para persistencia y recuperación de consultas basadas en vectores.
    """

    def __init__(self, settings: Optional[Settings] = None):
        if settings is None:
            settings = Settings()
        
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = "gemini-embedding-2"
        self.dimension = 768

    async def get_embedding(self, text_input: str) -> List[float]:
        """ Genera el embedding para un texto dado usando Gemini. """
        response = self.client.models.embed_content(
            model=self.model_id,
            contents=[text_input],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self.dimension
            )
        )
        embedding = response.embeddings[0].values
        return embedding

    async def find_similar_query(
        self, 
        db: AsyncSession, 
        query_text: str, 
        threshold: float = 0.95
    ) -> Optional[QueryVector]:
        """
        Busca una consulta similar en la base de datos.
        Usa la distancia de coseno (o producto escalar si están normalizados).
        """
        embedding = await self.get_embedding(query_text)
        
        # pgvector query: <=> is cosine distance
        # threshold is similarity, so distance < (1 - threshold)
        stmt = select(QueryVector).order_by(
            QueryVector.embedding.cosine_distance(embedding)
        ).limit(1)
        
        result = await db.execute(stmt)
        similar = result.scalar_one_or_none()
        
        if similar:
            # Calculamos la similitud manual si es necesario o confiamos en el orden
            # Para estar seguros del threshold, podemos hacer un fetch de la distancia
            # Pero por ahora confiamos en que si está muy cerca es válido.
            # Vamos a refinar para verificar el threshold real:
            
            distance_stmt = select(QueryVector.embedding.cosine_distance(embedding)).where(QueryVector.id == similar.id)
            distance_res = await db.execute(distance_stmt)
            distance = distance_res.scalar()
            
            if distance is not None and (1 - distance) >= threshold:
                return similar
                
        return None

    async def save_query_vector(
        self, 
        db: AsyncSession, 
        query: str, 
        sql: str,
        cached_response: Optional[dict] = None,
        response_type: Optional[str] = None
    ) -> QueryVector:
        """ Guarda una nueva consulta y su SQL asociado con su embedding. """
        embedding = await self.get_embedding(query)
        
        new_vector = QueryVector(
            query=query,
            embedding=embedding,
            sql=sql,
            cached_response=cached_response,
            response_type=response_type
        )
        
        db.add(new_vector)
        await db.commit()
        return new_vector

    async def find_relevant_schema_docs(
        self,
        db: AsyncSession,
        query_text: str,
        limit: int = 7
    ) -> List[SchemaDocumentation]:
        """
        Busca documentos de esquema (tablas y columnas) relevantes para la consulta.
        """
        embedding = await self.get_embedding(query_text)
        
        stmt = select(SchemaDocumentation).order_by(
            SchemaDocumentation.embedding.cosine_distance(embedding)
        ).limit(limit)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
        
    async def save_schema_doc(
        self,
        db: AsyncSession,
        table_name: str,
        column_name: Optional[str],
        description: str
    ) -> SchemaDocumentation:
        """ Guarda un nuevo documento de esquema con su embedding. """
        # Embeber la descripción junto con el nombre de tabla/columna para mayor contexto
        text_to_embed = f"Tabla: {table_name}"
        if column_name:
            text_to_embed += f", Columna: {column_name}"
        text_to_embed += f". Descripción: {description}"
        
        embedding = await self.get_embedding(text_to_embed)
        
        new_doc = SchemaDocumentation(
            table_name=table_name,
            column_name=column_name,
            description=description,
            embedding=embedding
        )
        
        db.add(new_doc)
        await db.commit()
        return new_doc
