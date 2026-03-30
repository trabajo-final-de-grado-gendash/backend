# examples/basic_usage.py

import pandas as pd
import sqlite3
from viz_agent.agent import VizAgent
from viz_agent.models import VizAgentInput
from viz_agent.config import Settings


def main():
    """Ejemplo básico de uso del VizAgent"""
    
    # 1. Cargar configuración
    settings = Settings()
    
    # Verificar que tenemos API key
    if not settings.GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY no configurada")
        print("Por favor, configura tu API key en el archivo .env")
        return
    
    # 2. Crear agente
    print("🤖 Inicializando VizAgent...")
    agent = VizAgent(config)
    
    # 3. Cargar datos de Chinook
    print("📊 Cargando datos de Chinook...")
    conn = sqlite3.connect('tests/fixtures/chinook.db')
    df = pd.read_sql_query("""
        SELECT g.Name as Genre, SUM(il.UnitPrice * il.Quantity) as Total
        FROM Genre g
        JOIN Track t ON g.GenreId = t.GenreId
        JOIN InvoiceLine il ON t.TrackId = il.TrackId
        GROUP BY g.Name
        ORDER BY Total DESC
        LIMIT 10
    """, conn)
    conn.close()
    print(df.head())
    print(f"✅ Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
    print(f"Columnas: {df.columns.tolist()}\n")
    
    # 4. Crear input
    input_data = VizAgentInput(
        dataframe=df,
        user_request="gráfico de ventas totales por género musical",
        allowed_charts=["bar", "line", "pie", "scatter", "histogram", "heatmap", "box"]
    )
    
    # 5. Generar visualización
    print("🎨 Generando visualización...")
    result = agent.generate_visualization(input_data)
    
    # 6. Procesar resultado
    if result.success:
        print("\n✅ Visualización generada exitosamente!")
        print(f"📊 Tipo de gráfico: {result.chart_type}")
        print(f"🔄 Intentos: {result.metadata['attempts']}")
        print(f"⏱️  Tiempo de ejecución: {result.metadata['execution_time']:.2f}s")
        print(f"💡 Razonamiento: {result.metadata['decision_reasoning']}")
        
        if result.metadata['corrections_made']:
            print(f"🔧 Correcciones realizadas: {len(result.metadata['corrections_made'])}")
        
        print("\n--- Código Generado ---")
        print(result.plotly_code)
        
        # Guardar JSON
        with open('output.json', 'w') as f:
            f.write(result.plotly_json)
        print("\n✅ JSON guardado en output.json")
        
        # Opcionalmente, renderizar el gráfico
        # try:
        #     import plotly.io as pio
        #     import json
        #     fig_dict = json.loads(result.plotly_json)
        #     pio.show(fig_dict)
        #     print("🌐 Gráfico abierto en el navegador")
        # except Exception as e:
        #     print(f"⚠️  No se pudo abrir el gráfico: {e}")
    else:
        print("\n❌ Visualización fallida")
        print(f"Error: {result.error_message}")
        if result.metadata.get("last_code"):
            print("\n--- Último Código Generado ---")
            print(result.metadata["last_code"])


if __name__ == "__main__":
    main()
