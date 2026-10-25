"""Generate project API appendix directly from source signatures and docstrings."""
import ast
from pathlib import Path

output=['# 프로젝트 함수와 파라미터 API 부록','',
        '자동 추출: `python3 scripts/document_api.py`. 각 함수의 파라미터 의미와 알고리즘 배경은 METHODS_EXPLAINED.md와 함께 읽는다.','']
for path in sorted(Path('src/perfume').glob('*.py')):
    module=ast.parse(path.read_text())
    output.extend([f'## {path}','',ast.get_docstring(module) or '', ''])
    for node in module.body:
        if isinstance(node,ast.ClassDef):
            output.extend([f'### {node.name}','',ast.get_docstring(node) or '', ''])
            functions=[n for n in node.body if isinstance(n,ast.FunctionDef)]
        elif isinstance(node,ast.FunctionDef): functions=[node]
        else: continue
        for function in functions:
            output.extend([f'`{function.name}({ast.unparse(function.args)})`','',ast.get_docstring(function) or '문서화 필요',''])
Path('reports/API_REFERENCE.md').write_text('\n'.join(output))
