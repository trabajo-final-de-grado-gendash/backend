"""
Ejemplo: Cargar y visualizar un gráfico desde output.json
"""
import json
import plotly.graph_objects as go
import plotly.io as pio

# Leer el JSON
names = [
    "output_temporal_line",
    "output_temporal_scatter",
    "output_customer_pie",
    "output_customer_box",
    "output_customer_histogram"
]
for name in names:
    with open(f"{name}.json", "r", encoding="utf-8") as f:
        fig_dict = json.load(f)

    # Reconstruir el Figure de Plotly
    fig = go.Figure(fig_dict)

    # Mostrar en el navegador
    fig.show()


    # O guardar como imagen estática (requiere kaleido)
    fig.write_image(f"{name}.png")
