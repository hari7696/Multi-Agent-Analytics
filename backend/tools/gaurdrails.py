import ast
import re
from typing import List, Dict, Any
from config import logger

def validate_code(code: str) -> dict:
    """Validate Python code for safety and correctness with improved detection."""
    logger.info(f"[GUARDRAILS] Starting code validation. Code length: {len(code)} characters")
    
    issues = []
    
    # Check syntax first
    try:
        logger.debug("[GUARDRAILS] Parsing code with AST")
        tree = ast.parse(code)
        logger.debug("[GUARDRAILS] Code syntax is valid")
    except SyntaxError as e:
        logger.error(f"[GUARDRAILS] Syntax error detected: {e}")
        return {"valid": False, "error": f"Syntax error: {e}"}
    
    # Advanced AST-based validation for dangerous functions
    logger.debug("[GUARDRAILS] Checking for dangerous function calls")
    dangerous_functions = _find_dangerous_function_calls(tree)
    if dangerous_functions:
        logger.warning(f"[GUARDRAILS] Found dangerous function calls: {dangerous_functions}")
        issues.extend([f"Dangerous function call: {func}" for func in dangerous_functions])
    
    # Check for dangerous imports
    logger.debug("[GUARDRAILS] Checking for dangerous imports")
    dangerous_imports = _find_dangerous_imports(tree)
    if dangerous_imports:
        logger.warning(f"[GUARDRAILS] Found dangerous imports: {dangerous_imports}")
        issues.extend([f"Forbidden import: {imp}" for imp in dangerous_imports])
    
    # Check for result assignment
    logger.debug("[GUARDRAILS] Checking for result variable assignment")
    if not _has_result_assignment(tree):
        logger.warning("[GUARDRAILS] Code does not assign output to 'result' variable")
        issues.append("Code must assign output to 'result' variable")
    
    # Check for file/network operations (more precise)
    logger.debug("[GUARDRAILS] Checking for file operations")
    file_operations = _find_file_operations(tree)
    if file_operations:
        logger.warning(f"[GUARDRAILS] Found file operations: {file_operations}")
        issues.extend([f"File operation not allowed: {op}" for op in file_operations])
    
    # NEW: Validate SQL queries for safety
    logger.debug("[GUARDRAILS] Checking for dangerous SQL operations")
    sql_issues = _validate_sql_queries(tree, code)
    if sql_issues:
        logger.warning(f"[GUARDRAILS] Found dangerous SQL operations: {sql_issues}")
        issues.extend(sql_issues)
    
    if issues:
        logger.error(f"[GUARDRAILS] Code validation failed with {len(issues)} issues: {issues}")
        return {"valid": False, "issues": issues}
    
    logger.info("[GUARDRAILS] Code validation passed successfully")
    return {"valid": True}

