"""
agent.py — VannaAgent, wrapper sobre Vanna AI para integrarlo al ecosistema.

Referencia: plan.md §Vanna Agent, tasks.md T020
"""

from __future__ import annotations

import pandas as pd
from vanna.integrations.google import GeminiLlmService
from vanna.integrations.postgres import PostgresRunner
from vanna.tools import RunSqlTool

from vanna_agent.config import Settings
from vanna_agent.models import Text2SQLInput, Text2SQLOutput


class VannaAgent:
    """Wrapper de Vanna AI especializado en conversiones Text2SQL para Postgres con Gemini."""

    def __init__(self, settings: Settings | None = None) -> None:
        if settings is None:
            settings = Settings()  # type: ignore[call-arg]

        # Inicializar el servicio LLM de Gemini (vanna.integrations.google)
        self.llm = GeminiLlmService(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )
        
        # Inicializar el runner para ejecutar el SQL en PostgreSQL (Chinook)
        self.sql_runner = PostgresRunner(connection_string=settings.SOURCE_DB_URL)
        
        # Instanciar la herramienta que envuelve la ejecución SQL
        self.run_sql_tool = RunSqlTool(sql_runner=self.sql_runner)

    def text_to_sql(self, query: str) -> Text2SQLOutput:
        """
        Traduce una pregunta en lenguaje natural a código SQL
        usando Vanna AI y la API de Google Gemini.

        Args:
            query: La consulta en lenguaje natural (NL).

        Returns:
            Text2SQLOutput indicando el éxito fallido con el SQL, si aplica.
        """
        try:
            from vanna import LlmMessage, LlmRequest, User
            
            # Construir petición directa al LLM usando la nueva interfaz de Vanna (LlmRequest)
            # Solicitamos directamente el SQL para luego validarlo nosotros (en DecisionAgent),
            # sin ejecutar herramientas automáticamente aún.
            req = LlmRequest(
                messages=[LlmMessage(role="user", content=query)],
                user=User(id="decision_agent", role="system"),
                system_prompt=(
                    "Eres un experto en PostgreSQL especializado en traducir lenguaje natural a consultas SQL. "
                    "Tu tarea: Dada la petición del usuario, generar una sentencia SELECT válida y optimizada.\n\n"
                    "REGLAS ESTRICTAS E INQUEBRANTABLES:\n"
                    "1. FORMATO RAW: Tu respuesta DEBE ser ÚNICAMENTE código SQL en texto plano. Tienes prohibido "
                    "incluir saludos, explicaciones o etiquetas de código (no uses ```sql).\n"
                    "2. ESQUEMA OBLIGATORIO: Todas las tablas DEBEN usar obligatoriamente el esquema 'bigenia'. "
                    "ESTÁ ESTRICTAMENTE PROHIBIDO usar el esquema 'public' o dejar la tabla sin esquema. "
                    "Si el contexto sugiere 'public', ignóralo y usa 'bigenia'.\n"
                    "3. IDENTIFICADORES: Asume PascalCase o camelCase. En PostgreSQL, DEBES envolver siempre el "
                    "esquema, las tablas y las columnas en comillas dobles.\n"
                    "   - Formato CORRECTO: \"bigenia\".\"NombreDeTabla\"\n"
                    "   - Formato PROHIBIDO: public.\"NombreDeTabla\" o \"NombreDeTabla\"\n"
                    "   - Ejemplo de uso: SELECT \"TotalAmount\" FROM \"bigenia\".\"Invoice\"\n"
                    "4. SEGURIDAD: Solo genera sentencias SELECT. DML/DDL prohibidos."
                ),
                temperature=0.0
            )
            
            import asyncio
            
            # send_request en GeminiLlmService es asíncrono
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
                
            if loop and loop.is_running():
                # Estamos dentro de un event loop existente, usamos create_task si no podemos bloquear,
                # pero idealmente esto se llama desde un ThreadPoolExecutor en FastAPI
                import nest_asyncio
                nest_asyncio.apply()
                response = asyncio.run(self.llm.send_request(req))
            else:
                response = asyncio.run(self.llm.send_request(req))
            
            # Limpiar el output en caso de que el LLM incluya tags markdown 
            sql_result = response.content.strip() if response.content else ""
            if sql_result.startswith("```sql"):
                sql_result = sql_result[6:]
            if sql_result.endswith("```"):
                sql_result = sql_result[:-3]
            
            sql_result = sql_result.strip()

            return Text2SQLOutput(
                query=query,
                sql=sql_result,
                success=True,
            )
        except Exception as e:
            return Text2SQLOutput(
                query=query,
                success=False,
                error=str(e)
            )

    def execute_sql(self, sql: str) -> pd.DataFrame:
        """
        Ejecuta la sentencia SQL validada sobre Chinook PostgreSQL.

        Args:
            sql: Sentencia en crudo que DEBE haber sido validada (solo lectura SELECT).

        Returns:
            pandas.DataFrame con los datos extraídos de la BD PostgreSQL.
        """
        # Delegar ejecución real vía PostgresRunner usando la API formal de Vanna v2
        try:
            from vanna.capabilities.sql_runner.models import RunSqlToolArgs
            import asyncio

            args = RunSqlToolArgs(sql=sql)
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                result = asyncio.run(self.sql_runner.run_sql(args=args, context=None)) # type: ignore
            else:
                result = asyncio.run(self.sql_runner.run_sql(args=args, context=None)) # type: ignore
                
            if not isinstance(result, pd.DataFrame):
                result = pd.DataFrame(result)
                
            # Sanitizar tipos de PostgreSQL (como Decimal) a tipos nativos para evitar fallos JSON en VizAgent
            from decimal import Decimal
            for col in result.columns:
                result[col] = result[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)
                
            return result
        except Exception as e:
            # Rethrow o convertir la excepción, quien llama deberá manejar esto 
            # (Ej. en el decision_agent.run() y PipelineError)
            raise Exception(f"Fallo al ejecutar SQL en VannaAgent: {e}") from e
