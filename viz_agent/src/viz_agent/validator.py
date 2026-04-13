# viz_agent/validator.py

import sys
import io
import re
import traceback
from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from .models import ValidationResult


class CodeValidator:
    """Valida y ejecuta código Plotly en un sandbox controlado"""
    
    def execute_and_validate(
        self,
        code: str,
        dataframe: pd.DataFrame
    ) -> ValidationResult:
        """Ejecuta el código y valida el resultado"""

        # 0. Rechazar código que redefina 'df' (usa datos falsos en lugar del real)
        df_error = self._check_df_redefinition(code)
        if df_error:
            return df_error

        # 1. Crear namespace sandbox
        sandbox_namespace = {
            'pd': pd,
            'px': px,
            'go': go,
            'df': dataframe,  # El DataFrame está disponible como 'df'
            '__builtins__': __builtins__
        }
        
        # 2. Capturar stdout/stderr para evitar prints molestos
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        
        try:
            # 3. Ejecutar código
            exec(code, sandbox_namespace)
            
            # 4. Buscar la figura generada
            fig = self._extract_figure(sandbox_namespace)
            
            if fig is None:
                return ValidationResult(
                    success=False,
                    error_type="runtime",
                    error_message="No Plotly figure found in executed code. Make sure to create a variable named 'fig'."
                )
            
            # 5. Validar que la figura tenga datos
            if not self._figure_has_data(fig):
                return ValidationResult(
                    success=False,
                    error_type="empty",
                    error_message="Generated figure has no data/traces"
                )
            
            # 6. Todo OK
            return ValidationResult(
                success=True,
                figure=fig
            )
        
        except SyntaxError as e:
            return ValidationResult(
                success=False,
                error_type="syntax",
                error_message=str(e),
                traceback=traceback.format_exc()
            )
        
        except Exception as e:
            return ValidationResult(
                success=False,
                error_type="runtime",
                error_message=str(e),
                traceback=traceback.format_exc()
            )
        
        finally:
            # Restaurar stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def _extract_figure(self, namespace: dict) -> Optional[go.Figure]:
        """Busca la figura Plotly en el namespace"""
        
        # Buscar variable 'fig' (convención)
        if 'fig' in namespace and isinstance(namespace['fig'], (go.Figure, type(px.bar()))):
            return namespace['fig']
        
        # Buscar cualquier objeto Figure en el namespace
        for value in namespace.values():
            if isinstance(value, (go.Figure, type(px.bar()))):
                return value
        
        return None
    
    def _figure_has_data(self, fig: go.Figure) -> bool:
        """Verifica que la figura tenga datos"""
        
        if not hasattr(fig, 'data'):
            return False
        
        if len(fig.data) == 0:
            return False
        
        # Verificar que al menos un trace tenga datos
        for trace in fig.data:
            if hasattr(trace, 'x') and len(trace.x) > 0:
                return True
            if hasattr(trace, 'y') and len(trace.y) > 0:
                return True
            if hasattr(trace, 'values') and len(trace.values) > 0:
                return True
        
        return False

    def _check_df_redefinition(self, code: str) -> Optional[ValidationResult]:
        """
        Detecta si el código intenta redefinir la variable 'df'.

        El DataFrame real se inyecta en el sandbox antes de exec(); si el código
        lo sobreescribe con datos simulados, el gráfico se genera con data falsa.
        """
        # Busca asignaciones directas: df = ... o df=...
        # Ignora accesos como df.copy(), df.groupby(), df_sorted = ...
        pattern = re.compile(r'^\s*df\s*=', re.MULTILINE)
        if pattern.search(code):
            return ValidationResult(
                success=False,
                error_type="runtime",
                error_message=(
                    "The code redefines the 'df' variable with mock/sample data. "
                    "You must use the existing 'df' variable directly — it is already "
                    "loaded with the real query results. Remove any 'df = pd.DataFrame(...)' "
                    "or similar assignments and use 'df' as-is."
                ),
            )
        return None