def _find_dangerous_function_calls(tree: ast.AST) -> List[str]:
    """Find actual dangerous function calls using AST analysis."""
    logger.debug("[GUARDRAILS] Scanning for dangerous function calls")
    dangerous_calls = []
    
    # These are actually dangerous when called as functions
    dangerous_functions = {
        'eval', 'exec', '__import__', 'compile', 'open', 'input', 
        'raw_input', 'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr'
    }
    
    class FunctionCallVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                if node.func.id in dangerous_functions:
                    dangerous_calls.append(node.func.id)
                    logger.debug(f"[GUARDRAILS] Found dangerous function call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                # Check for method calls like os.system()
                if hasattr(node.func, 'attr'):
                    if node.func.attr in {'system', 'popen', 'spawn', 'fork'}:
                        dangerous_calls.append(f"{node.func.attr}")
                        logger.debug(f"[GUARDRAILS] Found dangerous method call: {node.func.attr}")
            self.generic_visit(node)
    
    visitor = FunctionCallVisitor()
    visitor.visit(tree)
    logger.debug(f"[GUARDRAILS] Dangerous function calls found: {dangerous_calls}")
    return dangerous_calls

def _find_dangerous_imports(tree: ast.AST) -> List[str]:
    """Find dangerous module imports."""
    logger.debug("[GUARDRAILS] Scanning for dangerous imports")
    dangerous_imports = []
    
    # Modules that should not be imported
    forbidden_modules = {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'urllib2', 'urllib3',
        'requests', 'http', 'ftplib', 'smtplib', 'telnetlib', 'xmlrpc',
        'pickle', 'cPickle', 'marshal', 'shelve', 'dbm', 'anydbm',
        'ctypes', 'imp', 'importlib', '__builtin__', 'builtins'
    }
    
    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                if alias.name.split('.')[0] in forbidden_modules:
                    dangerous_imports.append(alias.name)
                    logger.debug(f"[GUARDRAILS] Found dangerous import: {alias.name}")
        
        def visit_ImportFrom(self, node):
            if node.module and node.module.split('.')[0] in forbidden_modules:
                dangerous_imports.append(node.module)
                logger.debug(f"[GUARDRAILS] Found dangerous import from: {node.module}")
    
    visitor = ImportVisitor()
    visitor.visit(tree)
    logger.debug(f"[GUARDRAILS] Dangerous imports found: {dangerous_imports}")
    return dangerous_imports

def _find_file_operations(tree: ast.AST) -> List[str]:
    """Find file operations that should be blocked."""
    logger.debug("[GUARDRAILS] Scanning for file operations")
    file_ops = []
    
    class FileOpVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # Check for file operations
            if isinstance(node.func, ast.Name):
                if node.func.id in {'open', 'file'}:
                    file_ops.append(node.func.id)
                    logger.debug(f"[GUARDRAILS] Found file operation: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                # Check for file-related method calls
                if hasattr(node.func, 'attr'):
                    if node.func.attr in {'read', 'write', 'open', 'close'} and \
                       self._looks_like_file_operation(node):
                        file_ops.append(f"file.{node.func.attr}")
                        logger.debug(f"[GUARDRAILS] Found file method call: {node.func.attr}")
            self.generic_visit(node)
        
        def _looks_like_file_operation(self, node):
            # Simple heuristic to detect file operations
            # This could be made more sophisticated
            return True
    
    visitor = FileOpVisitor()
    visitor.visit(tree)
    logger.debug(f"[GUARDRAILS] File operations found: {file_ops}")
    return file_ops

def _has_result_assignment(tree: ast.AST) -> bool:
    """Check if code assigns to 'result' variable."""
    logger.debug("[GUARDRAILS] Checking for result variable assignment")
    
    class ResultAssignmentVisitor(ast.NodeVisitor):
        def __init__(self):
            self.has_result = False
        
        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'result':
                    self.has_result = True
                    logger.debug("[GUARDRAILS] Found result variable assignment")
            self.generic_visit(node)
    
    visitor = ResultAssignmentVisitor()
    visitor.visit(tree)
    logger.debug(f"[GUARDRAILS] Result variable assignment found: {visitor.has_result}")
    return visitor.has_result

def _validate_sql_queries(tree: ast.AST, code: str) -> List[str]:
    """Validate SQL queries for dangerous keywords - simple and effective."""
    logger.debug("[GUARDRAILS] Starting SQL query validation")
    sql_issues = []
    
    # Dangerous SQL keywords that should never appear in read-only queries
    dangerous_keywords = {
        'DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE', 'ALTER', 
        'CREATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
        'xp_cmdshell', 'sp_executesql', 'BACKUP', 'RESTORE', 'MERGE'
    }
    
    # Extract all string constants that look like SQL
    class SQLStringExtractor(ast.NodeVisitor):
        def __init__(self):
            self.sql_strings = []
        
        def visit_Constant(self, node):
            if isinstance(node.value, str):
                sql_upper = node.value.strip().upper()
                # Check if it looks like SQL (starts with common SQL keywords)
                if any(sql_upper.startswith(kw) for kw in ['SELECT', 'WITH', 'DELETE', 'UPDATE', 'INSERT', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']):
                    self.sql_strings.append(node.value)
            self.generic_visit(node)
        
        def visit_JoinedStr(self, node):
            # f-string - reconstruct it
            query_parts = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    query_parts.append(str(value.value))
                elif isinstance(value, ast.FormattedValue):
                    query_parts.append("?")  # Placeholder
            query = "".join(query_parts)
            sql_upper = query.strip().upper()
            if any(sql_upper.startswith(kw) for kw in ['SELECT', 'WITH', 'DELETE', 'UPDATE', 'INSERT', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']):
                self.sql_strings.append(query)
            self.generic_visit(node)
    
    extractor = SQLStringExtractor()
    extractor.visit(tree)
    
    logger.debug(f"[GUARDRAILS] Found {len(extractor.sql_strings)} SQL-like strings to validate")
    
    # Check each SQL string for dangerous keywords
    for idx, sql_string in enumerate(extractor.sql_strings, 1):
        if not sql_string:
            continue
        
        sql_upper = sql_string.upper()
        logger.debug(f"[GUARDRAILS] Checking SQL string #{idx}: {sql_string[:80]}...")
        
        # Check for dangerous keywords
        found_dangerous = []
        for keyword in dangerous_keywords:
            # Use word boundary check to avoid false positives (e.g., "INSERTED" vs "INSERT")
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                found_dangerous.append(keyword)
        
        if found_dangerous:
            sql_issues.append(f"SQL contains forbidden operation(s): {', '.join(found_dangerous)}")
            logger.warning(f"[GUARDRAILS] SQL #{idx} contains dangerous keywords: {found_dangerous}")
    
    logger.debug(f"[GUARDRAILS] SQL validation complete. Found {len(sql_issues)} issues")
    return sql_issues

# Additional helper function for debugging
def analyze_code_structure(code: str) -> Dict[str, Any]:
    """Analyze code structure for debugging purposes."""
    logger.info("[GUARDRAILS] Starting code structure analysis")
    
    try:
        tree = ast.parse(code)
        
        analysis = {
            "imports": [],
            "function_calls": [],
            "assignments": [],
            "string_literals": []
        }
        
        class AnalysisVisitor(ast.NodeVisitor):
            def visit_Import(self, node):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node):
                if node.module:
                    analysis["imports"].append(node.module)
                self.generic_visit(node)
            
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    analysis["function_calls"].append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    analysis["function_calls"].append(node.func.attr)
                self.generic_visit(node)
            
            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        analysis["assignments"].append(target.id)
                self.generic_visit(node)
            
            def visit_Str(self, node):
                analysis["string_literals"].append(node.s)
                self.generic_visit(node)
        
        visitor = AnalysisVisitor()
        visitor.visit(tree)
        
        logger.info(f"[GUARDRAILS] Code structure analysis completed. Found {len(analysis['imports'])} imports, {len(analysis['function_calls'])} function calls, {len(analysis['assignments'])} assignments")
        logger.debug(f"[GUARDRAILS] Analysis details: {analysis}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"[GUARDRAILS] Error during code structure analysis: {e}")
        return {"error": str(e)}