import asyncio
import logging
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from api.db.engine import get_engine, get_session_factory
from api.services.vector_service import VectorService
from api.models.database import SchemaDocumentation
from google import genai
from api.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schema_enhancer")

async def main():
    settings = Settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    model_id = settings.GEMINI_MODEL
    vector_service = VectorService(settings)
    
    schema_name = "bigenia"
    
    def get_db_schema(conn):
        inspector = inspect(conn)
        schemas = inspector.get_schema_names()
        target_schema = schema_name if schema_name in schemas else None
        
        tables_info = {}
        for table_name in inspector.get_table_names(schema=target_schema):
            if table_name in ["alembic_version", "schema_documentation", "sessions", "projects", "conversation_messages", "charts", "query_vectors"]:
                continue
            
            columns = inspector.get_columns(table_name, schema=target_schema)
            fks = inspector.get_foreign_keys(table_name, schema=target_schema)
            
            tables_info[table_name] = {
                "columns": [col["name"] for col in columns],
                "fks": fks
            }
        return tables_info

    engine = get_engine(settings)
    async_session_maker = get_session_factory(settings)
    
    from sqlalchemy import create_engine
    source_engine = create_engine(settings.SOURCE_DB_URL)
    
    with source_engine.connect() as conn:
        tables_info = get_db_schema(conn)
        
    source_engine.dispose()

    async with async_session_maker() as session:
        result = await session.execute(select(SchemaDocumentation.table_name, SchemaDocumentation.column_name))
        existing_docs = set((row[0], row[1]) for row in result.all())
        
        items_to_document = []
        for table, info in tables_info.items():
            if (table, None) not in existing_docs:
                items_to_document.append((table, None, info))
            for col in info["columns"]:
                if (table, col) not in existing_docs:
                    items_to_document.append((table, col, info))
                    
        obsolete_ids = []
        result = await session.execute(select(SchemaDocumentation.id, SchemaDocumentation.table_name, SchemaDocumentation.column_name))
        for row in result.all():
            doc_id, t_name, c_name = row
            if t_name not in tables_info:
                obsolete_ids.append(doc_id)
            elif c_name is not None and c_name not in tables_info[t_name]["columns"]:
                obsolete_ids.append(doc_id)
                
        if obsolete_ids:
            logger.info(f"Eliminando {len(obsolete_ids)} documentos obsoletos...")
            await session.execute(delete(SchemaDocumentation).where(SchemaDocumentation.id.in_(obsolete_ids)))
            await session.commit()
            
        if not items_to_document:
            logger.info("El esquema está completamente documentado. No hay novedades.")
            return

        logger.info(f"Se encontraron {len(items_to_document)} elementos nuevos para documentar.")
        
        for table, col, info in items_to_document:
            prompt = ""
            if col is None:
                prompt = (
                    f"Eres un experto analista de bases de datos. "
                    f"Explica brevemente (1 o 2 oraciones) cuál es el propósito de la tabla '{table}' en un sistema de negocio. "
                    f"Las columnas que tiene son: {', '.join(info['columns'])}. "
                    f"No uses formato markdown."
                )
            else:
                prompt = (
                    f"Eres un experto analista de bases de datos. "
                    f"Explica brevemente (1 o 2 oraciones) qué representa la columna '{col}' dentro de la tabla '{table}'. "
                    f"No uses formato markdown."
                )
                
            logger.info(f"Generando documentación para {table} - {col}...")
            
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                )
                description = response.text.strip()
                
                await vector_service.save_schema_doc(session, table, col, description)
            except Exception as e:
                logger.error(f"Error generando docs para {table} - {col}: {e}")
                
        logger.info("Enriquecimiento semántico completado con éxito.")

if __name__ == "__main__":
    asyncio.run(main())
