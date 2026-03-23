# examples/temporal_analysis.py

import pandas as pd
import sqlite3
from viz_agent.agent import VizAgent
from viz_agent.models import VizAgentInput
from viz_agent.config import Config


def main():
    """Ejemplo de análisis temporal con VizAgent - Gráficos de línea y scatter"""
    
    # 1. Cargar configuración
    config = Config.from_env()
    
    # Verificar que tenemos API key
    if not config.gemini_api_key:
        print("❌ Error: GEMINI_API_KEY no configurada")
        print("Por favor, configura tu API key en el archivo .env")
        return
    
    # 2. Crear agente
    print("🤖 Inicializando VizAgent...")
    agent = VizAgent(config)
    
    # 3. Cargar datos de ventas mensuales de Chinook
    print("📊 Cargando datos de ventas temporales de Chinook...")
    conn = sqlite3.connect('tests/fixtures/chinook.db')
    
    # Query para obtener ventas por mes
    df = pd.read_sql_query("""
        SELECT 
            strftime('%Y-%m', i.InvoiceDate) as Month,
            COUNT(DISTINCT i.InvoiceId) as Orders,
            SUM(i.Total) as Revenue,
            ROUND(AVG(i.Total), 2) as AvgOrderValue
        FROM Invoice i
        GROUP BY strftime('%Y-%m', i.InvoiceDate)
        ORDER BY Month
    """, conn)
    conn.close()
    
    print(df.head())
    print(f"✅ Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
    print(f"Columnas: {df.columns.tolist()}\n")
    
    # 4. Ejemplo 1: Gráfico de línea - Evolución de ingresos
    print("=" * 60)
    print("📈 EJEMPLO 1: Evolución temporal de ingresos")
    print("=" * 60)
    
    input_data_1 = VizAgentInput(
        dataframe=df,
        user_request="muestra la evolución de los ingresos a lo largo del tiempo",
    )
    
    print("🎨 Generando visualización de línea temporal...")
    result_1 = agent.generate_visualization(input_data_1)
    
    if result_1.success:
        print("\n✅ Visualización 1 generada exitosamente!")
        print(f"📊 Tipo de gráfico: {result_1.chart_type}")
        print(f"🔄 Intentos: {result_1.metadata['attempts']}")
        print(f"⏱️  Tiempo de ejecución: {result_1.metadata['execution_time']:.2f}s")
        print(f"💡 Razonamiento: {result_1.metadata['decision_reasoning']}")
        
        print("\n--- Código Generado ---")
        print(result_1.plotly_code)
        
        # Guardar JSON
        with open('output_temporal_line.json', 'w') as f:
            f.write(result_1.plotly_json)
        print("\n✅ JSON guardado en output_temporal_line.json")
    else:
        print("\n❌ Visualización 1 fallida")
        print(f"Error: {result_1.error_message}")
    
    # 5. Ejemplo 2: Scatter plot - Relación entre órdenes y valor promedio
    print("\n" + "=" * 60)
    print("📊 EJEMPLO 2: Relación entre cantidad de órdenes y ticket promedio")
    print("=" * 60)
    
    input_data_2 = VizAgentInput(
        dataframe=df,
        user_request="muestra la relación entre el número de órdenes y el valor promedio de cada orden por mes",
    )
    
    print("🎨 Generando visualización de dispersión...")
    result_2 = agent.generate_visualization(input_data_2)
    
    if result_2.success:
        print("\n✅ Visualización 2 generada exitosamente!")
        print(f"📊 Tipo de gráfico: {result_2.chart_type}")
        print(f"🔄 Intentos: {result_2.metadata['attempts']}")
        print(f"⏱️  Tiempo de ejecución: {result_2.metadata['execution_time']:.2f}s")
        print(f"💡 Razonamiento: {result_2.metadata['decision_reasoning']}")
        
        print("\n--- Código Generado ---")
        print(result_2.plotly_code)
        
        # Guardar JSON
        with open('output_temporal_scatter.json', 'w') as f:
            f.write(result_2.plotly_json)
        print("\n✅ JSON guardado en output_temporal_scatter.json")
    else:
        print("\n❌ Visualización 2 fallida")
        print(f"Error: {result_2.error_message}")
    
    # 6. Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE VISUALIZACIONES")
    print("=" * 60)
    print(f"✅ Visualización 1 (Temporal): {'Éxito' if result_1.success else 'Fallo'}")
    print(f"✅ Visualización 2 (Scatter): {'Éxito' if result_2.success else 'Fallo'}")
    print("\n💾 Archivos generados:")
    print("   - output_temporal_line.json")
    print("   - output_temporal_scatter.json")


if __name__ == "__main__":
    main()
