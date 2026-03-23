# examples/customer_analysis.py

import pandas as pd
import sqlite3
from viz_agent.agent import VizAgent
from viz_agent.models import VizAgentInput
from viz_agent.config import Config


def main():
    """Ejemplo de análisis de clientes con VizAgent - Gráficos de pie, box y heatmap"""
    
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
    
    # 3. EJEMPLO 1: Distribución de clientes por país (Pie Chart)
    print("\n" + "=" * 60)
    print("🥧 EJEMPLO 1: Distribución de clientes por país")
    print("=" * 60)
    
    conn = sqlite3.connect('tests/fixtures/chinook.db')
    df_countries = pd.read_sql_query("""
        SELECT 
            Country,
            COUNT(*) as CustomerCount,
            ROUND(SUM(Total), 2) as TotalRevenue
        FROM Customer c
        LEFT JOIN Invoice i ON c.CustomerId = i.CustomerId
        GROUP BY Country
        ORDER BY CustomerCount DESC
        LIMIT 10
    """, conn)
    
    print(df_countries)
    print(f"✅ Datos cargados: {df_countries.shape[0]} filas\n")
    
    input_data_1 = VizAgentInput(
        dataframe=df_countries,
        user_request="muestra la proporción de clientes por país",
    )
    
    print("🎨 Generando gráfico de pastel...")
    result_1 = agent.generate_visualization(input_data_1)
    
    if result_1.success:
        print("\n✅ Visualización 1 generada exitosamente!")
        print(f"📊 Tipo de gráfico: {result_1.chart_type}")
        print(f"⏱️  Tiempo: {result_1.metadata['execution_time']:.2f}s")
        print(f"💡 Razonamiento: {result_1.metadata['decision_reasoning']}")
        
        with open('output_customer_pie.json', 'w') as f:
            f.write(result_1.plotly_json)
        print("✅ JSON guardado en output_customer_pie.json")
    else:
        print(f"\n❌ Error: {result_1.error_message}")
    
    # 4. EJEMPLO 2: Distribución de valores de facturas (Box Plot)
    print("\n" + "=" * 60)
    print("📦 EJEMPLO 2: Distribución de valores de facturas por país")
    print("=" * 60)
    
    df_invoices = pd.read_sql_query("""
        SELECT 
            c.Country,
            i.Total as InvoiceAmount
        FROM Invoice i
        JOIN Customer c ON i.CustomerId = c.CustomerId
        WHERE c.Country IN ('USA', 'Canada', 'France', 'Germany', 'Brazil', 'UK')
        ORDER BY c.Country
    """, conn)
    
    print(f"✅ Datos cargados: {df_invoices.shape[0]} filas")
    print(f"Países únicos: {df_invoices['Country'].nunique()}\n")
    
    input_data_2 = VizAgentInput(
        dataframe=df_invoices,
        user_request="muestra la distribución de los montos de las facturas por país",
    )
    
    print("🎨 Generando diagrama de caja...")
    result_2 = agent.generate_visualization(input_data_2)
    
    if result_2.success:
        print("\n✅ Visualización 2 generada exitosamente!")
        print(f"📊 Tipo de gráfico: {result_2.chart_type}")
        print(f"⏱️  Tiempo: {result_2.metadata['execution_time']:.2f}s")
        print(f"💡 Razonamiento: {result_2.metadata['decision_reasoning']}")
        
        with open('output_customer_box.json', 'w') as f:
            f.write(result_2.plotly_json)
        print("✅ JSON guardado en output_customer_box.json")
    else:
        print(f"\n❌ Error: {result_2.error_message}")
    
    # 5. EJEMPLO 3: Histograma de duración de canciones
    print("\n" + "=" * 60)
    print("📊 EJEMPLO 3: Distribución de duración de canciones")
    print("=" * 60)
    
    df_tracks = pd.read_sql_query("""
        SELECT 
            t.Name as TrackName,
            ROUND(Milliseconds / 1000.0 / 60.0, 2) as DurationMinutes,
            g.Name as Genre
        FROM Track t
        JOIN Genre g ON t.GenreId = g.GenreId
        WHERE t.Milliseconds > 0
        LIMIT 500
    """, conn)
    conn.close()
    
    print(f"✅ Datos cargados: {df_tracks.shape[0]} filas")
    print(f"Duración promedio: {df_tracks['DurationMinutes'].mean():.2f} minutos\n")
    
    input_data_3 = VizAgentInput(
        dataframe=df_tracks,
        user_request="quiero ver la distribución de la duración de las canciones en minutos",
    )
    
    print("🎨 Generando histograma...")
    result_3 = agent.generate_visualization(input_data_3)
    
    if result_3.success:
        print("\n✅ Visualización 3 generada exitosamente!")
        print(f"📊 Tipo de gráfico: {result_3.chart_type}")
        print(f"⏱️  Tiempo: {result_3.metadata['execution_time']:.2f}s")
        print(f"💡 Razonamiento: {result_3.metadata['decision_reasoning']}")
        
        print("\n--- Código Generado ---")
        print(result_3.plotly_code)
        
        with open('output_customer_histogram.json', 'w') as f:
            f.write(result_3.plotly_json)
        print("\n✅ JSON guardado en output_customer_histogram.json")
    else:
        print(f"\n❌ Error: {result_3.error_message}")
    
    # 6. Resumen
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE VISUALIZACIONES")
    print("=" * 60)
    print(f"✅ Visualización 1 (Pie Chart): {'Éxito' if result_1.success else 'Fallo'}")
    print(f"✅ Visualización 2 (Box Plot): {'Éxito' if result_2.success else 'Fallo'}")
    print(f"✅ Visualización 3 (Histogram): {'Éxito' if result_3.success else 'Fallo'}")
    print("\n💾 Archivos generados:")
    print("   - output_customer_pie.json")
    print("   - output_customer_box.json")
    print("   - output_customer_histogram.json")


if __name__ == "__main__":
    main()
